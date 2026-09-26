"""State tests."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

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


# Update tests


def test_get_latest_pip_version_success(monkeypatch):
    """get_latest_pip_version returns version on success."""
    from otinstaller.installer.core import get_latest_pip_version

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"version": "1.2.3"}}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = lambda s, *a: None
        mock_urlopen.return_value = mock_resp

        version = get_latest_pip_version("testpkg")
        assert version == "1.2.3"


def test_get_latest_pip_version_not_found(monkeypatch):
    """get_latest_pip_version returns None for 404."""
    from otinstaller.installer.core import get_latest_pip_version

    with patch("urllib.request.urlopen", side_effect=HTTPError("url", 404, "Not Found", {}, None)):
        version = get_latest_pip_version("nonexistent")
        assert version is None


def test_get_latest_pip_version_network_error(monkeypatch):
    """get_latest_pip_version returns None on network error."""
    from urllib.error import URLError

    from otinstaller.installer.core import get_latest_pip_version

    with patch("urllib.request.urlopen", side_effect=URLError("network error")):
        version = get_latest_pip_version("testpkg")
        assert version is None


def test_get_latest_git_ref_success(monkeypatch):
    """get_latest_git_ref returns commit hash on success."""
    from otinstaller.installer.core import get_latest_git_ref

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123def456\tHEAD\n"
        mock_run.return_value = mock_result

        ref = get_latest_git_ref("https://github.com/user/repo.git")
        assert ref == "abc123def456"


def test_get_latest_git_ref_error(monkeypatch):
    """get_latest_git_ref returns None on error."""
    from otinstaller.installer.core import get_latest_git_ref

    with patch("subprocess.run", side_effect=subprocess.SubprocessError("git failed")):
        ref = get_latest_git_ref("https://github.com/user/repo.git")
        assert ref is None


def test_versions_differ(monkeypatch):
    """versions_differ correctly compares versions."""
    from otinstaller.installer.core import versions_differ

    # Different versions
    assert versions_differ("1.0.0", "1.0.1") is True
    assert versions_differ("1.0.0", "1.0.0") is False

    # Git commit hashes
    assert versions_differ("abc123", "def456") is True
    assert versions_differ("abc123", "abc123") is False


def test_update_both_names_and_all_error(monkeypatch, tmp_path):
    """update with both names and --all errors."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["update", "tool1", "--all"])
    assert result.exit_code == 1
    assert "cannot use both tool names and --all" in result.output


def test_update_nothing_specified_error(monkeypatch, tmp_path):
    """update with neither names nor --all errors."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["update"])
    assert result.exit_code == 1
    assert "specify tool names or --all" in result.output


def test_update_all_empty_db(monkeypatch, tmp_path):
    """update --all with empty installed DB prints nothing to update."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    # Initialize but don't install anything
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["update", "--all"])
    assert result.exit_code == 0
    assert "nothing installed to update" in result.output


def test_update_check_only_reports_outdated(monkeypatch, tmp_path):
    """--check-only reports outdated tools without installing."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    tool = InstalledTool(
        name="testtool",
        version="1.0.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at=now,
        updated_at=now,
    )
    add_installed(tool)

    def mock_get_latest_pip_version(pkg):
        return "1.0.1"

    with patch(
        "otinstaller.installer.core.get_latest_pip_version", side_effect=mock_get_latest_pip_version
    ):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="testtool",
                display_name="Test Tool",
                description="A tool",
                install=Install(method="pip", package="testpkg"),
                entrypoint=Entrypoint(command="testtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["update", "testtool", "--check-only"])

    assert result.exit_code == 0
    assert "testtool: 1.0.0 -> 1.0.1 available" in result.output
    # install_tool should NOT be called
    with patch("otinstaller.installer.install_tool") as mock_install:
        runner = CliRunner()
        result = runner.invoke(app, ["update", "testtool", "--check-only"])
        mock_install.assert_not_called()


def test_update_check_only_up_to_date(monkeypatch, tmp_path):
    """--check-only reports up-to-date tools correctly."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    tool = InstalledTool(
        name="testtool",
        version="1.0.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at=now,
        updated_at=now,
    )
    add_installed(tool)

    def mock_get_latest_pip_version(pkg):
        return "1.0.0"

    with patch(
        "otinstaller.installer.core.get_latest_pip_version", side_effect=mock_get_latest_pip_version
    ):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="testtool",
                display_name="Test Tool",
                description="A tool",
                install=Install(method="pip", package="testpkg"),
                entrypoint=Entrypoint(command="testtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["update", "testtool", "--check-only"])

    assert result.exit_code == 0
    assert "testtool is already up to date" in result.output


def test_update_pinned_git_tool_skipped(monkeypatch, tmp_path):
    """Pinned git tool is reported as pinned and skipped."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    tool = InstalledTool(
        name="pinnedtool",
        version="4.11.1",
        method="git",
        source="https://github.com/user/repo.git",
        ref="4.11.1",
        commit="abc123",
        entry_command="pinnedtool",
        entry_script=None,
        installed_at=now,
        updated_at=now,
    )
    add_installed(tool)

    with patch("otinstaller.registry.load_registry") as mock_load:
        from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

        mock_tool = Tool(
            name="pinnedtool",
            display_name="Pinned Tool",
            description="A tool",
            install=Install(
                method="git", url="https://github.com/user/repo.git", ref="4.11.1", as_package=True
            ),
            entrypoint=Entrypoint(command="pinnedtool"),
            api_keys=ApiKeys(required=(), optional=()),
            capabilities=[],
            tier="community",
        )
        mock_load.return_value = [mock_tool]

        runner = CliRunner()
        result = runner.invoke(app, ["update", "pinnedtool", "--check-only"])

    assert result.exit_code == 0
    assert "pinned at 4.11.1, skip" in result.output


def test_update_check_only_json_output(monkeypatch, tmp_path):
    """--check-only --json outputs structured data."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    tool = InstalledTool(
        name="testtool",
        version="1.0.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at=now,
        updated_at=now,
    )
    add_installed(tool)

    def mock_get_latest_pip_version(pkg):
        return "1.0.1"

    with patch(
        "otinstaller.installer.core.get_latest_pip_version", side_effect=mock_get_latest_pip_version
    ):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tool = Tool(
                name="testtool",
                display_name="Test Tool",
                description="A tool",
                install=Install(method="pip", package="testpkg"),
                entrypoint=Entrypoint(command="testtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            )
            mock_load.return_value = [mock_tool]

            runner = CliRunner()
            result = runner.invoke(app, ["update", "testtool", "--check-only", "--json"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["tool"] == "testtool"
    assert data[0]["current"] == "1.0.0"
    assert data[0]["latest"] == "1.0.1"
    assert data[0]["outdated"] is True
    assert "error" not in data[0]


def test_update_network_error_continues_batch(monkeypatch, tmp_path):
    """Network error for one tool doesn't stop the batch."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    # Two tools
    for name in ["tool1", "tool2"]:
        t = InstalledTool(
            name=name,
            version="1.0.0",
            method="pip",
            source="pkg",
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )
        add_installed(t)

    def mock_urlopen(req, timeout=10):
        if "pkg1" in req.full_url:
            raise URLError("network error")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"version": "1.0.1"}}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = lambda s, *a: None
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with patch("otinstaller.registry.load_registry") as mock_load:
            from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

            mock_tools = [
                Tool(
                    name="tool1",
                    display_name="Tool 1",
                    description="A tool",
                    install=Install(method="pip", package="pkg1"),
                    entrypoint=Entrypoint(command="tool1"),
                    api_keys=ApiKeys(required=(), optional=()),
                    capabilities=[],
                    tier="community",
                ),
                Tool(
                    name="tool2",
                    display_name="Tool 2",
                    description="A tool",
                    install=Install(method="pip", package="pkg2"),
                    entrypoint=Entrypoint(command="tool2"),
                    api_keys=ApiKeys(required=(), optional=()),
                    capabilities=[],
                    tier="community",
                ),
            ]
            mock_load.return_value = mock_tools

            runner = CliRunner()
            result = runner.invoke(app, ["update", "--all", "--check-only"])

    assert result.exit_code == 0
    assert "error: tool1: could not check for updates" in result.output
    assert "tool2: 1.0.0 -> 1.0.1 available" in result.output


def test_update_outdated_tool_reinstalled(monkeypatch, tmp_path):
    """Outdated tool gets safely reinstalled when confirmed."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()
    tool = InstalledTool(
        name="testtool",
        version="1.0.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at=now,
        updated_at=now,
    )
    add_installed(tool)

    def mock_get_latest_pip_version(pkg):
        return "1.0.1"

    calls = {"install_tool": 0}

    def mock_install_tool(tool, force=False, stream=False):
        calls["install_tool"] += 1
        assert force is True
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool

        now = datetime.now(timezone.utc).isoformat()
        return InstalledTool(
            name="testtool",
            version="1.0.1",
            method="pip",
            source="testpkg",
            ref=None,
            commit=None,
            entry_command="testtool",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch(
        "otinstaller.installer.core.get_latest_pip_version", side_effect=mock_get_latest_pip_version
    ):
        with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
            with patch("otinstaller.registry.load_registry") as mock_load:
                from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

                mock_tool = Tool(
                    name="testtool",
                    display_name="Test Tool",
                    description="A tool",
                    install=Install(method="pip", package="testpkg"),
                    entrypoint=Entrypoint(command="testtool"),
                    api_keys=ApiKeys(required=(), optional=()),
                    capabilities=[],
                    tier="community",
                )
                mock_load.return_value = [mock_tool]

                runner = CliRunner()
                result = runner.invoke(app, ["update", "testtool", "--yes"])

    assert result.exit_code == 0
    assert calls["install_tool"] == 1
    assert "updating testtool..." in result.output
    assert "updated testtool 1.0.1" in result.output


def test_update_summary_counts_mixed(monkeypatch, tmp_path):
    """Summary counts are correct for mixed batch."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")

    from datetime import datetime, timezone

    from otinstaller.state import InstalledTool, add_installed

    now = datetime.now(timezone.utc).isoformat()

    # Add 4 tools: 1 outdated, 1 up-to-date, 1 pinned, 1 error
    for _, (name, version, method, ref) in enumerate(
        [
            ("outdated", "1.0.0", "pip", None),
            ("current", "1.0.0", "pip", None),
            ("pinned", "1.0.0", "git", "v1.0.0"),
            ("error", "1.0.0", "pip", None),
        ]
    ):
        t = InstalledTool(
            name=name,
            version=version,
            method=method,
            source="pkg",
            ref=ref,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )
        add_installed(t)

    def mock_urlopen(req, timeout=10):
        if "pkg-error" in req.full_url:
            raise URLError("network error")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"version": "1.0.1"}}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = lambda s, *a: None
        return mock_resp

    def mock_get_latest_git_ref(url):
        return "def456"

    def mock_install_tool(tool, force=False, stream=False):
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool

        now = datetime.now(timezone.utc).isoformat()
        return InstalledTool(
            name=tool.name,
            version="1.0.1",
            method="pip",
            source="pkg",
            ref=None,
            commit=None,
            entry_command=tool.name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with patch(
            "otinstaller.installer.core.get_latest_git_ref", side_effect=mock_get_latest_git_ref
        ):
            with patch("otinstaller.installer.install_tool", side_effect=mock_install_tool):
                with patch("otinstaller.registry.load_registry") as mock_load:
                    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

                    mock_tools = [
                        Tool(
                            name="outdated",
                            display_name="Outdated Tool",
                            description="A tool",
                            install=Install(method="pip", package="pkg-outdated"),
                            entrypoint=Entrypoint(command="outdated"),
                            api_keys=ApiKeys(required=(), optional=()),
                            capabilities=[],
                            tier="community",
                        ),
                        Tool(
                            name="current",
                            display_name="Current Tool",
                            description="A tool",
                            install=Install(method="pip", package="pkg-current"),
                            entrypoint=Entrypoint(command="current"),
                            api_keys=ApiKeys(required=(), optional=()),
                            capabilities=[],
                            tier="community",
                        ),
                        Tool(
                            name="pinned",
                            display_name="Pinned Tool",
                            description="A tool",
                            install=Install(
                                method="git",
                                url="https://github.com/user/repo.git",
                                ref="v1.0.0",
                                as_package=True,
                            ),
                            entrypoint=Entrypoint(command="pinned"),
                            api_keys=ApiKeys(required=(), optional=()),
                            capabilities=[],
                            tier="community",
                        ),
                        Tool(
                            name="error",
                            display_name="Error Tool",
                            description="A tool",
                            install=Install(method="pip", package="pkg-error"),
                            entrypoint=Entrypoint(command="error"),
                            api_keys=ApiKeys(required=(), optional=()),
                            capabilities=[],
                            tier="community",
                        ),
                    ]
                    mock_load.return_value = mock_tools

                    runner = CliRunner()
                    result = runner.invoke(app, ["update", "--all", "--yes"])

    assert result.exit_code == 1
    # Check summary: 2 updated, 1 pinned, 1 failed (error tool fails)
    assert "2 updated" in result.output
    assert "1 pinned" in result.output
    assert "1 failed" in result.output
