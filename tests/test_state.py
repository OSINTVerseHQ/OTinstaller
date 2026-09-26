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

    def mock_install_tool(tool, force=False, stream=False):
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool

        now = datetime.now(timezone.utc).isoformat()
        return InstalledTool(
            name="testtool",
            version="1.0",
            method="pip",
            source="testpkg",
            ref=None,
            commit=None,
            entry_command="testtool",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="testtool",
                display_name="Test Tool",
                description="A test tool",
                install=Install(method="pip", package="testpkg"),
                entrypoint=Entrypoint(command="testtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["resume"])

    assert result.exit_code == 0
    assert "resuming install: testtool..." in result.output
    assert "installed testtool 1.0" in result.output
    # Malformed marker should be skipped, not cause crash


# Resume retry tests


def test_resume_orphaned_install_cleans_and_retries(monkeypatch, tmp_path):
    """Resuming an orphaned install cleans the tool dir, removes marker, and calls install_tool."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create a tool directory (simulating half-finished install)
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True)
    tool_dir = tools_dir / "testtool"
    tool_dir.mkdir(parents=True)
    (tool_dir / "partial_file.txt").write_text("partial")

    # Create an orphaned install marker with dead PID
    marker = job_start("install", "testtool")
    job_file = tmp_path / "jobs" / f"{marker.job_id}.json"
    data = json.loads(job_file.read_text())
    data["pid"] = 999999  # Dead PID
    job_file.write_text(json.dumps(data))

    # Track calls
    calls = {"cleaned": False, "install_called": False}

    def mock_safe_rmtree(path):
        calls["cleaned"] = True
        assert path == tool_dir

    def mock_install_tool(tool, force=False, stream=False):
        calls["install_called"] = True
        assert tool.name == "testtool"
        assert force is True
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool

        now = datetime.now(timezone.utc).isoformat()
        return InstalledTool(
            name="testtool",
            version="1.0",
            method="pip",
            source="testpkg",
            ref=None,
            commit=None,
            entry_command="testtool",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("otinstaller.installer.core.safe_rmtree", side_effect=mock_safe_rmtree):
        with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
            with patch("otinstaller.registry.load_registry") as mock_load:
                from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

                mock_tool = Tool(
                    name="testtool",
                    display_name="Test Tool",
                    description="A test tool",
                    install=Install(method="pip", package="testpkg"),
                    entrypoint=Entrypoint(command="testtool"),
                    api_keys=ApiKeys(required=(), optional=()),
                    capabilities=[],
                    tier="community",
                )
                mock_load.return_value = [mock_tool]

                runner = CliRunner()
                result = runner.invoke(app, ["resume"])

    assert result.exit_code == 0
    assert calls["cleaned"]
    assert calls["install_called"]
    assert "resuming install: testtool..." in result.output
    assert "installed testtool 1.0" in result.output
    # Marker should be removed
    assert not job_file.exists()


def test_resume_orphaned_install_failure_removes_marker(monkeypatch, tmp_path):
    """Resuming an orphaned install that fails still removes the marker."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create an orphaned install marker with dead PID
    marker = job_start("install", "badtool")
    job_file = tmp_path / "jobs" / f"{marker.job_id}.json"
    data = json.loads(job_file.read_text())
    data["pid"] = 999999
    job_file.write_text(json.dumps(data))

    def mock_install_tool(tool, force=False, stream=False):
        from otinstaller.installer import InstallError

        raise InstallError("simulated failure")

    with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="badtool",
                display_name="Bad Tool",
                description="A bad tool",
                install=Install(method="pip", package="badpkg"),
                entrypoint=Entrypoint(command="badtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["resume"])

    # Exit code 1 because install failed
    assert result.exit_code == 1
    # Marker should still be removed (job resolved either way)
    assert not job_file.exists()
    assert "resuming install: badtool..." in result.output
    assert "error: badtool: simulated failure" in result.output


def test_resume_orphaned_run_reports_and_removes_marker(monkeypatch, tmp_path):
    """An orphaned run job is reported with rerun command, marker removed."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create an orphaned run marker with dead PID
    marker = job_start("run", "testtool", "target1")
    job_file = tmp_path / "jobs" / f"{marker.job_id}.json"
    data = json.loads(job_file.read_text())
    data["pid"] = 999999
    job_file.write_text(json.dumps(data))

    runner = CliRunner()
    result = runner.invoke(app, ["resume"])

    assert result.exit_code == 0
    base = "found interrupted run: testtool (target: target1)"
    expected = f"{base} - rerun manually with: otinstaller run testtool -- target1"
    assert expected in result.output
    # Marker should be removed
    assert not job_file.exists()


def test_resume_still_running_skipped(monkeypatch, tmp_path):
    """A still-running job is left completely untouched."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create a marker with current PID (still running)
    marker = job_start("install", "testtool")
    job_file = tmp_path / "jobs" / f"{marker.job_id}.json"

    runner = CliRunner()
    result = runner.invoke(app, ["resume"])

    assert result.exit_code == 0
    assert "possibly still running: testtool" in result.output
    assert "skipping" in result.output
    # Marker should NOT be removed
    assert job_file.exists()


def test_resume_dry_run_makes_no_changes(monkeypatch, tmp_path):
    """--dry-run makes zero changes to disk."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create a tool directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True)
    tool_dir = tools_dir / "testtool"
    tool_dir.mkdir(parents=True)
    (tool_dir / "partial_file.txt").write_text("partial")

    # Create orphaned markers (install and run)
    install_marker = job_start("install", "testtool")
    install_file = tmp_path / "jobs" / f"{install_marker.job_id}.json"
    data = json.loads(install_file.read_text())
    data["pid"] = 999999
    install_file.write_text(json.dumps(data))

    run_marker = job_start("run", "runtool", "target1")
    run_file = tmp_path / "jobs" / f"{run_marker.job_id}.json"
    data = json.loads(run_file.read_text())
    data["pid"] = 999999
    run_file.write_text(json.dumps(data))

    runner = CliRunner()
    result = runner.invoke(app, ["resume", "--dry-run"])

    assert result.exit_code == 0
    assert "would resume install: testtool" in result.output
    assert "would report interrupted run: runtool" in result.output
    assert "1 installs resumed, 1 runs reported, 0 skipped (still running)" in result.output
    # Nothing should be changed
    assert install_file.exists()
    assert run_file.exists()
    assert tool_dir.exists()
    assert (tool_dir / "partial_file.txt").exists()


def test_resume_summary_counts_mixed(monkeypatch, tmp_path):
    """Summary line counts are correct for a mixed set."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Create orphaned install
    marker1 = job_start("install", "tool1")
    job_file1 = tmp_path / "jobs" / f"{marker1.job_id}.json"
    data = json.loads(job_file1.read_text())
    data["pid"] = 999999
    job_file1.write_text(json.dumps(data))

    # Create orphaned run
    marker2 = job_start("run", "tool2", "target1")
    job_file2 = tmp_path / "jobs" / f"{marker2.job_id}.json"
    data = json.loads(job_file2.read_text())
    data["pid"] = 999999
    job_file2.write_text(json.dumps(data))

    # Create still-running
    _ = job_start("install", "tool3")
    # current PID - will be detected as running

    def mock_install_tool(tool, force=False, stream=False):
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool

        now = datetime.now(timezone.utc).isoformat()
        return InstalledTool(
            name=tool.name,
            version="1.0",
            method="pip",
            source="pkg",
            ref=None,
            commit=None,
            entry_command=tool.name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="tool1",
                display_name="Tool 1",
                description="A tool",
                install=Install(method="pip", package="pkg"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["resume"])

    assert result.exit_code == 0
    assert "1 installs resumed, 1 runs reported, 1 skipped (still running)" in result.output
