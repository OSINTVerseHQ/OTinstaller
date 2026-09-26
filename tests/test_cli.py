"""CLI tests."""

import os
import sys
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
    [
        ["update", "tool1"],
        ["example", "tool1"],
        ["keys", "check"],
        ["resume"],
    ],
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
    import json

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
    import json

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
    import json

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
    import json

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
    import json

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
    import json

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
    monkeypatch.setattr("sys.platform", "win32")

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[problem] platform is not Linux" in result.output


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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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
                    assert extra_args == ["someuser", "--timeout", "5"]


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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
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

    with patch("otinstaller.state.get_installed", side_effect=mock_get_installed):
        with patch("otinstaller.cli.run_tool") as _:
            with patch(
                "otinstaller.cli.run_tools_parallel", return_value=[meta1, meta2, meta3]
            ) as _:
                with patch("otinstaller.cli.write_meta") as _:
                    result = runner.invoke(
                        app, ["run", "sherlock", "maigret", "thirdtool", "--", "someuser"]
                    )
                    assert result.exit_code == 1
                    assert "2 ok, 1 failed" in result.output
