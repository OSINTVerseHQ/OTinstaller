"""CLI tests."""

import importlib.resources
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from otinstaller.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "otinstaller 0.0.1" in result.output


def test_help_contains_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    commands = [
        "install",
        "remove",
        "run",
        "update",
        "list",
        "search",
        "info",
        "example",
        "init",
        "keys",
        "resume",
        "doctor",
    ]
    for cmd in commands:
        assert cmd in result.output


def test_help_no_osint():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "osint" not in result.output.lower()


def test_keys_help():
    result = runner.invoke(app, ["keys", "--help"])
    assert result.exit_code == 0
    assert "Manage API keys." in result.output


@pytest.mark.parametrize(
    "cmd_args",
    [],
)
def test_stub_commands_exit_2(cmd_args):
    result = runner.invoke(app, cmd_args)
    assert result.exit_code == 2
    assert "not implemented yet" in result.output


def test_run_with_extra_args(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    }
                ],
            )
        ),
    )
    # Run init first
    runner.invoke(app, ["init", "--yes"])

    # Use single -- (Click strips it, registry-based parsing handles the rest)
    result = runner.invoke(app, ["run", "sherlock", "--", "someuser", "--timeout", "5"])
    assert result.exit_code == 1
    assert "not installed" in result.output


def make_registry_yaml(tmp_path, tools_data):
    import yaml

    reg = tmp_path / "registry.yaml"
    reg.write_text(yaml.dump({"tools": tools_data}))
    return reg


def test_list_table(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "sherlock" in result.output
    assert "username-search" not in result.output
    assert "1 tool" in result.output


def test_list_json(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "sherlock"
    assert data[0]["capabilities"] == ["username-search"]


def test_list_empty(monkeypatch, tmp_path):
    reg = make_registry_yaml(tmp_path, [])
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "no tools in the registry" in result.output


def test_list_empty_json(monkeypatch, tmp_path):
    reg = make_registry_yaml(tmp_path, [])
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data == []


def test_list_installed(monkeypatch, tmp_path):
    # Use a temp OTINSTALLER_HOME for state DB
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    reg = make_registry_yaml(tmp_path, [])
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list", "--installed"])
    assert result.exit_code == 0
    assert "no tools installed" in result.output


def test_list_installed_json(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    reg = make_registry_yaml(tmp_path, [])
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list", "--installed", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data == []


def test_search(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        },
        {
            "name": "maigret",
            "display_name": "Maigret",
            "description": "Build profile",
            "install": {
                "method": "pip",
                "package": "maigret",
            },
            "entrypoint": {"command": "maigret"},
            "capabilities": ["username-search"],
        },
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["search", "username"])
    assert result.exit_code == 0
    assert "sherlock" in result.output
    assert "maigret" in result.output
    assert "2 tools" in result.output


def test_search_no_match(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["search", "email"])
    assert result.exit_code == 0
    assert "no tools match 'email'" in result.output


def test_search_single_match(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        },
        {
            "name": "maigret",
            "display_name": "Maigret",
            "description": "Build profile",
            "install": {
                "method": "pip",
                "package": "maigret",
            },
            "entrypoint": {"command": "maigret"},
            "capabilities": ["username-search"],
        },
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["search", "maigret"])
    assert result.exit_code == 0
    assert "maigret" in result.output
    assert "sherlock" not in result.output
    assert "1 tool" in result.output


def test_search_json(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["search", "username", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "sherlock"


def test_info(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "repo": "sherlock-project/sherlock",
            "license": "MIT",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["info", "sherlock"])
    assert result.exit_code == 0
    assert "Sherlock (sherlock)" in result.output
    assert "Search usernames" in result.output
    assert "Tier: community" in result.output
    assert "Repo: sherlock-project/sherlock" in result.output
    assert "License: MIT" in result.output
    assert "Install: pip sherlock-project" in result.output
    assert "Entrypoint: sherlock" in result.output
    assert "Capabilities: username-search" in result.output
    assert "API keys: none" in result.output
    assert "Not verified yet" in result.output


def test_info_case_insensitive(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["info", "SHERLOCK"])
    assert result.exit_code == 0
    assert "Sherlock" in result.output


def test_info_unknown_tool(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["info", "sherlok"])
    assert result.exit_code == 1
    assert "error: unknown tool 'sherlok'" in result.output
    assert "did you mean: sherlock?" in result.output


def test_info_json(monkeypatch, tmp_path):
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {
                "method": "pip",
                "package": "sherlock-project",
            },
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["info", "sherlock", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["name"] == "sherlock"
    assert data["capabilities"] == ["username-search"]


def test_info_dual_use_notice(monkeypatch, tmp_path):
    tools = [
        {
            "name": "dualtool",
            "display_name": "Dual Tool",
            "description": "A dual use tool",
            "install": {
                "method": "pip",
                "package": "dualtool",
            },
            "entrypoint": {"command": "dualtool"},
            "capabilities": ["dual-use"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["info", "dualtool"])
    assert result.exit_code == 0
    assert "Dual-use tool. See the responsible use notice in the README." in result.output


def test_broken_registry_error(monkeypatch, tmp_path):
    reg = tmp_path / "bad.yaml"
    reg.write_text("invalid: yaml: [")
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert "error:" in result.output


def test_install_refuses_on_non_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    result = runner.invoke(app, ["install", "sherlock"])
    assert result.exit_code == 1
    assert "error: otinstaller currently supports Linux only" in result.output


def test_remove_refuses_on_non_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    result = runner.invoke(app, ["remove", "sherlock"])
    assert result.exit_code == 1
    assert "error: otinstaller currently supports Linux only" in result.output


def test_help_no_osint_still():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "osint" not in result.output.lower()


def test_install_refuses_before_init(monkeypatch, tmp_path):
    """install refuses before init."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {"method": "pip", "package": "sherlock-project"},
            "entrypoint": {"command": "sherlock"},
            "capabilities": ["username-search"],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))

    result = runner.invoke(app, ["install", "sherlock", "--yes"])
    assert result.exit_code == 1
    assert "error: run 'otinstaller init' first" in result.output


def test_install_unknown_name_gives_suggestions(monkeypatch, tmp_path):
    """unknown name gives suggestions."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": [],
                    }
                ],
            )
        ),
    )
    # Run init first
    runner.invoke(app, ["init", "--yes"])

    result = runner.invoke(app, ["install", "sherlok", "--yes"])
    assert result.exit_code == 1
    assert "error: unknown tool 'sherlok'" in result.output
    assert "did you mean: sherlock?" in result.output


def test_install_no_tty_without_yes_refuses(monkeypatch, tmp_path):
    """no terminal without --yes refuses."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": [],
                    }
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    # Without --yes and no tty
    result = runner.invoke(app, ["install", "sherlock"], input="")
    assert result.exit_code == 1
    assert "confirmation needed" in result.output
    assert "--yes" in result.output


def test_install_one_failure_continues_and_exits_1(monkeypatch, tmp_path):
    """one failure among several continues and exits 1."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tools = [
        {
            "name": "goodtool",
            "display_name": "Good Tool",
            "description": "A good tool",
            "install": {"method": "pip", "package": "goodtool"},
            "entrypoint": {"command": "goodtool"},
            "capabilities": [],
        },
        {
            "name": "badtool",
            "display_name": "Bad Tool",
            "description": "A bad tool",
            "install": {"method": "pip", "package": "badtool"},
            "entrypoint": {"command": "badtool"},
            "capabilities": [],
        },
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))
    runner.invoke(app, ["init", "--yes"])

    # Mock install_tool to succeed for goodtool, fail for badtool
    import datetime

    from otinstaller.installer import InstallError
    from otinstaller.state import InstalledTool

    def mock_install_tool(tool, force=False, stream=False):
        if tool.name == "goodtool":
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return InstalledTool(
                name="goodtool",
                version="1.0",
                method="pip",
                source="goodtool",
                ref=None,
                commit=None,
                entry_command="goodtool",
                entry_script=None,
                installed_at=now,
                updated_at=now,
            )
        else:
            raise InstallError("simulated failure")

    with patch("otinstaller.cli.install_tool", side_effect=mock_install_tool):
        result = runner.invoke(app, ["install", "goodtool", "badtool", "--yes"])

    assert result.exit_code == 1
    assert "installed goodtool" in result.output
    assert "error: badtool" in result.output
    assert "1 installed, 0 skipped, 1 failed" in result.output


def test_remove_single_tool(monkeypatch, tmp_path):
    """remove single tool."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {"method": "pip", "package": "sherlock-project"},
            "entrypoint": {"command": "sherlock"},
            "capabilities": [],
        }
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))
    runner.invoke(app, ["init", "--yes"])

    # Mock install and remove
    import datetime

    from otinstaller.state import InstalledTool

    def mock_install_tool(tool, force=False, stream=False):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=tool.name,
            version="1.0",
            method="pip",
            source=tool.install.package,
            ref=None,
            commit=None,
            entry_command=tool.name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("otinstaller.cli.install_tool", side_effect=mock_install_tool):
        with patch("otinstaller.cli.remove_tool", return_value=True) as mock_remove:
            result = runner.invoke(app, ["install", "sherlock", "--yes"])
            assert result.exit_code == 0

            result = runner.invoke(app, ["remove", "sherlock", "--yes"])
            assert result.exit_code == 0
            assert "removed sherlock" in result.output
            mock_remove.assert_called_once_with("sherlock")


def test_remove_all_tools(monkeypatch, tmp_path):
    """remove --all removes all tools."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    tools = [
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {"method": "pip", "package": "sherlock-project"},
            "entrypoint": {"command": "sherlock"},
            "capabilities": [],
        },
        {
            "name": "maigret",
            "display_name": "Maigret",
            "description": "Build profile",
            "install": {"method": "pip", "package": "maigret"},
            "entrypoint": {"command": "maigret"},
            "capabilities": [],
        },
    ]
    reg = make_registry_yaml(tmp_path, tools)
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_install_tool(tool, force=False, stream=False):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=tool.name,
            version="1.0",
            method="pip",
            source=tool.install.package,
            ref=None,
            commit=None,
            entry_command=tool.name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    with patch("otinstaller.cli.install_tool", side_effect=mock_install_tool):
        with patch("otinstaller.cli.list_installed") as mock_list:
            with patch("otinstaller.cli.remove_tool", return_value=True) as mock_remove:
                mock_list.return_value = [
                    InstalledTool(
                        name="sherlock",
                        version="1.0",
                        method="pip",
                        source="sherlock-project",
                        ref=None,
                        commit=None,
                        entry_command="sherlock",
                        entry_script=None,
                        installed_at="2024-01-01T00:00:00+00:00",
                        updated_at="2024-01-01T00:00:00+00:00",
                    ),
                    InstalledTool(
                        name="maigret",
                        version="1.0",
                        method="pip",
                        source="maigret",
                        ref=None,
                        commit=None,
                        entry_command="maigret",
                        entry_script=None,
                        installed_at="2024-01-01T00:00:00+00:00",
                        updated_at="2024-01-01T00:00:00+00:00",
                    ),
                ]
                result = runner.invoke(app, ["remove", "--all", "--yes"])
                assert result.exit_code == 0
                assert mock_remove.call_count == 2


def test_remove_unknown_tool(monkeypatch, tmp_path):
    """remove unknown tool returns error."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    runner.invoke(app, ["init", "--yes"])

    with patch("otinstaller.cli.remove_tool", return_value=False):
        result = runner.invoke(app, ["remove", "unknown", "--yes"])
        assert result.exit_code == 1
        assert "error: unknown is not installed" in result.output


def test_list_installed_table_with_data(monkeypatch, tmp_path):
    """list --installed table with data."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    from otinstaller.state import InstalledTool

    with patch("otinstaller.cli.list_installed") as mock_list:
        mock_list.return_value = [
            InstalledTool(
                name="sherlock",
                version="1.0",
                method="pip",
                source="sherlock-project",
                ref=None,
                commit=None,
                entry_command="sherlock",
                entry_script=None,
                installed_at="2024-01-15T12:00:00+00:00",
                updated_at="2024-01-15T12:00:00+00:00",
            ),
        ]
        result = runner.invoke(app, ["list", "--installed"])
        assert result.exit_code == 0
        assert "sherlock" in result.output
        assert "1.0" in result.output
        assert "pip" in result.output
        assert "2024-01-15" in result.output
        assert "1 tool" in result.output


def test_list_installed_json_with_data(monkeypatch, tmp_path):
    """list --installed --json with data."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    from otinstaller.state import InstalledTool

    with patch("otinstaller.cli.list_installed") as mock_list:
        mock_list.return_value = [
            InstalledTool(
                name="sherlock",
                version="1.0",
                method="pip",
                source="sherlock-project",
                ref=None,
                commit=None,
                entry_command="sherlock",
                entry_script=None,
                installed_at="2024-01-15T12:00:00+00:00",
                updated_at="2024-01-15T12:00:00+00:00",
            ),
        ]
        result = runner.invoke(app, ["list", "--installed", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "sherlock"
        assert data[0]["version"] == "1.0"


def test_list_installed_singular(monkeypatch, tmp_path):
    """list --installed shows '1 tool' not '1 tools'."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    from otinstaller.state import InstalledTool

    with patch("otinstaller.cli.list_installed") as mock_list:
        mock_list.return_value = [
            InstalledTool(
                name="sherlock",
                version="1.0",
                method="pip",
                source="sherlock-project",
                ref=None,
                commit=None,
                entry_command="sherlock",
                entry_script=None,
                installed_at="2024-01-15T12:00:00+00:00",
                updated_at="2024-01-15T12:00:00+00:00",
            ),
        ]
        result = runner.invoke(app, ["list", "--installed"])
        assert result.exit_code == 0
        assert "1 tool" in result.output
        assert "1 tools" not in result.output


def test_doctor_all_ok(monkeypatch, tmp_path):
    """doctor exits 0 when all checks pass."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/git" if x == "git" else None)

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "[ok] platform is Linux" in result.output
    assert "[ok] git found" in result.output
    assert "[ok] venv module works" in result.output
    assert "[ok] home directory writable" in result.output


def test_doctor_not_linux(monkeypatch, tmp_path):
    """doctor exits 1 on non-Linux."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    # CliRunner.invoke() breaks when sys.platform="win32" because click's testing
    # internals try to use Windows-only APIs (_winapi, msvcrt) that don't exist on Linux.
    # Test the real doctor command logic by calling the function directly with a mocked sys.
    import io
    import sys
    from contextlib import redirect_stderr, redirect_stdout
    from unittest.mock import MagicMock

    import typer

    # Import doctor first (click/typer loaded with real sys.platform="linux")
    from otinstaller.cli import doctor

    # Mock sys.platform for the function's internal import
    real_sys = sys
    mock_sys = MagicMock()
    mock_sys.platform = "win32"
    mock_sys.version_info = real_sys.version_info
    mock_sys.executable = real_sys.executable
    mock_sys.argv = ["otinstaller", "doctor"]

    import sys as sys_module

    sys_module.modules["sys"] = mock_sys

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            doctor()
    except typer.Exit as e:
        exit_code = e.exit_code
    else:
        exit_code = 0

    # Restore
    sys_module.modules["sys"] = real_sys

    output = stdout.getvalue()
    assert exit_code == 1
    assert "[problem] platform is not Linux" in output


def test_doctor_python_version_problem(monkeypatch, tmp_path):
    """doctor exits 1 when Python version is not supported."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 14, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/git" if x == "git" else None)

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] python 3.14 is not supported" in result.output
    assert "this project targets 3.10-3.12" in result.output


def test_doctor_git_missing_debian(monkeypatch, tmp_path):
    """doctor shows debian install command when git is missing."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("otinstaller.config.get_distro", lambda: "debian")
    monkeypatch.setattr("otinstaller.config.get_distro_family", lambda: "debian")

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] git not found" in result.output
    assert "sudo apt install git" in result.output


def test_doctor_git_missing_arch(monkeypatch, tmp_path):
    """doctor shows arch install command when git is missing."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: None)

    # Mock distro detection
    os_release = tmp_path / "os-release"
    os_release.write_text('ID="arch"\n')
    monkeypatch.setattr(
        "otinstaller.config.Path", lambda x: os_release if x == "/etc/os-release" else Path(x)
    )

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] git not found" in result.output
    assert "sudo pacman -S git" in result.output


def test_doctor_venv_broken_debian(monkeypatch, tmp_path):
    """doctor shows debian install command when venv is broken."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/git" if x == "git" else None)
    monkeypatch.setattr("otinstaller.config.get_distro", lambda: "debian")
    monkeypatch.setattr("otinstaller.config.get_distro_family", lambda: "debian")

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 1

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] venv module failed" in result.output
    assert "python3.12-venv" in result.output


def test_doctor_venv_broken_arch(monkeypatch, tmp_path):
    """doctor shows arch message when venv is broken."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/git" if x == "git" else None)

    # Mock distro detection
    os_release = tmp_path / "os-release"
    os_release.write_text('ID="arch"\n')
    monkeypatch.setattr(
        "otinstaller.config.Path", lambda x: os_release if x == "/etc/os-release" else Path(x)
    )

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 1

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] venv module failed" in result.output
    assert "should be included with python on Arch" in result.output


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="permission checks are meaningless as root",
)
def test_doctor_home_not_writable(monkeypatch, tmp_path):
    """doctor fails when home is not writable."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("sys.version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/git" if x == "git" else None)
    monkeypatch.setattr("otinstaller.config.get_distro", lambda: "debian")
    monkeypatch.setattr("otinstaller.config.get_distro_family", lambda: "debian")

    def mock_run(*args, **kwargs):
        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", mock_run)

    # Make home directory not writable
    home = tmp_path
    home.chmod(0o555)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] home directory not writable" in result.output

    # Restore permissions for cleanup
    home.chmod(0o755)


def test_run_single_tool_still_works(monkeypatch, tmp_path):
    """Single tool run behaves as before (no regression)."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    }
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        if name == "sherlock":
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return InstalledTool(
                name="sherlock",
                version="1.0",
                method="pip",
                source="sherlock-project",
                ref=None,
                commit=None,
                entry_command="sherlock",
                entry_script=None,
                installed_at=now,
                updated_at=now,
            )
        return None

    mock_meta = type(
        "Meta",
        (),
        {
            "exit_code": 0,
            "output_path": ("sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"),
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": (
                    "sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"
                ),
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool", return_value=mock_meta) as mock_run_tool:
            with patch("otinstaller.cli.write_meta") as _:
                # Use single -- (Click strips it, registry-based parsing handles the rest)
                result = runner.invoke(app, ["run", "sherlock", "--", "someuser", "--timeout", "5"])
                assert result.exit_code == 0
                assert "tool exited 0" in result.output
                mock_run_tool.assert_called_once()
                call_args = mock_run_tool.call_args
                assert call_args[0][2] == ["someuser", "--timeout", "5"]


def test_run_multiple_tool_names(monkeypatch, tmp_path):
    """Multiple tool names are parsed correctly from ctx.args."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    fake_path = "sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"

    meta1 = type(
        "Meta",
        (),
        {
            "tool": "sherlock",
            "exit_code": 0,
            "output_path": fake_path,
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": fake_path,
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()
    meta2 = type(
        "Meta",
        (),
        {
            "tool": "maigret",
            "exit_code": 0,
            "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
            "sha256": "def456",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
                "sha256": "def456",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool") as mock_run_tool:
            with patch(
                "otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2]
            ) as mock_run_parallel:
                with patch("otinstaller.cli.write_meta") as _:
                    # Use single -- (Click strips it, registry-based parsing handles the rest)
                    result = runner.invoke(
                        app, ["run", "sherlock", "maigret", "--", "someuser", "--timeout", "5"]
                    )
                    assert result.exit_code == 0
                    mock_run_tool.assert_not_called()
                    mock_run_parallel.assert_called_once()
                    # Verify tool_names and extra_args were parsed correctly
                    call_args = mock_run_parallel.call_args
                    tools_arg = call_args[0][0]
                    assert tools_arg[0].name == "sherlock"
                    assert tools_arg[1].name == "maigret"
                    extra_args = call_args[0][2]
                    assert isinstance(extra_args, dict)
                    assert extra_args["sherlock"] == ["someuser", "--timeout", "5"]
                    assert extra_args["maigret"] == ["someuser", "--timeout", "5"]


def test_run_parallel_single_tool_uses_single_path(monkeypatch, tmp_path):
    """Running 1 tool uses the single-tool path, not parallel path."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    }
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        if name == "sherlock":
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return InstalledTool(
                name="sherlock",
                version="1.0",
                method="pip",
                source="sherlock-project",
                ref=None,
                commit=None,
                entry_command="sherlock",
                entry_script=None,
                installed_at=now,
                updated_at=now,
            )
        return None

    fake_path = "sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"

    mock_meta = type(
        "Meta",
        (),
        {
            "exit_code": 0,
            "output_path": fake_path,
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": fake_path,
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool", return_value=mock_meta) as mock_run_tool:
            with patch("otinstaller.cli.run_tools_parallel") as mock_run_parallel:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(app, ["run", "sherlock", "--", "someuser"])
                    assert result.exit_code == 0
                    mock_run_tool.assert_called_once()
                    mock_run_parallel.assert_not_called()


def test_run_parallel_multiple_tools_uses_parallel_path(monkeypatch, tmp_path):
    """Running 2+ tools uses run_tools_parallel, not run_tool directly."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    fake_path = "sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"

    # Create mock metas with proper tool attribute
    meta1 = type(
        "Meta",
        (),
        {
            "tool": "sherlock",
            "exit_code": 0,
            "output_path": fake_path,
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": fake_path,
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()
    meta2 = type(
        "Meta",
        (),
        {
            "tool": "maigret",
            "exit_code": 0,
            "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
            "sha256": "def456",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
                "sha256": "def456",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool", return_value=meta1) as mock_run_tool:
            with patch(
                "otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2]
            ) as mock_run_parallel:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(app, ["run", "sherlock", "maigret", "--", "someuser"])
                    assert result.exit_code == 0
                    mock_run_tool.assert_not_called()
                    mock_run_parallel.assert_called_once()
                    # Verify max_parallel was passed
                    call_kwargs = mock_run_parallel.call_args[1]
                    assert call_kwargs["max_parallel"] == 4  # default


def test_run_parallel_custom_parallel_value(monkeypatch, tmp_path):
    """--parallel value is passed through to max_parallel."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    fake_path = "sherlock/unspecified/20240101-000000_sherlock_unspecified_abc123.txt"

    meta1 = type(
        "Meta",
        (),
        {
            "tool": "sherlock",
            "exit_code": 0,
            "output_path": fake_path,
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": fake_path,
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()
    meta2 = type(
        "Meta",
        (),
        {
            "tool": "maigret",
            "exit_code": 0,
            "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
            "sha256": "def456",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": "maigret/unspecified/20240101-000000_maigret_unspecified_abc123.txt",
                "sha256": "def456",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool", return_value=meta1) as mock_run_tool:
            with patch(
                "otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2]
            ) as mock_run_parallel:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(
                        app, ["run", "sherlock", "maigret", "--parallel", "2", "--", "someuser"]
                    )
                    assert result.exit_code == 0
                    mock_run_tool.assert_not_called()
                    mock_run_parallel.assert_called_once()
                    call_kwargs = mock_run_parallel.call_args[1]
                    assert call_kwargs["max_parallel"] == 2


def test_run_parallel_invalid_parallel_exits(monkeypatch, tmp_path):
    """--parallel 0 or negative exits 1 with error message before calling anything."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    mock_meta = type(
        "Meta",
        (),
        {
            "exit_code": 0,
            "output_path": "test/unspecified/20240101-000000_test_unspecified_abc123.txt",
            "sha256": "abc123",
            "tool_version": "",
            "to_dict": lambda self: {
                "exit_code": 0,
                "output_path": "test/unspecified/20240101-000000_test_unspecified_abc123.txt",
                "sha256": "abc123",
                "tool_version": "",
            },
        },
    )()

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool", return_value=mock_meta) as mock_run_tool:
            with patch("otinstaller.cli.run_tools_parallel") as mock_run_parallel:
                with patch("otinstaller.cli.write_meta") as _:
                    # Test --parallel 0
                    result = runner.invoke(
                        app, ["run", "sherlock", "maigret", "--parallel", "0", "--", "someuser"]
                    )
                    assert result.exit_code == 1
                    assert "error: --parallel must be at least 1" in result.output
                    mock_run_tool.assert_not_called()
                    mock_run_parallel.assert_not_called()

                    # Test --parallel -1
                    result = runner.invoke(
                        app, ["run", "sherlock", "maigret", "--parallel", "-1", "--", "someuser"]
                    )
                    assert result.exit_code == 1
                    assert "error: --parallel must be at least 1" in result.output


def test_run_parallel_exit_code_all_succeed(monkeypatch, tmp_path):
    """Exit code 0 when all mocked results succeed."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.results import RunMeta
    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta1 = RunMeta(
        command=["sherlock", "someuser"],
        tool="sherlock",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=0,
        status="complete",
        output_path="sherlock/someuser/20240101-000000_sherlock_someuser_abc123.txt",
        sha256="abc123",
        bytes=100,
    )
    meta2 = RunMeta(
        command=["maigret", "someuser"],
        tool="maigret",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=0,
        status="complete",
        output_path="maigret/someuser/20240101-000000_maigret_someuser_abc123.txt",
        sha256="def456",
        bytes=100,
    )

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool") as _:
            with patch("otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2]) as _:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(app, ["run", "sherlock", "maigret", "--", "someuser"])
                    assert result.exit_code == 0
                    assert "2 ok, 0 failed" in result.output


def test_run_parallel_exit_code_any_failed(monkeypatch, tmp_path):
    """Exit code 1 when any mocked result failed."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.results import RunMeta
    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta1 = RunMeta(
        command=["sherlock", "someuser"],
        tool="sherlock",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=0,
        status="complete",
        output_path="sherlock/someuser/20240101-000000_sherlock_someuser_abc123.txt",
        sha256="abc123",
        bytes=100,
    )
    meta2 = RunMeta(
        command=["maigret", "someuser"],
        tool="maigret",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=1,
        status="failed",
        output_path="maigret/someuser/20240101-000000_maigret_someuser_abc123.txt",
        sha256="def456",
        bytes=100,
    )

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool") as _:
            with patch("otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2]) as _:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(app, ["run", "sherlock", "maigret", "--", "someuser"])
                    assert result.exit_code == 1
                    assert "1 ok, 1 failed" in result.output


def test_run_parallel_summary_line_correct(monkeypatch, tmp_path):
    """Summary line 'N ok, N failed' is correct for mixed results."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "capabilities": ["username-search"],
                    },
                    {
                        "name": "thirdtool",
                        "display_name": "Third Tool",
                        "description": "Another tool",
                        "install": {"method": "pip", "package": "thirdtool"},
                        "entrypoint": {"command": "thirdtool"},
                        "capabilities": ["username-search"],
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    import datetime

    from otinstaller.results import RunMeta
    from otinstaller.state import InstalledTool

    def mock_get_installed(name):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return InstalledTool(
            name=name,
            version="1.0",
            method="pip",
            source=name,
            ref=None,
            commit=None,
            entry_command=name,
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta1 = RunMeta(
        command=["sherlock", "someuser"],
        tool="sherlock",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=0,
        status="complete",
        output_path="sherlock/someuser/20240101-000000_sherlock_someuser_abc123.txt",
        sha256="abc123",
        bytes=100,
    )
    meta2 = RunMeta(
        command=["maigret", "someuser"],
        tool="maigret",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=1,
        status="failed",
        output_path="maigret/someuser/20240101-000000_maigret_someuser_abc123.txt",
        sha256="def456",
        bytes=100,
    )
    meta3 = RunMeta(
        command=["thirdtool", "someuser"],
        tool="thirdtool",
        tool_version="1.0",
        target="someuser",
        case=None,
        started_at=now,
        ended_at=now,
        duration_seconds=1.0,
        exit_code=0,
        status="complete",
        output_path="thirdtool/someuser/20240101-000000_thirdtool_someuser_abc123.txt",
        sha256="ghi789",
        bytes=100,
    )

    with patch("otinstaller.cli.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.runner.run_tool", side_effect=[meta1, meta2, meta3]):
            with patch("otinstaller.cli.write_meta") as _:
                result = runner.invoke(
                    app, ["run", "sherlock", "maigret", "thirdtool", "--", "someuser"]
                )
                assert result.exit_code == 1
                assert "2 ok, 1 failed" in result.output


def test_keys_check_no_keys_set(monkeypatch, tmp_path):
    """keys check with no keys set shows all as missing."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "api_keys": {"required": ["SHODAN_API_KEY"]},
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "api_keys": {
                            "required": ["HUNTER_API_KEY"],
                            "optional": ["SHODAN_API_KEY"],
                        },
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    with patch("otinstaller.keys.load_env_file", return_value={}):
        result = runner.invoke(app, ["keys", "check"])
        assert result.exit_code == 0
        assert "✗ SHODAN_API_KEY" in result.output
        assert "✗ HUNTER_API_KEY" in result.output
        assert "these tools need keys you don't have" in result.output
        assert "sherlock: missing SHODAN_API_KEY" in result.output
        assert "maigret: missing HUNTER_API_KEY" in result.output
        # SHODAN_API_KEY is optional for maigret - shown in coverage hints, not as missing
        assert "Adding SHODAN_API_KEY would unlock 1 more tool(s)" in result.output


def test_keys_check_some_keys_set(monkeypatch, tmp_path):
    """keys check with some keys set shows correct ✓/✗ per key."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "api_keys": {"required": ["SHODAN_API_KEY"]},
                    },
                    {
                        "name": "maigret",
                        "display_name": "Maigret",
                        "description": "Build profile",
                        "install": {"method": "pip", "package": "maigret"},
                        "entrypoint": {"command": "maigret"},
                        "api_keys": {
                            "required": ["HUNTER_API_KEY"],
                            "optional": ["SHODAN_API_KEY"],
                        },
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    with patch("otinstaller.keys.load_env_file", return_value={"SHODAN_API_KEY": "set_value"}):
        result = runner.invoke(app, ["keys", "check"])
        assert result.exit_code == 0
        assert "✓ SHODAN_API_KEY" in result.output
        assert "✗ HUNTER_API_KEY" in result.output
        assert "maigret: missing HUNTER_API_KEY" in result.output
        assert "sherlock" not in result.output  # sherlock has all required keys


def test_keys_check_json(monkeypatch, tmp_path):
    """keys check --json produces valid JSON with no key values in it."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "sherlock",
                        "display_name": "Sherlock",
                        "description": "Search usernames",
                        "install": {"method": "pip", "package": "sherlock-project"},
                        "entrypoint": {"command": "sherlock"},
                        "api_keys": {"required": ["SHODAN_API_KEY"]},
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    with patch("otinstaller.keys.load_env_file", return_value={"SHODAN_API_KEY": "secret_value"}):
        result = runner.invoke(app, ["keys", "check", "--json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert "keys" in data
        assert data["keys"]["SHODAN_API_KEY"] == "set"
        assert "secret_value" not in result.output  # Value should not be in output
        assert "tools_missing_keys" in data
        assert "coverage_hints" in data


def test_keys_check_coverage_hint(monkeypatch, tmp_path):
    """Coverage hint math is correct for a simple constructed case."""
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv(
        "OTINSTALLER_REGISTRY",
        str(
            make_registry_yaml(
                tmp_path,
                [
                    {
                        "name": "tool1",
                        "display_name": "Tool 1",
                        "description": "Tool 1",
                        "install": {"method": "pip", "package": "tool1"},
                        "entrypoint": {"command": "tool1"},
                        "api_keys": {"required": ["KEY_A"]},
                    },
                    {
                        "name": "tool2",
                        "display_name": "Tool 2",
                        "description": "Tool 2",
                        "install": {"method": "pip", "package": "tool2"},
                        "entrypoint": {"command": "tool2"},
                        "api_keys": {"required": ["KEY_A", "KEY_B"]},
                    },
                    {
                        "name": "tool3",
                        "display_name": "Tool 3",
                        "description": "Tool 3",
                        "install": {"method": "pip", "package": "tool3"},
                        "entrypoint": {"command": "tool3"},
                        "api_keys": {"required": ["KEY_B"]},
                    },
                ],
            )
        ),
    )
    runner.invoke(app, ["init", "--yes"])

    # Only KEY_A is set
    with patch("otinstaller.keys.load_env_file", return_value={"KEY_A": "value"}):
        result = runner.invoke(app, ["keys", "check"])
        assert result.exit_code == 0
        # Adding KEY_B would unlock tool2 (needs KEY_A and KEY_B, has KEY_A)
        # and tool3 (needs KEY_B, has none) -> 2 tools
        assert "Adding KEY_B would unlock 2 more tool(s)" in result.output


# Extract CLI tests


def test_extract_with_case_scans_case_directory(monkeypatch, tmp_path):
    """extract with --case scans the right directory."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Create case directory structure
    case_dir = tmp_path / "results" / "cases" / "mycase" / "tool" / "target"
    case_dir.mkdir(parents=True)
    file1 = case_dir / "result.txt"
    file1.write_text("email@test.com")

    result = runner.invoke(app, ["extract", "ignored", "--case", "mycase"])
    assert result.exit_code == 0
    assert "email@test.com" in result.output


def test_extract_unknown_tool_errors(monkeypatch, tmp_path):
    """extract with an unknown tool/path name errors correctly."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["extract", "nonexistent"])
    assert result.exit_code == 1
    assert "error: 'nonexistent' is not a known installed tool" in result.output


def test_extract_json_shape(monkeypatch, tmp_path):
    """extract --json shape is correct."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Create a case with an email
    case_dir = tmp_path / "results" / "cases" / "mycase" / "tool" / "target"
    case_dir.mkdir(parents=True)
    file1 = case_dir / "result.txt"
    file1.write_text("email@test.com")

    import json

    result = runner.invoke(app, ["extract", "ignored", "--case", "mycase", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "emails" in data
    assert "domains" in data
    assert "ips" in data
    assert "urls" in data
    assert "email@test.com" in data["emails"]


def test_extract_nothing_found_prints_message(monkeypatch, tmp_path):
    """extract with nothing found prints 'no indicators found'."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Create case with no indicators
    case_dir = tmp_path / "results" / "cases" / "mycase" / "tool" / "target"
    case_dir.mkdir(parents=True)
    file1 = case_dir / "result.txt"
    file1.write_text("no indicators here")

    result = runner.invoke(app, ["extract", "ignored", "--case", "mycase"])
    assert result.exit_code == 0
    assert "no indicators found" in result.output


# Diff CLI tests


def test_diff_fewer_than_two_runs_errors(monkeypatch, tmp_path):
    """diff with fewer than 2 runs reports correctly and exits 1."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # No runs exist
    result = runner.invoke(app, ["diff", "tool", "target"])
    assert result.exit_code == 1
    assert "no runs found" in result.output


def test_diff_json_shape(monkeypatch, tmp_path):
    """diff --json shape is correct."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.diff

    original_get_results = otinstaller.diff.get_results_dir
    otinstaller.diff.get_results_dir = lambda: tmp_path / "results"

    try:
        # Create two runs
        base = tmp_path / "results"
        tool_dir = base / "tool" / "target"
        tool_dir.mkdir(parents=True)

        file1 = tool_dir / "20240101-120000_tool_target_abc123.txt"
        file2 = tool_dir / "20240102-120000_tool_target_def456.txt"
        file1.write_text("line1\nline2\n")
        file2.write_text("line1\nline2\nline3\n")

        import json

        file1.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-01T00:00:00+00:00"})
        )
        file2.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-02T00:00:00+00:00"})
        )

        runner = CliRunner()
        result = runner.invoke(app, ["diff", "tool", "target", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "added" in data
        assert "removed" in data
        assert "older_file" in data
        assert "newer_file" in data
        assert "older_date" in data
        assert "newer_date" in data
        assert "line3" in data["added"]
    finally:
        otinstaller.diff.get_results_dir = original_get_results


def test_diff_shows_differences(monkeypatch, tmp_path):
    """diff with real differences shows added/removed correctly."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.diff

    original_get_results = otinstaller.diff.get_results_dir
    otinstaller.diff.get_results_dir = lambda: tmp_path / "results"

    try:
        # Create two runs with known differences
        base = tmp_path / "results"
        tool_dir = base / "tool" / "target"
        tool_dir.mkdir(parents=True)

        file1 = tool_dir / "20240101-120000_tool_target_abc123.txt"
        file2 = tool_dir / "20240102-120000_tool_target_def456.txt"
        file1.write_text("common\nold_line\n")
        file2.write_text("common\nnew_line\n")

        import json

        file1.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-01T00:00:00+00:00"})
        )
        file2.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-02T00:00:00+00:00"})
        )

        runner = CliRunner()
        result = runner.invoke(app, ["diff", "tool", "target"])
        assert result.exit_code == 0
        assert "comparing" in result.output
        assert "+ new_line" in result.output
        assert "- old_line" in result.output
    finally:
        otinstaller.diff.get_results_dir = original_get_results


def test_diff_no_changes(monkeypatch, tmp_path):
    """diff with identical files reports no changes."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.diff

    original_get_results = otinstaller.diff.get_results_dir
    otinstaller.diff.get_results_dir = lambda: tmp_path / "results"

    try:
        # Create two runs with identical content
        base = tmp_path / "results"
        tool_dir = base / "tool" / "target"
        tool_dir.mkdir(parents=True)

        file1 = tool_dir / "20240101-120000_tool_target_abc123.txt"
        file2 = tool_dir / "20240102-120000_tool_target_def456.txt"
        content = "same\ncontent\n"
        file1.write_text(content)
        file2.write_text(content)

        import json

        file1.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-01T00:00:00+00:00"})
        )
        file2.with_suffix(".meta.json").write_text(
            json.dumps({"started_at": "2024-01-02T00:00:00+00:00"})
        )

        runner = CliRunner()
        result = runner.invoke(app, ["diff", "tool", "target"])
        assert result.exit_code == 0
        assert "no changes between these two runs" in result.output
    finally:
        otinstaller.diff.get_results_dir = original_get_results


# Auto CLI tests


def test_auto_type_override_skips_detection(monkeypatch, tmp_path):
    """auto with --type override skips detection entirely."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Use --type to override - even though "example.com" would detect as domain,
    # we override to username
    result = runner.invoke(app, ["auto", "example.com", "--type", "username", "--dry-run"])
    assert result.exit_code == 0
    assert "detected target type" not in result.output  # Detection was skipped


def test_auto_filters_to_installed_matching_tools(monkeypatch, tmp_path):
    """auto correctly filters to only installed tools matching the type."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    # Create registry with tools that accept different types
    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="tool1",
                display_name="Tool 1",
                description="Accepts username",
                install=Install(method="pip", package="tool1"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
            Tool(
                name="tool2",
                display_name="Tool 2",
                description="Accepts domain",
                install=Install(method="pip", package="tool2"),
                entrypoint=Entrypoint(command="tool2"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("domain",),
            ),
            Tool(
                name="tool3",
                display_name="Tool 3",
                description="Accepts both",
                install=Install(method="pip", package="tool3"),
                entrypoint=Entrypoint(command="tool3"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username", "domain"),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool, add_installed

        now = datetime.now(timezone.utc).isoformat()
        # Only tool1 and tool3 are installed
        for name in ["tool1", "tool3"]:
            t = InstalledTool(
                name=name,
                version="1.0",
                method="pip",
                source=name,
                ref=None,
                commit=None,
                entry_command=name,
                entry_script=None,
                installed_at=now,
                updated_at=now,
            )
            add_installed(t)

        from typer.testing import CliRunner

        from otinstaller.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # Target is a username - should match tool1 and tool3
        result = runner.invoke(app, ["auto", "someuser", "--dry-run"])
        assert result.exit_code == 0
        assert "tool1" in result.output
        assert "tool3" in result.output
        assert "tool2" not in result.output  # Not installed
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_auto_reports_not_installed_separately(monkeypatch, tmp_path):
    """auto reports not-installed-but-matching tools separately."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="installed_tool",
                display_name="Installed Tool",
                description="Accepts username",
                install=Install(method="pip", package="installed_tool"),
                entrypoint=Entrypoint(command="installed_tool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
            Tool(
                name="not_installed_tool",
                display_name="Not Installed Tool",
                description="Accepts username",
                install=Install(method="pip", package="not_installed_tool"),
                entrypoint=Entrypoint(command="not_installed_tool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool, add_installed

        now = datetime.now(timezone.utc).isoformat()
        # Only installed_tool is installed
        t = InstalledTool(
            name="installed_tool",
            version="1.0",
            method="pip",
            source="installed_tool",
            ref=None,
            commit=None,
            entry_command="installed_tool",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )
        add_installed(t)

        from typer.testing import CliRunner

        from otinstaller.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["auto", "someuser", "--dry-run"])
        assert result.exit_code == 0
        assert "installed_tool" in result.output
        assert "not_installed_tool" in result.output
        assert "not installed" in result.output
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_auto_zero_matching_installed_tools(monkeypatch, tmp_path):
    """auto with zero matching installed tools reports correctly, exit 0."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="tool1",
                display_name="Tool 1",
                description="Accepts username",
                install=Install(method="pip", package="tool1"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from typer.testing import CliRunner

        from otinstaller.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # No tools installed, target is username and tool accepts username but not installed
        result = runner.invoke(app, ["auto", "someuser", "--dry-run"])
        assert result.exit_code == 0
        assert "no installed tools accept 'username' targets" in result.output
        assert "tool1" in result.output  # Suggested as matching but not installed
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_auto_dry_run_makes_no_calls(monkeypatch, tmp_path):
    """auto --dry-run makes no calls to run_tools_parallel."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="tool1",
                display_name="Tool 1",
                description="Accepts username",
                install=Install(method="pip", package="tool1"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool, add_installed

        now = datetime.now(timezone.utc).isoformat()
        t = InstalledTool(
            name="tool1",
            version="1.0",
            method="pip",
            source="tool1",
            ref=None,
            commit=None,
            entry_command="tool1",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )
        add_installed(t)

        from typer.testing import CliRunner

        from otinstaller.cli import app

        runner = CliRunner()

        with patch("otinstaller.cli.run_tools_parallel") as mock_run_parallel:
            result = runner.invoke(app, ["auto", "someuser", "--dry-run"])
            assert result.exit_code == 0
            mock_run_parallel.assert_not_called()
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_auto_without_yes_no_tty_refuses(monkeypatch, tmp_path):
    """auto without --yes and no tty refuses."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="tool1",
                display_name="Tool 1",
                description="Accepts username",
                install=Install(method="pip", package="tool1"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool, add_installed

        now = datetime.now(timezone.utc).isoformat()
        t = InstalledTool(
            name="tool1",
            version="1.0",
            method="pip",
            source="tool1",
            ref=None,
            commit=None,
            entry_command="tool1",
            entry_script=None,
            installed_at=now,
            updated_at=now,
        )
        add_installed(t)

        from typer.testing import CliRunner

        from otinstaller.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # No --yes and no tty
        result = runner.invoke(app, ["auto", "someuser"], input="")
        assert result.exit_code == 1
        assert "confirmation needed" in result.output
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_auto_calls_run_tools_parallel_correctly(monkeypatch, tmp_path):
    """auto correctly calls run_tools_parallel with right arguments."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setenv("OTINSTALLER_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(sys, "platform", "linux")

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="tool1",
                display_name="Tool 1",
                description="Accepts username",
                install=Install(method="pip", package="tool1"),
                entrypoint=Entrypoint(command="tool1"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
            Tool(
                name="tool2",
                display_name="Tool 2",
                description="Accepts username",
                install=Install(method="pip", package="tool2"),
                entrypoint=Entrypoint(command="tool2"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                accepts=("username",),
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        from datetime import datetime, timezone

        from otinstaller.state import InstalledTool, add_installed

        now = datetime.now(timezone.utc).isoformat()
        for name in ["tool1", "tool2"]:
            t = InstalledTool(
                name=name,
                version="1.0",
                method="pip",
                source=name,
                ref=None,
                commit=None,
                entry_command=name,
                entry_script=None,
                installed_at=now,
                updated_at=now,
            )
            add_installed(t)

        from typer.testing import CliRunner

        from otinstaller.cli import app
        from otinstaller.results import RunMeta

        mock_meta1 = RunMeta(
            command=["tool1", "someuser"],
            tool="tool1",
            tool_version="1.0",
            target="someuser",
            case=None,
            started_at="2024-01-01T00:00:00+00:00",
            ended_at="2024-01-01T00:00:01+00:00",
            duration_seconds=1.0,
            exit_code=0,
            status="complete",
            output_path="tool1/someuser/result.txt",
            sha256="abc123",
            bytes=100,
        )
        mock_meta2 = RunMeta(
            command=["tool2", "someuser"],
            tool="tool2",
            tool_version="1.0",
            target="someuser",
            case=None,
            started_at="2024-01-01T00:00:00+00:00",
            ended_at="2024-01-01T00:00:01+00:00",
            duration_seconds=1.0,
            exit_code=0,
            status="complete",
            output_path="tool2/someuser/result.txt",
            sha256="def456",
            bytes=100,
        )

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        # Create tool directories for the mock tools
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "tool1").mkdir(parents=True, exist_ok=True)
        (tools_dir / "tool2").mkdir(parents=True, exist_ok=True)

        with patch(
            "otinstaller.cli.run_tools_parallel", return_value=[mock_meta1, mock_meta2]
        ) as mock_run_parallel:
            with patch("otinstaller.cli.write_meta"):
                from typer.testing import CliRunner

                from otinstaller.cli import app

                runner = CliRunner()
                result = runner.invoke(app, ["auto", "someuser", "--parallel", "2", "--yes"])
                assert result.exit_code == 0

                mock_run_parallel.assert_called_once()
                call_args = mock_run_parallel.call_args
                # target, case, max_parallel, stream are keyword-only
                assert call_args.kwargs["max_parallel"] == 2
                assert call_args.kwargs["target"] == "someuser"
                assert call_args.kwargs["case"] is None
                # tools is the first positional arg (index 0)
                tools = call_args.args[0]
                assert len(tools) == 2
                tool_names = {t.name for t in tools}
                assert tool_names == {"tool1", "tool2"}
    finally:
        otinstaller.registry.load_registry = original_load_registry


# Example CLI tests


def test_example_with_real_file(monkeypatch, tmp_path):
    """example with a real example file loads and displays the content."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Use sherlock which has a real example file in the package data
    result = runner.invoke(app, ["example", "sherlock"])
    assert result.exit_code == 0
    assert "example output for sherlock" in result.output
    assert "[+] Checking username: exampleuser" in result.output


def test_example_no_example_field(monkeypatch, tmp_path):
    """example for a tool with no example field shows message and exits 0."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Create a tool without example field
    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="noexample",
                display_name="No Example Tool",
                description="A tool without example",
                install=Install(method="pip", package="noexample"),
                entrypoint=Entrypoint(command="noexample"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
            ),
        ]

    otinstaller.registry.load_registry = mock_load_registry

    try:
        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["example", "noexample"])
        assert result.exit_code == 0
        assert "no example available for noexample yet" in result.output
        assert "install it and run it yourself" in result.output
    finally:
        otinstaller.registry.load_registry = original_load_registry


def test_example_unknown_tool(monkeypatch, tmp_path):
    """example for an unknown tool name shows suggestions."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["example", "nonexistent"])
    assert result.exit_code == 1
    assert "error: unknown tool 'nonexistent'" in result.output


def test_example_json_output(monkeypatch, tmp_path):
    """example --json outputs correct shape."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    # Create a mock tool with example
    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="testtool",
                display_name="Test Tool",
                description="A tool with example",
                install=Install(method="pip", package="testtool"),
                entrypoint=Entrypoint(command="testtool"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                example="examples/testtool.txt",
            ),
        ]

        otinstaller.registry.load_registry = mock_load_registry

        # Create example file in a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            examples_dir = Path(tmpdir) / "examples"
            examples_dir.mkdir(parents=True, exist_ok=True)
            example_file = examples_dir / "testtool.txt"
            example_file.write_text("example content\n")

            try:
                runner = CliRunner()
                result = runner.invoke(app, ["example", "testtool", "--json"])
                assert result.exit_code == 0
                import json

                data = json.loads(result.output)

                assert data["tool"] == "testtool"
                assert data["has_example"] is True
                assert data["content"] == "example content\n"
                assert "error" not in data

                # Test without example (unknown tool - outputs text error, not JSON)
                result = runner.invoke(app, ["example", "nonexistent", "--json"])
                assert result.exit_code == 1
                assert "error: unknown tool 'nonexistent'" in result.output
            finally:
                otinstaller.registry.load_registry = original_load_registry


def test_examples_dir_matches_registry(monkeypatch, tmp_path):
    """Guard test: every example file must correspond to a tool in registry."""
    from otinstaller import data
    from otinstaller.registry import default_registry_path, load_registry

    # Get all example files from the package data directory
    examples_dir = importlib.resources.files(data) / "examples"
    example_files = {f.name for f in examples_dir.iterdir() if f.is_file() and f.suffix == ".txt"}

    # Get all tools from registry that have example field
    tools_registry = load_registry(default_registry_path())
    registry_examples = {t.example for t in tools_registry if t.example}

    # Every example file must have a corresponding tool in registry
    for example_file in example_files:
        expected_path = f"examples/{example_file}"
        msg = f"Example file {example_file} has no corresponding tool in registry"
        assert expected_path in registry_examples, msg

    # Every tool with example field must have a corresponding file
    for example_path in registry_examples:
        filename = example_path.split("/")[-1]
        assert filename in example_files, (
            f"Registry references example {example_path} but file {filename} does not exist"
        )


def test_example_missing_file_errors_cleanly(monkeypatch, tmp_path):
    """example for a tool whose example file is missing errors cleanly."""
    from typer.testing import CliRunner

    from otinstaller.cli import app

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0

    import otinstaller.registry

    original_load_registry = otinstaller.registry.load_registry
    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    def mock_load_registry(path):
        return [
            Tool(
                name="broken",
                display_name="Broken Tool",
                description="Tool with missing example file",
                install=Install(method="pip", package="broken"),
                entrypoint=Entrypoint(command="broken"),
                api_keys=ApiKeys(required=(), optional=()),
                capabilities=[],
                tier="community",
                example="examples/nonexistent.txt",
            ),
        ]

    original_load_registry = otinstaller.registry.load_registry
    monkeypatch.setattr(otinstaller.registry, "load_registry", mock_load_registry)

    try:
        runner = CliRunner()
        result = runner.invoke(app, ["init", "--yes"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["example", "broken"])
        assert result.exit_code == 1
        assert "error: example file for broken could not be loaded" in result.output
    finally:
        otinstaller.registry.load_registry = original_load_registry
