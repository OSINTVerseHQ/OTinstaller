"""Job state persistence: SQLite-backed resume and tracking."""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from otinstaller.config import get_home, get_state_path


@dataclass(frozen=True)
class InstalledTool:
    name: str
    version: str
    method: str
    source: str
    ref: str | None
    commit: str | None
    entry_command: str | None
    entry_script: str | None
    installed_at: str
    updated_at: str


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    """Open a connection to the state database, running migrations if needed."""
    home = get_home()
    home.mkdir(parents=True, exist_ok=True)
    path = get_state_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Run database migrations using PRAGMA user_version."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    version = cursor.fetchone()[0]
    if version == 0:
        cursor.execute(
            """
            CREATE TABLE installed (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                method TEXT NOT NULL,
                source TEXT NOT NULL,
                ref TEXT,
                commit_hash TEXT,
                entry_command TEXT,
                entry_script TEXT,
                installed_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute("PRAGMA user_version = 1")
        conn.commit()


def add_installed(tool: InstalledTool) -> None:
    """Insert or replace an installed tool."""
    with contextlib.closing(connect()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO installed (
                name, version, method, source, ref, commit_hash,
                entry_command, entry_script, installed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool.name,
                tool.version,
                tool.method,
                tool.source,
                tool.ref,
                tool.commit,
                tool.entry_command,
                tool.entry_script,
                tool.installed_at,
                tool.updated_at,
            ),
        )
        conn.commit()


def get_installed(name: str) -> InstalledTool | None:
    """Get an installed tool by name."""
    with contextlib.closing(connect()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM installed WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return None
        return InstalledTool(
            name=row["name"],
            version=row["version"],
            method=row["method"],
            source=row["source"],
            ref=row["ref"],
            commit=row["commit_hash"],
            entry_command=row["entry_command"],
            entry_script=row["entry_script"],
            installed_at=row["installed_at"],
            updated_at=row["updated_at"],
        )


def list_installed() -> list[InstalledTool]:
    """List all installed tools, sorted by name."""
    with contextlib.closing(connect()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM installed ORDER BY name")
        return [
            InstalledTool(
                name=row["name"],
                version=row["version"],
                method=row["method"],
                source=row["source"],
                ref=row["ref"],
                commit=row["commit_hash"],
                entry_command=row["entry_command"],
                entry_script=row["entry_script"],
                installed_at=row["installed_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]


def remove_installed(name: str) -> bool:
    """Remove an installed tool by name. Returns True if a row was deleted."""
    with contextlib.closing(connect()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM installed WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0


# Job marker system for crash detection/resume


def _jobs_dir() -> Path:
    """Return the directory for job marker files."""
    home = get_home()
    jobs_dir = home / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def _job_path(job_id: str) -> Path:
    """Return the path to a job marker file."""
    return _jobs_dir() / f"{job_id}.json"


@dataclass(frozen=True)
class JobMarker:
    """A marker file recording an in-progress job."""

    job_id: str
    job_type: str  # "install" or "run"
    tool: str
    target: str | None
    started_at: str
    pid: int


def job_start(job_type: str, tool: str, target: str | None = None) -> JobMarker:
    """Create a job marker file recording the start of a job.

    Returns the created JobMarker. The marker file persists on disk until
    job_end() is called, allowing detection of crashed jobs.
    """
    job_id = uuid.uuid4().hex
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pid = os.getpid()

    marker = JobMarker(
        job_id=job_id,
        job_type=job_type,
        tool=tool,
        target=target,
        started_at=started_at,
        pid=pid,
    )

    path = _job_path(job_id)
    data = {
        "job_id": marker.job_id,
        "job_type": marker.job_type,
        "tool": marker.tool,
        "target": marker.target,
        "started_at": marker.started_at,
        "pid": marker.pid,
    }
    path.write_text(json.dumps(data, indent=2))

    return marker


def job_end(job_id: str) -> None:
    """Remove the job marker file for a completed job (success, failure, or SIGINT)."""
    path = _job_path(job_id)
    if path.exists():
        path.unlink()


def list_jobs() -> list[JobMarker]:
    """List all job marker files currently on disk."""
    jobs = []
    for path in _jobs_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text())
            jobs.append(JobMarker(**data))
        except (json.JSONDecodeError, TypeError):
            # Skip malformed marker files
            pass
    return jobs


def scan_orphaned_jobs() -> list[JobMarker]:
    """Scan for job markers whose processes are no longer running.

    Returns a list of JobMarker for jobs whose PID is no longer running.
    These are jobs that were likely killed by SIGKILL, crash, or power loss.
    """
    all_jobs = list_jobs()
    orphaned = []
    for job in all_jobs:
        try:
            # os.kill(pid, 0) checks if process exists without sending signal
            os.kill(job.pid, 0)
            # Process exists - not orphaned
        except ProcessLookupError:
            # Process does not exist - orphaned
            orphaned.append(job)
        except PermissionError:
            # Process exists but we can't signal it (different user) - treat as running
            pass
    return orphaned


def _is_pid_running(pid: int) -> bool:
    """Check if a PID is currently running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Process exists but we can't signal it
