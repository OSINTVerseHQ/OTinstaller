"""Installer core tests."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from otinstaller.config import get_tools_dir
from otinstaller.installer import (
    AlreadyInstalled,
    InstallError,
    PythonVersionError,
    install_tool,
    remove_tool,
)
from otinstaller.registry import Entrypoint, Install, Tool
from otinstaller.state import InstalledTool, add_installed, get_installed


def make_tool_pip(name="testtool", package="testpkg", version=None):
    return Tool(
        name=name,
        display_name="Test Tool",
        description="A test tool",
        install=Install(method="pip", package=package, version=version),
        entrypoint=Entrypoint(command=name),
        capabilities=[],
        tier="community",
    )


def make_tool_git(
    name="testtool",
    url="https://github.com/user/repo",
    ref=None,
    requirements=None,
    as_package=False,
):
    return Tool(
        name=name,
        display_name="Test Tool",
        description="A test tool",
        install=Install(
            method="git",
            url=url,
            ref=ref,
            requirements=requirements,
            as_package=as_package,
        ),
        entrypoint=Entrypoint(command=name),
        capabilities=[],
        tier="community",
    )


def _mock_entrypoint_check():
    """Context manager to mock entrypoint existence and access checks."""
    from contextlib import ExitStack

    stack = ExitStack()
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.__str__ = lambda self: "/fake/venv/bin/testtool"
    mock_python = MagicMock()
    mock_python.exists.return_value = True
    mock_python.__str__ = lambda self: "/fake/venv/bin/python"
    stack.enter_context(patch("otinstaller.installer.venv.venv_bin", return_value=mock_path))
    stack.enter_context(
        patch("otinstaller.installer.pip_install.venv_python", return_value=mock_python)
    )
    stack.enter_context(
        patch("otinstaller.installer.git_install.venv_python", return_value=mock_python)
    )
    stack.enter_context(patch("os.access", return_value=True))
    return stack


def test_pip_spec_exact_command(monkeypatch, tmp_path):
    """pip spec is exactly [python, -m, pip, install, package] and adds ==version when pinned."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg", "1.2.3")

    with patch("otinstaller.installer.pip_install.run") as mock_run:
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="1.2.3"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    # Verify pip was called with correct args
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == str(Path("/fake/venv/bin/python"))
    assert args[1:5] == ["-m", "pip", "install", "testpkg==1.2.3"]


def test_pip_spec_without_version(monkeypatch, tmp_path):
    """pip spec without version doesn't add ==version."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    with patch("otinstaller.installer.pip_install.run") as mock_run:
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="1.2.3"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[4] == "testpkg"  # No ==version


def test_git_clone_depth_one_no_ref(monkeypatch, tmp_path):
    """git clone uses --depth 1 and -- before url when there is no ref."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_git("testtool", "https://github.com/user/repo")

    with patch("otinstaller.installer.git_install.run") as mock_run:
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.git_install.run_capture", return_value="abc123"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    # Find the git clone call
    clone_calls = [
        c for c in mock_run.call_args_list if c.args[0][0] == "git" and c.args[0][1] == "clone"
    ]
    assert len(clone_calls) == 1
    args = clone_calls[0].args[0]
    expected = ["git", "clone", "--depth", "1", "--", "https://github.com/user/repo"]
    expected.append(str(get_tools_dir() / "testtool" / "src"))
    assert args == expected


def test_git_clone_checkout_with_ref(monkeypatch, tmp_path):
    """git clone plus checkout when there is a ref."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_git("testtool", "https://github.com/user/repo", ref="v1.0")

    with patch("otinstaller.installer.git_install.run") as mock_run:
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.git_install.run_capture", return_value="abc123"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    # Find git clone and checkout calls
    clone_calls = [
        c for c in mock_run.call_args_list if c.args[0][0] == "git" and c.args[0][1] == "clone"
    ]
    checkout_calls = [
        c for c in mock_run.call_args_list if c.args[0][0] == "git" and "checkout" in c.args[0]
    ]
    assert len(clone_calls) == 1
    assert len(checkout_calls) == 1
    clone_args = clone_calls[0].args[0]
    expected_clone = ["git", "clone", "--", "https://github.com/user/repo"]
    expected_clone.append(str(get_tools_dir() / "testtool" / "src"))
    assert clone_args == expected_clone
    checkout_args = checkout_calls[0].args[0]
    expected_checkout = ["git", "-C", str(get_tools_dir() / "testtool" / "src"), "checkout", "v1.0"]
    assert checkout_args == expected_checkout


def test_git_requirements_path_escaping_dotdot(monkeypatch, tmp_path):
    """a requirements path escaping the clone (..) raises InstallError."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_git(
        "testtool", "https://github.com/user/repo", requirements="../requirements.txt"
    )

    with pytest.raises(InstallError, match="requirements path escapes clone"):
        install_tool(tool)


def test_git_requirements_path_escaping_symlink(monkeypatch, tmp_path):
    """a requirements path that is a symlink escaping the clone raises InstallError."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_git(
        "testtool", "https://github.com/user/repo", requirements="requirements.txt"
    )

    # Create a mock where the requirements file resolves outside the clone
    with patch("otinstaller.installer.git_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.git_install.run_capture", return_value="abc123"):
                # Mock Path.resolve to return outside path for req_path,
                # but allow other resolves to pass through
                original_resolve = Path.resolve

                def mock_resolve(self):
                    # Check if this is the requirements file path (src_dir / requirements)
                    if "requirements.txt" in str(self):
                        return Path("/etc/passwd")  # Outside the clone!
                    return original_resolve(self)

                with patch("pathlib.Path.resolve", mock_resolve):
                    with pytest.raises(InstallError, match="requirements path escapes clone"):
                        install_tool(tool)


def test_missing_entrypoint_leaves_no_dir_or_db(monkeypatch, tmp_path):
    """a missing entrypoint leaves no directory and no DB row."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    with patch("otinstaller.installer.pip_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="1.2.3"):
                with patch("otinstaller.installer.venv.venv_bin") as mock_venv_bin:
                    mock_path = MagicMock()
                    mock_path.exists.return_value = False
                    mock_path.__str__ = lambda self: "/fake/venv/bin/nonexistent"
                    mock_venv_bin.return_value = mock_path
                    with pytest.raises(InstallError, match="entrypoint.*not found"):
                        install_tool(tool)

    # Check no directory left
    assert not (get_tools_dir() / "testtool").exists()
    # Check no DB row
    assert get_installed("testtool") is None


def test_failure_cleans_up(monkeypatch, tmp_path):
    """failure cleans up the tool directory."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    with patch("otinstaller.installer.pip_install.run", side_effect=InstallError("pip failed")):
        with patch("otinstaller.installer.venv.create_venv"):
            with _mock_entrypoint_check():
                with pytest.raises(InstallError):
                    install_tool(tool)

    # Directory should be cleaned up
    assert not (get_tools_dir() / "testtool").exists()


def test_keyboard_interrupt_cleans_up(monkeypatch, tmp_path):
    """KeyboardInterrupt cleans up the tool directory."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    with patch("otinstaller.installer.pip_install.run", side_effect=KeyboardInterrupt):
        with patch("otinstaller.installer.venv.create_venv"):
            with _mock_entrypoint_check():
                with pytest.raises(KeyboardInterrupt):
                    install_tool(tool)

    # Directory should be cleaned up
    assert not (get_tools_dir() / "testtool").exists()


def test_incompatible_python_fails_before_any_install_work(monkeypatch, tmp_path):
    """a tool the running Python cannot satisfy fails early, before pip runs."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = replace(make_tool_pip("testtool", "testpkg"), requires_python="<3.13")

    with patch("otinstaller.compat.current_python", return_value=(3, 14, 4)):
        with patch("otinstaller.installer.pip_install.run") as mock_pip_run:
            with patch("otinstaller.installer.venv.create_venv") as mock_venv:
                with pytest.raises(
                    PythonVersionError,
                    match="testtool requires Python <3.13 \\(you are running 3.14.4\\)",
                ):
                    install_tool(tool)

    mock_pip_run.assert_not_called()
    mock_venv.assert_not_called()
    assert not (get_tools_dir() / "testtool").exists()
    assert get_installed("testtool") is None


def test_compatible_python_does_not_block_install(monkeypatch, tmp_path):
    """a satisfied requires_python constraint does not block the install."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = replace(make_tool_pip("testtool", "testpkg"), requires_python="<3.13")

    with patch("otinstaller.compat.current_python", return_value=(3, 12, 14)):
        with patch("otinstaller.installer.pip_install.run"):
            with patch("otinstaller.installer.venv.create_venv"):
                with patch("otinstaller.installer.core._get_version_pip", return_value="1.0"):
                    with _mock_entrypoint_check():
                        result = install_tool(tool)

    assert result.version == "1.0"


def test_already_installed_raises(monkeypatch, tmp_path):
    """already installed raises AlreadyInstalled."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    # Pre-populate the DB
    existing = InstalledTool(
        name="testtool",
        version="1.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(existing)

    with pytest.raises(AlreadyInstalled):
        install_tool(tool)


def test_force_replaces(monkeypatch, tmp_path):
    """force replaces an already installed tool."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg", "2.0")

    # Pre-populate the DB with older version
    existing = InstalledTool(
        name="testtool",
        version="1.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(existing)

    with patch("otinstaller.installer.pip_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="2.0"):
                with _mock_entrypoint_check():
                    result = install_tool(tool, force=True)

    assert result.version == "2.0"


def test_leftover_dir_no_db_row_cleaned_first(monkeypatch, tmp_path):
    """a leftover directory with no DB row is cleaned first."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    # Create leftover directory
    leftover = get_tools_dir() / "testtool"
    leftover.mkdir(parents=True)
    (leftover / "junk.txt").write_text("junk")

    with patch("otinstaller.installer.pip_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="1.0"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    # Should have succeeded, leftover cleaned first
    assert get_installed("testtool") is not None


def test_version_falls_back_to_unknown(monkeypatch, tmp_path):
    """version falls back to 'unknown' when pip show fails."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    with patch("otinstaller.installer.pip_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="unknown"):
                with _mock_entrypoint_check():
                    result = install_tool(tool)

    assert result.version == "unknown"


def test_remove_tool_removes_files_and_row(monkeypatch, tmp_path):
    """remove_tool removes files and row."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tool = make_tool_pip("testtool", "testpkg")

    # Install first
    with patch("otinstaller.installer.pip_install.run"):
        with patch("otinstaller.installer.venv.create_venv"):
            with patch("otinstaller.installer.core._get_version_pip", return_value="1.0"):
                with _mock_entrypoint_check():
                    install_tool(tool)

    assert (get_tools_dir() / "testtool").exists()
    assert get_installed("testtool") is not None

    # Now remove
    result = remove_tool("testtool")
    assert result is True
    assert not (get_tools_dir() / "testtool").exists()
    assert get_installed("testtool") is None


def test_remove_tool_returns_false_for_unknown(monkeypatch, tmp_path):
    """remove_tool returns False for unknown tool."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    result = remove_tool("nonexistent")
    assert result is False


def test_remove_tool_clears_row_when_dir_already_gone(monkeypatch, tmp_path):
    """remove_tool clears the row when the directory is already gone."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    # Add to DB but no directory
    existing = InstalledTool(
        name="testtool",
        version="1.0",
        method="pip",
        source="testpkg",
        ref=None,
        commit=None,
        entry_command="testtool",
        entry_script=None,
        installed_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    add_installed(existing)

    result = remove_tool("testtool")
    assert result is True
    assert get_installed("testtool") is None
