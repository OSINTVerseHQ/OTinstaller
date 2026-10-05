"""Compare tool Python-version constraints against the running interpreter."""

from __future__ import annotations

import sys

from otinstaller.registry import REQUIRES_PYTHON_RE, Tool


def current_python() -> tuple[int, ...]:
    """Version of the running interpreter as a tuple of ints."""
    return sys.version_info[:3]


def _satisfied(spec: str, version: tuple[int, ...]) -> bool:
    match = REQUIRES_PYTHON_RE.match(spec)
    if not match:
        return False
    op, bound_text = match.groups()
    bound = tuple(int(part) for part in bound_text.split("."))
    length = max(len(version), len(bound))
    current = version + (0,) * (length - len(version))
    wanted = bound + (0,) * (length - len(bound))
    if op == "<":
        return current < wanted
    if op == "<=":
        return current <= wanted
    if op == ">":
        return current > wanted
    if op == ">=":
        return current >= wanted
    if op == "==":
        return current == wanted
    return current != wanted


def incompatibility(tool: Tool, version: tuple[int, ...] | None = None) -> str | None:
    """Message when this Python cannot install the tool, else None."""
    if not tool.requires_python:
        return None
    if version is None:
        version = current_python()
    if _satisfied(tool.requires_python, version):
        return None
    running = ".".join(str(part) for part in version)
    return (
        f"{tool.name} requires Python {tool.requires_python} (you are running {running}). "
        "Install Python 3.12 and recreate your venv — see README."
    )
