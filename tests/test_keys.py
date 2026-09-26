"""Tests for keys module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from otinstaller.keys import (
    get_env_file_path,
    keys_for_tool,
    load_env_file,
    missing_required_keys,
)
from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool


def make_fake_tool(
    name: str = "testtool",
    required: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
) -> Tool:
    """Create a minimal fake tool for testing."""
    return Tool(
        name=name,
        display_name=name.title(),
        description=f"Fake tool {name}",
        install=Install(method="pip", package=name),
        entrypoint=Entrypoint(command=name),
        api_keys=ApiKeys(required=required, optional=optional),
    )


def test_get_env_file_path():
    """get_env_file_path returns the correct path."""
    with patch("otinstaller.keys.get_env_file") as mock_get_env_file:
        mock_get_env_file.return_value = Path("/home/user/.otinstaller/.env")
        path = get_env_file_path()
        assert path == Path("/home/user/.otinstaller/.env")


def test_load_env_file_missing():
    """load_env_file returns empty dict for missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        with patch("otinstaller.keys.get_env_file_path", return_value=env_file):
            result = load_env_file()
            assert result == {}


def test_load_env_file_basic():
    """load_env_file parses KEY=VALUE correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n")
        with patch("otinstaller.keys.get_env_file_path", return_value=env_file):
            result = load_env_file()
            assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_load_env_file_skips_comments_and_blanks():
    """load_env_file skips comments and blank lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("# comment\n\nKEY1=value1\n# another comment\nKEY2=value2\n")
        with patch("otinstaller.keys.get_env_file_path", return_value=env_file):
            result = load_env_file()
            assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_load_env_file_strips_quotes():
    """load_env_file strips surrounding quotes from values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("KEY1=\"value1\"\nKEY2='value2'\nKEY3=value3\n")
        with patch("otinstaller.keys.get_env_file_path", return_value=env_file):
            result = load_env_file()
            assert result == {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}


def test_load_env_file_skips_malformed():
    """load_env_file skips malformed lines silently."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("KEY1=value1\nmalformed line\nKEY2=value2\n")
        with patch("otinstaller.keys.get_env_file_path", return_value=env_file):
            result = load_env_file()
            assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_keys_for_tool():
    """keys_for_tool returns only keys the tool declared."""
    tool = make_fake_tool("testtool", required=("KEY1",), optional=("KEY2",))
    available = {"KEY1": "val1", "KEY2": "val2", "KEY3": "val3"}
    result = keys_for_tool(tool, available)
    assert result == {"KEY1": "val1", "KEY2": "val2"}


def test_keys_for_tool_empty():
    """keys_for_tool returns empty dict for tool with no api_keys."""
    tool = make_fake_tool("testtool")
    available = {"KEY1": "val1", "KEY2": "val2"}
    result = keys_for_tool(tool, available)
    assert result == {}


def test_missing_required_keys():
    """missing_required_keys returns missing required keys."""
    tool = make_fake_tool("testtool", required=("KEY1", "KEY2"), optional=("KEY3",))
    missing = missing_required_keys(tool, {"KEY1": "val1"})
    assert missing == ["KEY2"]


def test_missing_required_keys_none_missing():
    """missing_required_keys returns empty list when all present."""
    tool = make_fake_tool("testtool", required=("KEY1", "KEY2"))
    available = {"KEY1": "val1", "KEY2": "val2"}
    missing = missing_required_keys(tool, available)
    assert missing == []


def test_missing_required_keys_all_missing():
    """missing_required_keys returns all when none present."""
    tool = make_fake_tool("testtool", required=("KEY1", "KEY2"))
    available = {}
    missing = missing_required_keys(tool, available)
    assert missing == ["KEY1", "KEY2"]
