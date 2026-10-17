"""Process execution utilities."""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


class InstallError(Exception):
    """Raised when installation fails."""

    pass


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INPUT"] = "1"
    return env


def _run_with_cleanup(
    args: list[str],
    *,
    log: Path,
    cwd: Path | None = None,
    timeout: int = 900,
    stream: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a command with proper cleanup on KeyboardInterrupt.

    Creates the child in its own process group so we can kill it and all its
    descendants on interrupt.
    """
    cmd_str = " ".join(args)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", errors="replace") as f:
        f.write(f"$ {cmd_str}\n")
    extra_env = env
    env = _base_env()
    if extra_env:
        env.update(extra_env)

    # Use Popen with start_new_session to create a new process group
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE if not stream else None,
        stderr=subprocess.PIPE if not stream else None,
        text=True if not stream else False,
    )

    try:
        if stream:
            # Output went to the terminal, so there is nothing to capture, but the
            # exit code still decides whether the step failed.
            proc.wait(timeout=timeout)
            return subprocess.CompletedProcess(args, proc.returncode, None, None)
        else:
            stdout, stderr = proc.communicate(timeout=timeout)
            return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        # Kill the entire process group on timeout
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.wait(timeout=5)
        raise InstallError(f"timed out after {timeout} seconds: {args[0]}") from None
    except BaseException:
        # On any other exception (including KeyboardInterrupt), kill the process group
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.wait(timeout=5)
        raise


def run(
    args: list[str],
    *,
    log: Path,
    cwd: Path | None = None,
    timeout: int = 900,
    stream: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    """Run a command, logging output to a file. env adds to the usual environment."""
    result = _run_with_cleanup(args, log=log, cwd=cwd, timeout=timeout, stream=stream, env=env)
    with log.open("a", encoding="utf-8", errors="replace") as f:
        f.write(result.stdout or "")
        f.write(result.stderr or "")
        if stream and result.returncode != 0:
            f.write(f"(exit code {result.returncode}; output was shown on the terminal)\n")
    if result.returncode != 0:
        _raise_from_log(args[0], log)


def run_capture(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 60,
) -> str:
    """Run a command and return stdout, raising on failure."""
    env = _base_env()
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise InstallError(f"{args[0]} failed: {e.stderr.strip() or e.stdout.strip()}") from e
    except subprocess.TimeoutExpired as e:
        raise InstallError(f"timed out after {timeout} seconds: {args[0]}") from e


def _raise_from_log(cmd_name: str, log: Path) -> None:
    """Read the last 15 lines of the log and raise InstallError."""
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = "\n".join(lines[-15:])
    raise InstallError(f"{cmd_name} failed:\n{tail}\nlog: {log}")
