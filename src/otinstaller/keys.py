"""API key management: loading and distributing keys to tools."""

from __future__ import annotations

from pathlib import Path

from otinstaller.config import get_env_file
from otinstaller.registry import Tool


def get_env_file_path() -> Path:
    """Return the path to the .env file."""
    return get_env_file()


def load_env_file() -> dict[str, str]:
    """Load and parse the .env file.

    Parses KEY=VALUE lines, skipping blank lines and comments.
    Strips whitespace and optional surrounding quotes from values.
    Returns empty dict if file doesn't exist.
    Silently skips malformed lines.
    """
    path = get_env_file_path()
    if not path.exists():
        return {}

    result: dict[str, str] = {}
    content = path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes if present
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def keys_for_tool(tool: Tool, available: dict[str, str]) -> dict[str, str]:
    """Return only the keys that the tool declares needing."""
    needed = set(tool.api_keys.required) | set(tool.api_keys.optional)
    return {k: v for k, v in available.items() if k in needed}


def missing_required_keys(tool: Tool, available: dict[str, str]) -> list[str]:
    """Return list of required keys that are missing from available."""
    return [k for k in tool.api_keys.required if k not in available]
