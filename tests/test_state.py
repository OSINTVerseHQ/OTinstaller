"""State tests."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

from otinstaller.state import (
    InstalledTool,
    add_installed,
    connect,
    get_installed,
    job_end,
    job_start,
    list_installed,
    list_jobs,
    remove_installed,
    scan_orphaned_jobs,
)


def test_migration_sets_user_version(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_add_and_get_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = InstalledTool(
        name="test",
        version="1.0",
        method="pip",
        source="test-pkg",
        ref=None,
        commit=None,
        entry_command="test",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(tool)
    got = get_installed("test")
    assert got == tool


def test_add_replace_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool1 = InstalledTool(
        name="test",
        version="1.0",
        method="pip",
        source="test-pkg",
        ref=None,
        commit=None,
        entry_command="test",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    tool2 = InstalledTool(
        name="test",
        version="2.0",
        method="pip",
        source="test-pkg",
        ref=None,
        commit=None,
        entry_command="test",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-02T00:00:00+00:00",
    )
    add_installed(tool1)
    add_installed(tool2)
    got = get_installed("test")
    assert got.version == "2.0"


def test_list_installed_sorted(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    for name in ["ztool", "atool", "mtool"]:
        tool = InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source="pkg",
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
        )
        add_installed(tool)
    tools = list_installed()
    assert [t.name for t in tools] == ["atool", "mtool", "ztool"]


def test_remove_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = InstalledTool(
        name="test",
        version="1.0",
        method="pip",
        source="test-pkg",
        ref=None,
        commit=None,
        entry_command="test",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(tool)
    assert remove_installed("test") is True
    assert get_installed("test") is None
    assert remove_installed("test") is False


def test_sql_injection_safe(monkeypatch, tmp_path):
    """Test that names with quotes and SQL text are stored as plain data."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    name = "test'; DROP TABLE installed; --"
    tool = InstalledTool(
        name=name,
        version="1.0",
        method="pip",
        source="pkg",
        ref=None,
        commit=None,
        entry_command="cmd",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(tool)
    got = get_installed(name)
    assert got is not None
    assert got.name == name


# Job marker tests


def test_job_start_creates_marker_file(monkeypatch, tmp_path):
    """job_start creates a marker file with correct content."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    marker = job_start("install", "testtool", "target1")
    assert marker.job_type == "install"
    assert marker.tool == "testtool"
    assert marker.target == "target1"
    assert marker.pid == os.getpid()
    assert marker.started_at is not None

    # Verify file exists on disk
    jobs = list_jobs()
    assert len(jobs) == 1
    assert jobs[0].job_id == marker.job_id


def test_job_end_removes_marker_file(monkeypatch, tmp_path):
    """job_end removes the marker file."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    marker = job_start("install", "testtool")
    assert len(list_jobs()) == 1

    job_end(marker.job_id)
    assert len(list_jobs()) == 0


def test_job_marker_cleanup_on_success(monkeypatch, tmp_path):
    """Marker file is cleaned up on successful job completion."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    marker = job_start("run", "testtool", "target1")

    # Simulate successful completion
    job_end(marker.job_id)

    assert len(list_jobs()) == 0


def test_job_marker_cleanup_on_failure(monkeypatch, tmp_path):
    """Marker file is cleaned up on job failure (exception)."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    marker = job_start("install", "testtool")

    # Simulate failure cleanup (like install_tool does)
    try:
        raise ValueError("simulated failure")
    except Exception:
        job_end(marker.job_id)

    assert len(list_jobs()) == 0


def test_job_marker_cleanup_on_sigint(monkeypatch, tmp_path):
    """Marker file is cleaned up on KeyboardInterrupt (clean interrupt)."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    marker = job_start("run", "testtool", "target1")

    # Simulate SIGINT cleanup (like runner does)
    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        job_end(marker.job_id)

    assert len(list_jobs()) == 0


def test_scan_orphaned_jobs_dead_pid(monkeypatch, tmp_path):
    """scan_orphaned_jobs returns jobs with dead PIDs."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    # Create a marker with a PID that doesn't exist
    marker = job_start("install", "testtool")
    # Manually modify the marker file to have a non-existent PID
    import pathlib

    job_file = pathlib.Path(tmp_path) / "jobs" / f"{marker.job_id}.json"
    data = json.loads(job_file.read_text())
    data["pid"] = 999999  # Very unlikely to exist
    job_file.write_text(json.dumps(data))

    orphaned = scan_orphaned_jobs()
    assert len(orphaned) == 1
    assert orphaned[0].job_id == marker.job_id


def test_scan_orphaned_jobs_running_pid(monkeypatch, tmp_path):
    """scan_orphaned_jobs does not return jobs with running PIDs (current process)."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    # Create a marker with the current PID (which is running)
    _ = job_start("install", "testtool")

    orphaned = scan_orphaned_jobs()
    assert len(orphaned) == 0  # Current process is running


def test_scan_orphaned_jobs_permission_error(monkeypatch, tmp_path):
    """scan_orphaned_jobs handles PermissionError (different user process)."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    _ = job_start("install", "testtool")

    # Mock os.kill to raise PermissionError
    with patch("os.kill", side_effect=PermissionError("permission denied")):
        orphaned = scan_orphaned_jobs()
        # Should treat as running, not orphaned
        assert len(orphaned) == 0


def test_resume_empty_jobs_dir(monkeypatch, tmp_path, capsys):
    """resume with empty jobs directory prints 'nothing to resume'."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 0
    assert "nothing to resume" in result.output


def test_resume_malformed_marker_file(monkeypatch, tmp_path, capsys):
    """resume skips malformed/corrupt marker files gracefully."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create a malformed marker file
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / "bad.json").write_text("not valid json")

    runner = CliRunner()
    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 0
    assert "nothing to resume" in result.output


def test_resume_mixed_valid_invalid_markers(monkeypatch, tmp_path):
    """resume handles mix of valid and invalid marker files."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create a valid marker with dead PID
    marker = job_start("install", "testtool")
    import pathlib

    job_file = pathlib.Path(tmp_path) / "jobs" / f"{marker.job_id}.json"
    data = json.loads(job_file.read_text())
    data["pid"] = 999999  # Dead PID
    job_file.write_text(json.dumps(data))

    # Create a malformed marker
    (tmp_path / "jobs" / "bad.json").write_text("not valid json")

    runner = CliRunner()
    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 1  # orphaned job found
    assert "found interrupted install: testtool" in result.output
