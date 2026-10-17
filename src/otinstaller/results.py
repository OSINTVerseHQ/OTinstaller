"""Results handling: saving, naming, and organizing tool output."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otinstaller.config import get_results_dir
from otinstaller.registry import Tool


class ResultsDirError(Exception):
    """The results folder can't be created (no write access, a file in the way, ...)."""


def sanitize_component(value: str) -> str:
    """Sanitize a path component for safe filesystem use."""
    # Lowercase
    value = value.lower()
    # Replace anything not [a-z0-9._-] with _
    value = re.sub(r"[^a-z0-9._-]", "_", value)
    # Collapse repeated _
    value = re.sub(r"_+", "_", value)
    # Strip leading/trailing _ and .
    value = value.strip("_.-")
    # Truncate to 80 chars
    if len(value) > 80:
        value = value[:80]
    # If empty, return "target"
    if not value:
        return "target"
    return value


def new_run_id() -> str:
    """Generate a new run ID (8 lowercase hex chars)."""
    return os.urandom(4).hex()


def ext_for_tool(tool: Tool) -> str:
    """Return the output file extension for a tool."""
    return "txt"


def results_paths(
    tool_name: str,
    target: str,
    case: str | None,
) -> tuple[Path, Path]:
    """Return (output_path, meta_path) for a tool run."""
    base = get_results_dir()
    if case:
        base = base / "cases" / sanitize_component(case)
    target_sanitized = sanitize_component(target)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    runid = new_run_id()
    ext = "txt"  # hardcoded for now
    filename = f"{timestamp}_{tool_name}_{target_sanitized}_{runid}.{ext}"
    output_path = base / tool_name / target_sanitized / filename
    meta_path = output_path.with_suffix(".meta.json")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        reason = exc.strerror or exc.__class__.__name__
        raise ResultsDirError(
            f"can't save results in {get_results_dir()} ({reason.lower()}). "
            "Run otinstaller from a folder you can write to, such as your home folder, "
            "or choose one with: export OTINSTALLER_RESULTS_DIR=~/otinstaller-results"
        ) from exc
    return output_path, meta_path


@dataclass
class RunMeta:
    command: list[str]
    tool: str
    tool_version: str
    target: str
    case: str | None
    started_at: str
    ended_at: str
    duration_seconds: float
    exit_code: int
    status: str
    output_path: str
    sha256: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_meta(meta: RunMeta, path: Path) -> None:
    """Write RunMeta as pretty JSON with sorted keys."""
    path.write_text(json.dumps(meta.to_dict(), sort_keys=True, indent=2))


def hash_file(path: Path) -> str:
    """Compute SHA-256 of a file in streaming chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
