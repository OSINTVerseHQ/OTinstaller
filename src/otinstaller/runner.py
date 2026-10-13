"""Tool execution: running tools in their virtualenvs and capturing output."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from otinstaller.config import get_results_dir
from otinstaller.installer.venv import venv_bin, venv_python
from otinstaller.keys import keys_for_tool, load_env_file, missing_required_keys
from otinstaller.registry import Tool
from otinstaller.results import RunMeta, hash_file, results_paths, write_meta
from otinstaller.state import job_end, job_start


def build_command(tool: Tool, root: Path, extra_args: list[str]) -> list[str]:
    """Build the command to run a tool."""
    if tool.entrypoint.command:
        return [str(venv_bin(root, tool.entrypoint.command)), *extra_args]
    elif tool.entrypoint.script:
        return [str(venv_python(root)), str(root / "src" / tool.entrypoint.script), *extra_args]
    else:
        raise ValueError(f"tool {tool.name} has no entrypoint")


# Flags whose value is a credential. Tools take cookies, tokens and passwords on the
# command line, and the full command ends up in .meta.json.
_SECRET_FLAG_RE = re.compile(
    r"^--?[A-Za-z0-9_-]*(cookie|token|passw|secret|api[-_]?key|api[-_]?hash|session)[A-Za-z0-9_-]*$",
    re.IGNORECASE,
)


def is_secret_flag(arg: str) -> bool:
    return bool(_SECRET_FLAG_RE.match(arg.partition("=")[0]))


def _redact_api_keys(command: list[str], tool: Tool) -> list[str]:
    """Redact credential values from a command before it is written to the meta file."""
    key_names = tool.api_keys.required + tool.api_keys.optional
    redacted: list[str] = []
    hide_next = False
    for arg in command:
        if hide_next:
            redacted.append("***")
            hide_next = False
            continue
        flag, sep, _value = arg.partition("=")
        if sep and _SECRET_FLAG_RE.match(flag):
            redacted.append(f"{flag}=***")
        elif any(arg.startswith(f"{key}=") for key in key_names):
            redacted.append("***")
        else:
            redacted.append(arg)
            hide_next = bool(_SECRET_FLAG_RE.match(arg))
    return redacted


def run_in_pty(
    cmd: list[str],
    *,
    env: dict[str, str] | None,
    cwd: Path | None,
    sink: BinaryIO,
    stdin_fd: int | None,
) -> int:
    """Run cmd on a pseudo-terminal, copying its output to the terminal and to sink.

    Prompts that do not end in a newline (logins, menus, setup wizards) only show up
    when the tool writes to a terminal, so interactive tools run this way.
    """
    import fcntl
    import pty
    import select
    import termios
    import tty

    master, slave = pty.openpty()
    if sys.stdout.isatty():
        size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, size)

    def make_controlling_tty() -> None:
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=cwd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        preexec_fn=make_controlling_tty,
        close_fds=True,
    )
    os.close(slave)

    saved_mode = None
    if stdin_fd is not None and os.isatty(stdin_fd):
        saved_mode = termios.tcgetattr(stdin_fd)
        tty.setraw(stdin_fd)

    readers = [master] if stdin_fd is None else [master, stdin_fd]
    try:
        while True:
            ready, _, _ = select.select(readers, [], [])
            if master in ready:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    data = b""
                if not data:
                    break
                sink.write(data)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            if stdin_fd is not None and stdin_fd in ready:
                data = os.read(stdin_fd, 1024)
                if data:
                    os.write(master, data)
                else:
                    readers.remove(stdin_fd)
    finally:
        if saved_mode is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, saved_mode)
        os.close(master)
    return proc.wait()


def _run_captured(
    cmd: list[str],
    env: dict[str, str],
    cwd: Path | None,
    output_path: Path,
    stream: bool,
    cancel_event: asyncio.Event | None,
    job_id: str,
) -> int:
    # Run the process in its own process group
    proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=cwd,
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
            return -9  # SIGKILL
        return proc.wait()
    except KeyboardInterrupt:
        # Kill the entire process group on interrupt
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except ProcessLookupError:
            pass
        proc.wait()
        job_end(job_id)
        raise


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
    interactive: bool = False,
) -> RunMeta:
    """Run a tool and return RunMeta. Does not raise on tool exit code.

    interactive=True runs the tool on a pseudo-terminal wired to this terminal;
    only use it for a single tool when stdin and stdout are terminals.
    """
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

    # Record job start for crash detection
    marker = job_start("run", tool.name, target)

    # Start timing
    started_at = datetime.now(timezone.utc)
    started_at_str = started_at.isoformat()

    # Open output file for writing
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cwd = root / "src" if tool.run_from_source else None

    if interactive:
        # Ctrl-C reaches the tool through the terminal, so there is no
        # KeyboardInterrupt to handle here.
        with output_path.open("wb") as f:
            exit_code = run_in_pty(cmd, env=env, cwd=cwd, sink=f, stdin_fd=sys.stdin.fileno())
    else:
        exit_code = _run_captured(cmd, env, cwd, output_path, stream, cancel_event, marker.job_id)

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
    job_end(marker.job_id)
    return meta


async def run_tools_parallel(
    tools: list[Tool],
    roots: dict[str, Path],
    extra_args: list[str] | dict[str, list[str]],
    *,
    target: str | None,
    case: str | None,
    max_parallel: int,
    stream: bool,
    status_queue: asyncio.Queue[tuple] | None = None,
) -> list[RunMeta]:
    """Run multiple tools in parallel with a concurrency limit.

    Each tool runs in its own thread via asyncio.to_thread, preserving the
    exact behavior of run_tool. Returns results in the same order as the
    input tools list.

    extra_args can be a list (same args for all tools) or a dict mapping
    tool name to its specific extra args list.

    status_queue is optional one-way status reporting: workers put
    ("running", name), ("done", name, exit_code) or ("error", name)
    tuples onto it for a display task to consume. It is unbounded, so
    producers never block on it.
    """
    cancel_event = asyncio.Event()
    semaphore = asyncio.Semaphore(max_parallel)

    def get_extra_args(tool_name: str) -> list[str]:
        if isinstance(extra_args, dict):
            return extra_args.get(tool_name, [])
        return extra_args

    async def run_one(tool: Tool) -> RunMeta:
        root = roots[tool.name]
        tool_extra_args = get_extra_args(tool.name)
        async with semaphore:
            if status_queue is not None:
                await status_queue.put(("running", tool.name))
            try:
                result = await asyncio.to_thread(
                    run_tool,
                    tool,
                    root,
                    tool_extra_args,
                    target=target,
                    case=case,
                    env_overrides=None,
                    stream=stream,
                    cancel_event=cancel_event,
                )
            except Exception:
                if status_queue is not None:
                    await status_queue.put(("error", tool.name))
                raise
            if status_queue is not None:
                await status_queue.put(("done", tool.name, result.exit_code))
            return result

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
