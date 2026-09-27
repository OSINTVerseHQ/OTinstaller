"""Run diff: compare two result files for the same tool/target."""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from otinstaller.config import get_results_dir
from otinstaller.results import sanitize_component


def find_recent_runs(tool: str, target: str, case: str | None = None) -> list[Path]:
    """Find all output .txt files for a tool+target combination.

    Returns list sorted newest first by timestamp in filename.
    """
    base = get_results_dir()
    if case:
        base = base / "cases" / sanitize_component(case)
    target_sanitized = sanitize_component(target)

    tool_dir = base / tool / target_sanitized
    if not tool_dir.exists():
        return []

    # Find all .txt files (output files, not meta.json)
    files = list(tool_dir.glob("*.txt"))
    # Sort by filename timestamp (newest first)
    files.sort(key=lambda p: p.stem, reverse=True)
    return files


def diff_runs(older_path: Path, newer_path: Path) -> dict:
    """Compute diff between two run output files.

    Returns dict with added/removed lines and metadata.
    """
    older_text = older_path.read_text(encoding="utf-8", errors="ignore")
    newer_text = newer_path.read_text(encoding="utf-8", errors="ignore")

    older_lines = older_text.splitlines()
    newer_lines = newer_text.splitlines()

    diff = difflib.unified_diff(older_lines, newer_lines, lineterm="", n=0)

    added: list[str] = []
    removed: list[str] = []

    for line in diff:
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
        # Skip "?" lines (context markers) and "@@" headers

    # Get dates from meta.json files
    older_meta = older_path.with_suffix(".meta.json")
    newer_meta = newer_path.with_suffix(".meta.json")

    def get_date(meta_path: Path) -> str:
        try:
            with meta_path.open() as f:
                data = json.load(f)
                return data.get("started_at", "")
        except (OSError, json.JSONDecodeError):
            return ""

    return {
        "added": added,
        "removed": removed,
        "older_file": str(older_path),
        "newer_file": str(newer_path),
        "older_date": get_date(older_meta),
        "newer_date": get_date(newer_meta),
    }
