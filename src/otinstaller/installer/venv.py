"""Virtual environment utilities."""

from __future__ import annotations

import sys
from pathlib import Path

from otinstaller.installer.process import run


def create_venv(path: Path, log: Path, stream: bool = False, upgrade_pip: bool = True) -> None:
    """Create a virtual environment at the given path, then bring its pip up to date.

    The pip that venv bundles can be old (Ubuntu 22.04 ships 22.0). Old pips install
    packages that have no pyproject.toml with 'setup.py install', which leaves their
    commands with a '#!python' first line that the shell can't run (ivre is one).
    A current pip builds a wheel instead. If the upgrade fails, for example behind a
    mirror without pip on it, the bundled pip is kept and the install goes on.
    """
    run(
        [sys.executable, "-m", "venv", str(path)],
        log=log,
        stream=stream,
    )
    if upgrade_pip:
        try:
            run(
                [str(path / "bin" / "python"), "-m", "pip", "install", "--upgrade", "pip"],
                log=log,
                stream=stream,
                timeout=300,
            )
        except Exception as exc:  # keep going with the bundled pip
            with log.open("a", encoding="utf-8", errors="replace") as f:
                f.write(f"\nnote: could not upgrade pip, using the bundled one ({exc})\n")


def venv_python(root: Path) -> Path:
    """Return the path to the Python executable in the venv."""
    return root / "venv" / "bin" / "python"


def venv_bin(root: Path, name: str) -> Path:
    """Return the path to a binary in the venv's bin directory."""
    return root / "venv" / "bin" / name
