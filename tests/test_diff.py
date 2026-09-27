"""Diff tests."""

import json
import tempfile
from pathlib import Path

from otinstaller.diff import diff_runs, find_recent_runs


def test_find_recent_runs_empty(tmp_path):
    """find_recent_runs returns empty for no matches."""
    runs = find_recent_runs("nonexistent", "target", case=None)
    assert runs == []


def test_find_recent_runs_sorts_newest_first(tmp_path):
    """find_recent_runs sorts correctly newest-first."""
    # Create a fake results structure
    base = tmp_path / "results"
    tool_dir = base / "testtool" / "target"
    tool_dir.mkdir(parents=True)

    # Create files with timestamps in names
    file1 = tool_dir / "20240101-120000_testtool_target_abc123.txt"
    file2 = tool_dir / "20240102-120000_testtool_target_def456.txt"
    file3 = tool_dir / "20240103-120000_testtool_target_ghi789.txt"
    file1.write_text("old")
    file2.write_text("middle")
    file3.write_text("new")

    # Create meta files
    for f in [file1, file2, file3]:
        meta = f.with_suffix(".meta.json")
        meta.write_text(json.dumps({"started_at": "2024-01-01T00:00:00+00:00"}))

    # Mock get_results_dir to return our temp path
    import otinstaller.diff

    original_get_results = otinstaller.diff.get_results_dir
    otinstaller.diff.get_results_dir = lambda: tmp_path / "results"

    try:
        runs = find_recent_runs("testtool", "target", case=None)
        assert len(runs) == 3
        # Newest first
        assert runs[0].name == "20240103-120000_testtool_target_ghi789.txt"
        assert runs[1].name == "20240102-120000_testtool_target_def456.txt"
        assert runs[2].name == "20240101-120000_testtool_target_abc123.txt"
    finally:
        otinstaller.diff.get_results_dir = original_get_results


def test_diff_runs_added_removed():
    """diff_runs correctly identifies added and removed lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        older = Path(tmpdir) / "older.txt"
        newer = Path(tmpdir) / "newer.txt"

        older.write_text("line1\nline2\nline3\n")
        newer.write_text("line1\nline2\nline4\nline5\n")

        # Create meta files
        older_meta = older.with_suffix(".meta.json")
        newer_meta = newer.with_suffix(".meta.json")
        older_meta.write_text(json.dumps({"started_at": "2024-01-01T00:00:00+00:00"}))
        newer_meta.write_text(json.dumps({"started_at": "2024-01-02T00:00:00+00:00"}))

        result = diff_runs(older, newer)

        assert "line4" in result["added"]
        assert "line5" in result["added"]
        assert "line3" in result["removed"]
        assert result["older_file"] == str(older)
        assert result["newer_file"] == str(newer)
        assert result["older_date"] == "2024-01-01T00:00:00+00:00"
        assert result["newer_date"] == "2024-01-02T00:00:00+00:00"


def test_diff_runs_no_changes():
    """diff_runs reports no changes for identical files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        older = Path(tmpdir) / "older.txt"
        newer = Path(tmpdir) / "newer.txt"

        content = "line1\nline2\nline3\n"
        older.write_text(content)
        newer.write_text(content)

        older_meta = older.with_suffix(".meta.json")
        newer_meta = newer.with_suffix(".meta.json")
        older_meta.write_text(json.dumps({"started_at": "2024-01-01T00:00:00+00:00"}))
        newer_meta.write_text(json.dumps({"started_at": "2024-01-02T00:00:00+00:00"}))

        result = diff_runs(older, newer)

        assert result["added"] == []
        assert result["removed"] == []


def test_find_recent_runs_case(tmp_path):
    """find_recent_runs respects case parameter."""
    import otinstaller.diff

    original_get_results = otinstaller.diff.get_results_dir
    otinstaller.diff.get_results_dir = lambda: tmp_path / "results"

    try:
        # Create case directory structure
        case_dir = tmp_path / "results" / "cases" / "mycase" / "tool" / "target"
        case_dir.mkdir(parents=True)

        file1 = case_dir / "20240101-120000_tool_target_abc123.txt"
        file1.write_text("content")
        file1.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-01T00:00:00+00:00"})
        )

        runs = find_recent_runs("tool", "target", case="mycase")
        assert len(runs) == 1
    finally:
        otinstaller.diff.get_results_dir = original_get_results
