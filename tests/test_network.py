"""Network tests (require RUN_NETWORK_TESTS=1)."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import pytest
from typer.testing import CliRunner

from otinstaller.cli import app

runner = CliRunner()

# Only run if RUN_NETWORK_TESTS=1 is set
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_NETWORK_TESTS"),
    reason="Network tests require RUN_NETWORK_TESTS=1",
)


@pytest.mark.network
def test_network_install_sherlock():
    """Install sherlock into a temporary OTINSTALLER_HOME and remove it."""
    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["OTINSTALLER_HOME"] = tmp_home

        # Init
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # Install sherlock
        result = runner.invoke(app, ["install", "sherlock", "--yes"])
        assert result.exit_code == 0
        assert "installed sherlock" in result.output

        # Verify it's installed
        result = runner.invoke(app, ["list", "--installed"])
        assert result.exit_code == 0
        assert "sherlock" in result.output

        # Run sherlock --help
        sherlock_bin = os.path.join(tmp_home, "tools", "sherlock", "venv", "bin", "sherlock")
        assert os.path.exists(sherlock_bin)

        # Remove sherlock
        result = runner.invoke(app, ["remove", "sherlock", "--yes"])
        assert result.exit_code == 0
        assert "removed sherlock" in result.output

        # Verify it's removed
        result = runner.invoke(app, ["list", "--installed"])
        assert result.exit_code == 0
        assert "no tools installed" in result.output or "sherlock" not in result.output


@pytest.mark.network
def test_network_sigint_cleanup():
    """SIGINT during install cleans up tool directory and database row."""
    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["OTINSTALLER_HOME"] = tmp_home

        # Init first
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # Start install in background using subprocess in its own process group
        # so we can send SIGINT to it without affecting the test process
        otinstaller_path = shutil.which("otinstaller") or [sys.executable, "-m", "otinstaller"]
        if isinstance(otinstaller_path, str):
            otinstaller_path = [otinstaller_path]
        proc = subprocess.Popen(
            [
                *otinstaller_path,
                "install",
                "maigret",
                "--yes",
            ],
            env={**os.environ, "OTINSTALLER_HOME": tmp_home},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        # Wait for install to start (pip install phase)
        time.sleep(3)

        # Send SIGINT to the child process group only
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)

        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=5)

        # Verify tool directory is cleaned up
        maigret_dir = os.path.join(tmp_home, "tools", "maigret")
        assert not os.path.exists(maigret_dir), f"Directory {maigret_dir} should be cleaned up"

        # Verify no database row exists
        from otinstaller.state import connect

        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM installed WHERE name = 'maigret'")
        row = cursor.fetchone()
        conn.close()
        assert row is None, "Database row should not exist after SIGINT cleanup"


@pytest.mark.network
def test_network_crash_detection_marker_file():
    """SIGKILL during install leaves a marker file that resume detects."""
    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["OTINSTALLER_HOME"] = tmp_home

        # Init first
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # Start install in background using subprocess in its own process group
        otinstaller_path = shutil.which("otinstaller") or [sys.executable, "-m", "otinstaller"]
        if isinstance(otinstaller_path, str):
            otinstaller_path = [otinstaller_path]
        proc = subprocess.Popen(
            [
                *otinstaller_path,
                "install",
                "sherlock",
                "--yes",
            ],
            env={**os.environ, "OTINSTALLER_HOME": tmp_home},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        # Wait for install to start (job_start marker should be written)
        time.sleep(0.5)

        # Send SIGKILL to the child process group (simulates crash/power loss)
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=5)

        # Verify a marker file exists in jobs/
        jobs_dir = os.path.join(tmp_home, "jobs")
        marker_files = [f for f in os.listdir(jobs_dir) if f.endswith(".json")]
        assert len(marker_files) == 1, f"Expected 1 marker file, found {marker_files}"

        # Verify marker content
        import json

        with open(os.path.join(jobs_dir, marker_files[0])) as f:
            marker = json.load(f)
        assert marker["job_type"] == "install"
        assert marker["tool"] == "sherlock"
        assert marker["target"] is None
        assert "started_at" in marker
        assert "pid" in marker
        assert marker["pid"] == proc.pid

        # Run resume and verify it resumes the interrupted install
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 0  # install resumed successfully
        assert "resuming install: sherlock..." in result.output
        assert "installed sherlock" in result.output
        assert "1 installs resumed, 0 runs reported, 0 skipped (still running)" in result.output

        # Verify marker file is removed
        marker_files = [f for f in os.listdir(jobs_dir) if f.endswith(".json")]
        assert len(marker_files) == 0, f"Expected 0 marker files after resume, found {marker_files}"

        # Verify tool is installed
        sherlock_dir = os.path.join(tmp_home, "tools", "sherlock")
        assert os.path.exists(sherlock_dir), "sherlock tool directory should exist after resume"

        # Also test --json output (now shows empty since job is resolved)
        result = runner.invoke(app, ["resume", "--json"])
        assert result.exit_code == 0
        import json

        output = json.loads(result.output)
        assert len(output["orphaned"]) == 0
        assert len(output["all_jobs"]) == 0
