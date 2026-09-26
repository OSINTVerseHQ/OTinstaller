"""Core installation logic."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from otinstaller.config import ensure_dir, get_logs_dir, get_tools_dir, tool_dir
from otinstaller.installer.git_install import install_git
from otinstaller.installer.pip_install import install_pip
from otinstaller.installer.process import InstallError, run_capture
from otinstaller.registry import Tool
from otinstaller.state import (
    InstalledTool,
    add_installed,
    get_installed,
    job_end,
    job_start,
    remove_installed,
)


class AlreadyInstalled(InstallError):
    """Raised when trying to install a tool that is already installed."""

    pass


def safe_rmtree(path: Path) -> None:
    """Safely remove a directory tree.

    - Does nothing if path doesn't exist
    - If path is a symlink, only unlinks it
    - Refuses to remove the tools directory itself
    - Refuses to remove paths outside the tools directory
    """
    if not path.exists():
        return

    # Resolve to handle symlinks
    try:
        resolved = path.resolve()
    except OSError:
        return

    tools_dir = get_tools_dir().resolve()

    # Refuse to remove the tools directory itself
    if resolved == tools_dir:
        raise InstallError("refusing to remove tools directory")

    # Refuse to remove paths outside the tools directory
    try:
        resolved.relative_to(tools_dir)
    except ValueError as e:
        raise InstallError(f"refusing to remove path outside tools directory: {path}") from e

    if path.is_symlink() or (resolved != path and path.exists() and path.is_symlink()):
        # It's a symlink - just unlink it
        path.unlink()
        return

    shutil.rmtree(path, ignore_errors=False)


def _get_version_pip(tool: Tool, root: Path) -> str:
    """Get version from pip show."""
    try:
        from otinstaller.installer.venv import venv_python

        python = venv_python(root)
        output = run_capture([str(python), "-m", "pip", "show", tool.install.package])
        for line in output.splitlines():
            if line.startswith("Version: "):
                return line.split("Version: ", 1)[1].strip()
    except Exception:
        pass
    return "unknown"


def _get_version_git(commit: str) -> str:
    """Get version from git commit (first 12 chars)."""
    if commit:
        return commit[:12]
    return "unknown"


def get_latest_pip_version(package: str) -> str | None:
    """Query PyPI for the latest version of a package.

    Returns None on any network error or if package not found.
    """
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "otinstaller"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data["info"]["version"]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError):
        return None


def get_latest_git_ref(url: str) -> str | None:
    """Get the latest commit hash for a git repository's default branch.

    Uses git ls-remote to avoid a full clone. Returns None on any error.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Output format: <hash>\tHEAD
            return result.stdout.strip().split("\t")[0]
    except (subprocess.SubprocessError, OSError, IndexError):
        pass
    return None


def versions_differ(current: str, latest: str) -> bool:
    """Check if two versions differ.

    For pip: simple string inequality (versions are normalized by pip).
    For git: compares full commit hashes.
    """
    return current != latest


def install_tool(
    tool: Tool,
    *,
    force: bool = False,
    stream: bool = False,
) -> InstalledTool:
    """Install a tool into its own virtualenv."""
    # Check if already installed
    existing = get_installed(tool.name)
    if existing and not force:
        raise AlreadyInstalled(f"{tool.name} is already installed (use --force to reinstall)")

    root = tool_dir(tool.name)

    # Clean up any leftover directory
    if root.exists():
        safe_rmtree(root)

    if force and existing:
        remove_installed(tool.name)

    # Create root and log directory
    ensure_dir(root)
    ensure_dir(get_logs_dir())
    log = get_logs_dir() / f"install-{tool.name}.log"
    if log.exists():
        log.unlink()

    # Record job start for crash detection
    marker = job_start("install", tool.name)

    try:
        if tool.install.method == "pip":
            install_pip(tool, root, log, stream=stream)
            version = _get_version_pip(tool, root)
            commit = None
            source = tool.install.package or "unknown"
        elif tool.install.method == "git":
            commit = install_git(tool, root, log, stream=stream)
            version = _get_version_git(commit)
            source = tool.install.url or "unknown"
        else:
            raise InstallError(f"unknown install method: {tool.install.method}")

        # Verify entrypoint
        from otinstaller.installer.venv import venv_bin

        if tool.entrypoint.command:
            entry_path = venv_bin(root, tool.entrypoint.command)
            if not entry_path.exists() or not os.access(entry_path, os.X_OK):
                raise InstallError(
                    f"installed, but the entrypoint '{tool.entrypoint.command}' was not found"
                )
            entry_command = tool.entrypoint.command
            entry_script = None
        elif tool.entrypoint.script:
            script_path = root / "src" / tool.entrypoint.script
            if not script_path.is_file():
                raise InstallError(
                    f"installed, but the entrypoint '{tool.entrypoint.script}' was not found"
                )
            entry_command = None
            entry_script = tool.entrypoint.script
        else:
            raise InstallError("no entrypoint defined")

        # Build InstalledTool
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        installed = InstalledTool(
            name=tool.name,
            version=version,
            method=tool.install.method,
            source=source,
            ref=tool.install.ref,
            commit=commit,
            entry_command=entry_command,
            entry_script=entry_script,
            installed_at=now,
            updated_at=now,
        )

        add_installed(installed)
        job_end(marker.job_id)
        return installed

    except BaseException:
        # Clean up on any failure
        if root.exists():
            safe_rmtree(root)
        job_end(marker.job_id)
        raise


def remove_tool(name: str) -> bool:
    """Remove an installed tool."""
    installed = get_installed(name)
    if not installed:
        return False

    root = tool_dir(name)
    if root.exists():
        safe_rmtree(root)

    remove_installed(name)
    return True
