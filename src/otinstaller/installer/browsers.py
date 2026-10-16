"""Playwright browsers for tools that drive a headless browser.

The browser goes into the tool's own folder, not the shared ~/.cache/ms-playwright,
so removing the tool removes it too and tools never share or break each other's
browser. The same path is given to the tool when it runs.
"""

from __future__ import annotations

from pathlib import Path

from otinstaller.installer.process import run
from otinstaller.installer.venv import venv_python
from otinstaller.registry import Tool

BROWSERS_DIR = "playwright-browsers"


def browsers_path(root: Path) -> Path:
    return root / BROWSERS_DIR


def tool_env(tool: Tool, root: Path) -> dict[str, str]:
    """Environment a tool needs at run time (empty for most tools)."""
    if tool.install.playwright_browsers:
        return {"PLAYWRIGHT_BROWSERS_PATH": str(browsers_path(root))}
    return {}


def install_browsers(tool: Tool, root: Path, log: Path, stream: bool = False) -> None:
    """Download the tool's Playwright browsers with the Playwright in its venv."""
    for browser in tool.install.playwright_browsers:
        args = [str(venv_python(root)), "-m", "playwright", "install"]
        if browser == "chromium":
            # Tools run Chromium headless, which only needs the smaller headless shell
            args.append("--only-shell")
        args.append(browser)
        run(args, log=log, stream=stream, env=tool_env(tool, root), timeout=1200)
