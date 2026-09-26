"""Tool execution: running tools in their virtualenvs and capturing output."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from otinstaller.config import get_results_dir
from otinstaller.installer.venv import venv_bin, venv_python
from otinstaller.keys import keys_for_tool, load_env_file, missing_required_keys
from otinstaller.registry import Tool
from otinstaller.results import RunMeta, hash_file, results_paths, write_meta


def build_command(tool: Tool, root: Path, extra_args: list[str]) -> list[str]:
    """Build the command to run a tool."""
    if tool.entrypoint.command:
        return [str(venv_bin(root, tool.entrypoint.command)), *extra_args]
    elif tool.entrypoint.script:
        return [str(venv_python(root)), str(root / "src" / tool.entrypoint.script), *extra_args]
    else:
        raise ValueError(f"tool {tool.name} has no entrypoint")


def _redact_api_keys(command: list[str], tool: Tool) -> list[str]:
    """Redact API key values from command for meta file."""
    # API keys are passed via environment, not command line, but just in case
    redacted = []
    for arg in command:
        key_names = tool.api_keys.required + tool.api_keys.optional
        if any(arg.startswith(f"{key}=") for key in key_names):
            redacted.append("***")
        else:
            redacted.append(arg)
    return redacted


def run_tool(
    tool: Tool,
    root: Path,
    extra_args: list[str],
    *,
    target: str | None,
    case: str | None,
    env_overrides: dict[str, str] | None,
    stream: bool,
    cancel_event: asyncio.Event | None = None,
) -> RunMeta:
    """Run a tool and return RunMeta. Does not raise on tool exit code."""
    # Determine target
    if target is None:
        target = extra_args[0] if extra_args else "unspecified"

    output_path, meta_path = results_paths(tool.name, target, case)

    # Build command
    cmd = build_command(tool, root, extra_args)

    # Prepare environment
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    # Inject API keys for this tool
    all_keys = load_env_file()
    tool_keys = keys_for_tool(tool, all_keys)
    if tool_keys:
        env.update(tool_keys)
    missing = missing_required_keys(tool, all_keys)
    if missing:
        sys.stderr.write(f"warning: {tool.name} is missing required key(s): {', '.join(missing)}\n")

    # Start timing
    started_at = datetime.now(timezone.utc)
    started_at_str = started_at.isoformat()

    # Open output file for writing
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run the process in its own process group
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        # Stream output to file (and terminal if stream=True)
        with output_path.open("wb") as f:
            if proc.stdout:
                for line in iter(proc.stdout.readline, b""):
                    f.write(line)
                    if stream:
                        sys.stdout.buffer.write(line)
                        sys.stdout.buffer.flush()
                    # Check for cancellation
                    if cancel_event is not None and cancel_event.is_set():
                        break

        # Wait for process to complete (or kill if cancelled)
        if cancel_event is not None and cancel_event.is_set():
            # Kill the entire process group
            os.killpg(os.getpgid(proc.pid), 9)  # SIGKILL
            proc.wait()
            exit_code = -9  # SIGKILL
        else:
            exit_code = proc.wait()
    except KeyboardInterrupt:
        # Kill the entire process group on interrupt
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except ProcessLookupError:
            pass
        proc.wait()
        exit_code = -9
        raise

    ended_at = datetime.now(timezone.utc)
    ended_at_str = ended_at.isoformat()
    duration = (ended_at - started_at).total_seconds()

    # Determine status
    if exit_code == 0:
        status = "complete"
    elif exit_code < 0:
        # Negative exit code means killed by signal
        status = "interrupted"
    else:
        status = "failed"

    # Hash the output file
    sha256 = hash_file(output_path)
    bytes_size = output_path.stat().st_size

    # Build meta
    redacted_cmd = _redact_api_keys(cmd, tool)
    meta = RunMeta(
        command=redacted_cmd,
        tool=tool.name,
        tool_version="",  # Will be filled by caller
        target=target,
        case=case,
        started_at=started_at_str,
        ended_at=ended_at_str,
        duration_seconds=duration,
        exit_code=exit_code,
        status=status,
        output_path=str(output_path.relative_to(get_results_dir())),
        sha256=sha256,
        bytes=bytes_size,
    )

    write_meta(meta, meta_path)
    return meta


async def run_tools_parallel(
    tools: list[Tool],
    roots: dict[str, Path],
    extra_args: list[str],
    *,
    target: str | None,
    case: str | None,
    max_parallel: int,
    stream: bool,
) -> list[RunMeta]:
    """Run multiple tools in parallel with a concurrency limit.

    Each tool runs in its own thread via asyncio.to_thread, preserving the
    exact behavior of run_tool. Returns results in the same order as the
    input tools list.
    """
    cancel_event = asyncio.Event()
    semaphore = asyncio.Semaphore(max_parallel)

    async def run_one(tool: Tool) -> RunMeta:
        root = roots[tool.name]
        async with semaphore:
            return await asyncio.to_thread(
                run_tool,
                tool,
                root,
                extra_args,
                target=target,
                case=case,
                env_overrides=None,
                stream=stream,
                cancel_event=cancel_event,
            )

    # Use gather with return_exceptions=True so one failure doesn't cancel others
    tasks = [run_one(t) for t in tools]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Signal cancellation to all running tools
        cancel_event.set()
        # Wait for tasks to complete (they should exit quickly after seeing cancel_event)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Re-raise to signal interruption to caller
        raise

    # Convert exceptions to failed RunMeta objects
    final_results: list[RunMeta] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Build a minimal failed RunMeta for the exception case
            tool = tools[i]
            output_path, meta_path = results_paths(tool.name, target or "unspecified", case)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"Exception: {result}")

            from datetime import datetime, timezone

            from otinstaller.results import hash_file

            ended_at = datetime.now(timezone.utc).isoformat()
            meta = RunMeta(
                command=["<exception>"],
                tool=tool.name,
                tool_version="",
                target=target or "unspecified",
                case=case,
                started_at=ended_at,
                ended_at=ended_at,
                duration_seconds=0.0,
                exit_code=-1,
                status="failed",
                output_path=str(output_path.relative_to(get_results_dir())),
                sha256=hash_file(output_path),
                bytes=output_path.stat().st_size,
            )
            write_meta(meta, meta_path)
            final_results.append(meta)
        else:
            final_results.append(result)

    return final_results
