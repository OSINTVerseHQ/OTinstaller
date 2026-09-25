"""Runner tests."""

import time
from unittest.mock import MagicMock, patch

import pytest

from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool
from otinstaller.runner import run_tool, run_tools_parallel


def make_fake_tool(name: str) -> Tool:
    """Create a minimal fake tool for testing."""
    return Tool(
        name=name,
        display_name=name.title(),
        description=f"Fake tool {name}",
        install=Install(method="pip", package=name),
        entrypoint=Entrypoint(command=name),
        api_keys=ApiKeys(),
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

    def mock_run_tool(tool, root, extra_args, *, target, case, env_overrides, stream):
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

    def mock_run_tool(tool, root, extra_args, *, target, case, env_overrides, stream):
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

    def mock_run_tool(tool, root, extra_args, *, target, case, env_overrides, stream):
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
