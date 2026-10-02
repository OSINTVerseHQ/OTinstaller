"""Pip-based installation."""

from __future__ import annotations

from pathlib import Path

from otinstaller.installer.process import run
from otinstaller.installer.venv import create_venv, venv_python
from otinstaller.registry import Tool


def install_pip(
    tool: Tool,
    root: Path,
    log: Path,
    stream: bool = False,
) -> None:
    """Install a tool via pip into its virtualenv."""
    venv_dir = root / "venv"
    create_venv(venv_dir, log, stream=stream)

    package = tool.install.package
    if not package:
        raise ValueError("pip install requires a package name")

    if package.startswith("-"):
        raise ValueError(f"refusing to install package starting with '-': {package}")

    python = venv_python(root)

    spec = package
    if tool.install.version:
        spec = f"{package}=={tool.install.version}"
    run(
        [str(python), "-m", "pip", "install", spec],
        log=log,
        stream=stream,
    )

    for extra_pkg in tool.install.extra_packages:
        if extra_pkg.startswith("-"):
            raise ValueError(f"refusing to install extra package starting with '-': {extra_pkg}")
        run(
            [str(python), "-m", "pip", "install", extra_pkg],
            log=log,
            stream=stream,
        )
