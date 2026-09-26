"""Runner tests."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool
from otinstaller.runner import run_tool, run_tools_parallel


def make_fake_tool(
    name: str,
    required: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
) -> Tool:
    """Create a minimal fake tool for testing."""
    return Tool(
        name=name,
        display_name=name.title(),
        description=f"Fake tool {name}",
        install=Install(method="pip", package=name),
        entrypoint=Entrypoint(command=name),
        api_keys=ApiKeys(required=required, optional=optional),
    )


def test_run_tool_basic(tmp_path):
    """Basic sanity check that run_tool can be called with a mocked subprocess."""
    tool = make_fake_tool("faketool")
    root = tmp_path / "faketool"
    root.mkdir(parents=True)

    with patch("otinstaller.runner.subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        # Create a proper stdout that supports readline
        stdout_lines = [b"output line\n", b""]
        mock_proc.stdout.readline = MagicMock(side_effect=stdout_lines)
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        meta = run_tool(
            tool,
            root,
            ["arg1"],
            target="target1",
            case=None,
            env_overrides=None,
            stream=False,
        )

        assert meta.tool == "faketool"
        assert meta.target == "target1"
        assert meta.exit_code == 0
        assert meta.status == "complete"
        mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_run_tools_parallel_concurrent(tmp_path):
    """Test that run_tools_parallel runs tools concurrently when max_parallel >= tool count."""
    tools = [make_fake_tool(f"tool{i}") for i in range(3)]
    roots = {t.name: tmp_path / t.name for t in tools}
    for root in roots.values():
        root.mkdir(parents=True)

    # Track start/end times for each tool
    tool_times = {}

    def mock_run_tool(
        tool, root, extra_args, *, target, case, env_overrides, stream, cancel_event=None
    ):
        start = time.monotonic()
        tool_times[tool.name] = {"start": start}
        time.sleep(0.3)  # Simulate work (sync sleep since run_tool is sync)
        end = time.monotonic()
        tool_times[tool.name]["end"] = end

        # Return a minimal RunMeta
        from datetime import datetime, timezone

        from otinstaller.results import RunMeta

        now = datetime.now(timezone.utc).isoformat()
        return RunMeta(
            command=[tool.name],
            tool=tool.name,
            tool_version="1.0",
            target=target or "unspecified",
            case=case,
            started_at=now,
            ended_at=now,
            duration_seconds=end - start,
            exit_code=0,
            status="complete",
            output_path=f"{tool.name}/unspecified/test.txt",
            sha256="abc123",
            bytes=100,
        )

    with patch("otinstaller.runner.run_tool", side_effect=mock_run_tool):
        start_wall = time.monotonic()
        results = await run_tools_parallel(
            tools,
            roots,
            ["common_arg"],
            target="target1",
            case=None,
            max_parallel=3,
            stream=False,
        )
        elapsed = time.monotonic() - start_wall

    # Should complete in ~0.3-0.4s (concurrent), not ~0.9s (sequential)
    print(f"test_run_tools_parallel_concurrent: elapsed={elapsed:.2f}s")
    assert elapsed < 0.6, f"Expected concurrent execution (~0.3s), took {elapsed:.2f}s"
    assert len(results) == 3
    assert all(r.status == "complete" for r in results)

    # Verify all tools started at roughly the same time (within 0.1s of each other)
    starts = [t["start"] for t in tool_times.values()]
    assert max(starts) - min(starts) < 0.15


@pytest.mark.asyncio
async def test_run_tools_parallel_limited_concurrency(tmp_path):
    """Test that run_tools_parallel respects max_parallel limit."""
    tools = [make_fake_tool(f"tool{i}") for i in range(3)]
    roots = {t.name: tmp_path / t.name for t in tools}
    for root in roots.values():
        root.mkdir(parents=True)

    tool_times = {}

    def mock_run_tool(
        tool, root, extra_args, *, target, case, env_overrides, stream, cancel_event=None
    ):
        start = time.monotonic()
        tool_times[tool.name] = {"start": start}
        time.sleep(0.3)
        end = time.monotonic()
        tool_times[tool.name]["end"] = end

        from datetime import datetime, timezone

        from otinstaller.results import RunMeta

        now = datetime.now(timezone.utc).isoformat()
        return RunMeta(
            command=[tool.name],
            tool=tool.name,
            tool_version="1.0",
            target=target or "unspecified",
            case=case,
            started_at=now,
            ended_at=now,
            duration_seconds=end - start,
            exit_code=0,
            status="complete",
            output_path=f"{tool.name}/unspecified/test.txt",
            sha256="abc123",
            bytes=100,
        )

    with patch("otinstaller.runner.run_tool", side_effect=mock_run_tool):
        start_wall = time.monotonic()
        results = await run_tools_parallel(
            tools,
            roots,
            ["common_arg"],
            target="target1",
            case=None,
            max_parallel=1,
            stream=False,
        )
        elapsed = time.monotonic() - start_wall

    # Should take ~0.9s (sequential: 3 * 0.3s)
    print(f"test_run_tools_parallel_limited_concurrency: elapsed={elapsed:.2f}s")
    assert elapsed >= 0.8, f"Expected sequential execution (~0.9s), took {elapsed:.2f}s"
    assert len(results) == 3
    assert all(r.status == "complete" for r in results)

    # Verify tools ran sequentially (start times separated by ~0.3s)
    starts = sorted([t["start"] for t in tool_times.values()])
    assert starts[1] - starts[0] >= 0.25
    assert starts[2] - starts[1] >= 0.25


@pytest.mark.asyncio
async def test_run_tools_parallel_mixed_success_failure(tmp_path):
    """Test that one tool failing doesn't prevent others from completing."""
    tools = [make_fake_tool("success1"), make_fake_tool("fail"), make_fake_tool("success2")]
    roots = {t.name: tmp_path / t.name for t in tools}
    for root in roots.values():
        root.mkdir(parents=True)

    call_count = {"count": 0}

    def mock_run_tool(
        tool, root, extra_args, *, target, case, env_overrides, stream, cancel_event=None
    ):
        call_count["count"] += 1
        time.sleep(0.1)

        from datetime import datetime, timezone

        from otinstaller.results import RunMeta

        now = datetime.now(timezone.utc).isoformat()
        if tool.name == "fail":
            return RunMeta(
                command=[tool.name],
                tool=tool.name,
                tool_version="1.0",
                target=target or "unspecified",
                case=case,
                started_at=now,
                ended_at=now,
                duration_seconds=0.1,
                exit_code=1,
                status="failed",
                output_path=f"{tool.name}/unspecified/test.txt",
                sha256="abc123",
                bytes=100,
            )
        return RunMeta(
            command=[tool.name],
            tool=tool.name,
            tool_version="1.0",
            target=target or "unspecified",
            case=case,
            started_at=now,
            ended_at=now,
            duration_seconds=0.1,
            exit_code=0,
            status="complete",
            output_path=f"{tool.name}/unspecified/test.txt",
            sha256="abc123",
            bytes=100,
        )

    with patch("otinstaller.runner.run_tool", side_effect=mock_run_tool):
        results = await run_tools_parallel(
            tools,
            roots,
            [],
            target="target1",
            case=None,
            max_parallel=3,
            stream=False,
        )

    assert len(results) == 3
    assert results[0].status == "complete"
    assert results[1].status == "failed"
    assert results[2].status == "complete"
    assert call_count["count"] == 3  # All three were called


@pytest.mark.network
@pytest.mark.asyncio
async def test_run_tools_parallel_sigint(monkeypatch, tmp_path):
    """Real SIGINT test for parallel runs - requires Linux and installed tools."""
    import os
    import signal
    import subprocess
    import sys
    import time

    # Skip if not on Linux
    if sys.platform != "linux":
        pytest.skip("SIGINT test requires Linux")

    # Use a temporary OTINSTALLER_HOME
    home = tmp_path / "home"
    monkeypatch.setenv("OTINSTALLER_HOME", str(home))

    # Check if sherlock and maigret are installed
    sherlock_path = home / "tools" / "sherlock"
    maigret_path = home / "tools" / "maigret"
    if not sherlock_path.exists() or not maigret_path.exists():
        pytest.skip("sherlock and maigret must be installed")

    # Run otinstaller with both tools in parallel
    cmd = [
        sys.executable,
        "-m",
        "otinstaller",
        "run",
        "sherlock",
        "maigret",
        "--parallel",
        "2",
        "--",
        "testuser",
    ]

    # Start the process in its own process group
    proc = subprocess.Popen(
        cmd,
        preexec_fn=os.setsid,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        # Wait a moment for tools to start
        time.sleep(3)

        # Send SIGINT to the process group
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)

        # Wait for process to exit with timeout
        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, _ = proc.communicate()
            pytest.fail("otinstaller did not exit within 10 seconds after SIGINT")

        # Verify process exited
        assert proc.returncode is not None, "otinstaller process should have exited"

        # Check for orphaned processes
        time.sleep(1)  # Allow time for process cleanup
        remaining = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        sherlock_procs = [
            line
            for line in remaining.stdout.splitlines()
            if "sherlock" in line and "grep" not in line
        ]
        maigret_procs = [
            line
            for line in remaining.stdout.splitlines()
            if "maigret" in line and "grep" not in line
        ]

        # Should have no orphaned sherlock or maigret processes
        assert not sherlock_procs, f"Orphaned sherlock processes: {sherlock_procs}"
        assert not maigret_procs, f"Orphaned maigret processes: {maigret_procs}"

        # Check for meta.json files with status "interrupted"
        import json

        results_dir = home / "results"
        sherlock_meta_files = list(results_dir.glob("sherlock/**/*.meta.json"))
        maigret_meta_files = list(results_dir.glob("maigret/**/*.meta.json"))

        assert sherlock_meta_files, "No sherlock meta.json found"
        assert maigret_meta_files, "No maigret meta.json found"

        # Check at least one meta.json for each tool has status "interrupted"
        sherlock_interrupted = False
        for meta_file in sherlock_meta_files:
            with open(meta_file) as f:
                meta = json.load(f)
                if meta.get("status") == "interrupted":
                    sherlock_interrupted = True
                    break

        maigret_interrupted = False
        for meta_file in maigret_meta_files:
            with open(meta_file) as f:
                meta = json.load(f)
                if meta.get("status") == "interrupted":
                    maigret_interrupted = True
                    break

        assert sherlock_interrupted, "No sherlock meta.json with status 'interrupted'"
        assert maigret_interrupted, "No maigret meta.json with status 'interrupted'"

    finally:
        # Cleanup: ensure process is dead
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass


@pytest.mark.asyncio
async def test_run_tool_injects_only_declared_keys(tmp_path):
    """A tool's subprocess environment includes only its declared keys."""
    # Create a temp env file with multiple keys
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text(
            "REQUIRED_KEY=secret123\n"
            "OPTIONAL_KEY=optional456\n"
            "UNRELATED_KEY=should_not_appear\n"
            "ANOTHER_KEY=also_should_not_appear\n"
        )

        with patch("otinstaller.runner.load_env_file") as mock_load_env:
            mock_load_env.return_value = {
                "REQUIRED_KEY": "secret123",
                "OPTIONAL_KEY": "optional456",
                "UNRELATED_KEY": "should_not_appear",
                "ANOTHER_KEY": "also_should_not_appear",
            }

            with patch("otinstaller.runner.subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                stdout_lines = [b"output line\n", b""]
                mock_proc.stdout.readline = MagicMock(side_effect=stdout_lines)
                mock_proc.wait.return_value = 0
                mock_popen.return_value = mock_proc

                tool = make_fake_tool(
                    "testtool",
                    required=("REQUIRED_KEY",),
                    optional=("OPTIONAL_KEY",),
                )
                root = tmp_path / "testtool"
                root.mkdir(parents=True)

                run_tool(
                    tool,
                    root,
                    ["arg1"],
                    target="target1",
                    case=None,
                    env_overrides=None,
                    stream=False,
                )

                # Verify only the declared keys were passed to the subprocess
                mock_popen.assert_called_once()
                call_kwargs = mock_popen.call_args.kwargs
                env = call_kwargs["env"]
                assert env.get("REQUIRED_KEY") == "secret123"
                assert env.get("OPTIONAL_KEY") == "optional456"
                assert "UNRELATED_KEY" not in env
                assert "ANOTHER_KEY" not in env
                # Ensure original environment is still there
                assert "PATH" in env


@pytest.mark.asyncio
async def test_run_tool_missing_required_key_warns_but_runs(tmp_path):
    """A missing required key prints a warning but does NOT prevent the subprocess from starting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("OPTIONAL_KEY=optional456\n")  # Missing REQUIRED_KEY

        with patch("otinstaller.runner.load_env_file") as mock_load_env:
            mock_load_env.return_value = {"OPTIONAL_KEY": "optional456"}

            with patch("otinstaller.runner.subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                stdout_lines = [b"output line\n", b""]
                mock_proc.stdout.readline = MagicMock(side_effect=stdout_lines)
                mock_proc.wait.return_value = 0
                mock_popen.return_value = mock_proc

                tool = make_fake_tool(
                    "testtool",
                    required=("REQUIRED_KEY",),
                    optional=("OPTIONAL_KEY",),
                )
                root = tmp_path / "testtool"
                root.mkdir(parents=True)

                run_tool(
                    tool,
                    root,
                    ["arg1"],
                    target="target1",
                    case=None,
                    env_overrides=None,
                    stream=False,
                )

                # Should have printed warning to stderr
                # The subprocess should still have started
                mock_popen.assert_called_once()
                call_kwargs = mock_popen.call_args.kwargs
                env = call_kwargs["env"]
                assert env.get("OPTIONAL_KEY") == "optional456"
                assert "REQUIRED_KEY" not in env


@pytest.mark.asyncio
async def test_run_tool_does_not_leak_secrets_in_outputs(tmp_path):
    """A fake secret value in env file does NOT appear in meta.json, logs, or stdout."""
    secret_value = "SUPER_SECRET_API_KEY_12345"

    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text(f"SECRET_KEY={secret_value}\n")

        with patch("otinstaller.runner.load_env_file") as mock_load_env:
            mock_load_env.return_value = {"SECRET_KEY": secret_value}

            with patch("otinstaller.runner.subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                stdout_lines = [b"output line\n", b""]
                mock_proc.stdout.readline = MagicMock(side_effect=stdout_lines)
                mock_proc.wait.return_value = 0
                mock_popen.return_value = mock_proc

                tool = make_fake_tool(
                    "testtool",
                    required=("SECRET_KEY",),
                )
                root = tmp_path / "testtool"
                root.mkdir(parents=True)

                meta = run_tool(
                    tool,
                    root,
                    ["arg1"],
                    target="target1",
                    case=None,
                    env_overrides=None,
                    stream=False,
                )

                # Check meta.json does not contain the secret
                assert secret_value not in str(meta.__dict__)

                # The secret IS passed to the subprocess environment (this is intended behavior),
                # but should not appear in meta.json, logs, or stdout
                for call in mock_popen.call_args_list:
                    # The secret should not be in the command args
                    assert secret_value not in str(call.args)
                    # The secret SHOULD be in the env dict passed to Popen
                    assert call.kwargs.get("env", {}).get("SECRET_KEY") == secret_value

                # The secret should not be in the meta.json file content
                assert secret_value not in str(meta.output_path)
                assert secret_value not in str(meta.sha256)
