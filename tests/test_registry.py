"""Registry tests."""

from pathlib import Path

import pytest
import yaml

from otinstaller.registry import (
    RegistryError,
    default_registry_path,
    find_tool,
    load_registry,
    parse_tool,
    search_tools,
    suggest_names,
)


class TestParseTool:
    def test_valid_pip_entry(self):
        data = {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Search usernames",
            "install": {"method": "pip", "package": "sherlock-project"},
            "entrypoint": {"command": "sherlock"},
        }
        tool = parse_tool(data)
        assert tool.name == "sherlock"
        assert tool.install.method == "pip"
        assert tool.install.package == "sherlock-project"

    def test_valid_git_entry(self):
        data = {
            "name": "theharvester",
            "display_name": "theHarvester",
            "description": "Find emails",
            "install": {
                "method": "git",
                "url": "https://github.com/laramies/theHarvester.git",
                "as_package": True,
            },
            "entrypoint": {"command": "theHarvester"},
        }
        tool = parse_tool(data)
        assert tool.name == "theharvester"
        assert tool.install.method == "git"
        assert tool.install.url == "https://github.com/laramies/theHarvester.git"
        assert tool.install.as_package is True


@pytest.mark.parametrize(
    "data,expected_error",
    [
        (
            {
                "name": "Sherlock",
                "display_name": "S",
                "description": "D",
                "install": {},
                "entrypoint": {},
            },
            "name must match",
        ),
        (
            {
                "name": "sherlock!",
                "display_name": "S",
                "description": "D",
                "install": {},
                "entrypoint": {},
            },
            "name must match",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "",
                "description": "D",
                "install": {},
                "entrypoint": {},
            },
            "display_name is required",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "",
                "install": {},
                "entrypoint": {},
            },
            "description is required",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "line1\nline2",
                "install": {},
                "entrypoint": {},
            },
            "description must be one line",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "npm"},
                "entrypoint": {},
            },
            "install.method must be",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip"},
                "entrypoint": {},
            },
            "install.package is required",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "sherlock!"},
                "entrypoint": {},
            },
            "install.package must match",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "sherlock", "version": "v1.0@beta"},
                "entrypoint": {"command": "s"},
            },
            "install.version must match",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "sherlock", "url": "http://x"},
                "entrypoint": {},
            },
            "install.url must not be set",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "git", "url": "http://notgithub.com/x/y.git"},
                "entrypoint": {},
            },
            "install.url must be an https github.com URL",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "git", "url": "https://github.com/x/y.git", "ref": "-bad"},
                "entrypoint": {},
            },
            "install.ref must not start with",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {
                    "method": "git",
                    "url": "https://github.com/x/y.git",
                    "requirements": "r.txt",
                    "as_package": True,
                },
                "entrypoint": {},
            },
            "exactly one of install.requirements or install.as_package",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "git", "url": "https://github.com/x/y.git"},
                "entrypoint": {},
            },
            "exactly one of install.requirements or install.as_package",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {
                    "method": "git",
                    "url": "https://github.com/x/y.git",
                    "requirements": "../r.txt",
                },
                "entrypoint": {},
            },
            "install.requirements must be a relative path",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {},
            },
            "exactly one of entrypoint.command or entrypoint.script",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "s", "script": "s.py"},
            },
            "exactly one of entrypoint.command or entrypoint.script",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "bad!"},
            },
            "entrypoint.command must match",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"script": "s.py"},
            },
            "entrypoint.script only allowed for git method",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "s"},
                "capabilities": ["BadCap"],
            },
            "capabilities entries must be lowercase",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "s"},
                "api_keys": {"required": ["bad_key"]},
            },
            "api key 'bad_key' must match",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "s"},
                "stars": -1,
            },
            "stars must be a non-negative integer",
        ),
        (
            {
                "name": "sherlock",
                "display_name": "S",
                "description": "D",
                "install": {"method": "pip", "package": "s"},
                "entrypoint": {"command": "s"},
                "unknown_field": "x",
            },
            "unknown key 'unknown_field'",
        ),
    ],
)
def test_parse_tool_validation_errors(data, expected_error):
    with pytest.raises(RegistryError) as exc:
        parse_tool(data)
    assert expected_error in str(exc.value)


def test_duplicate_names_fail():
    data = {
        "tools": [
            {
                "name": "sherlock",
                "display_name": "S1",
                "description": "D",
                "install": {"method": "pip", "package": "p1"},
                "entrypoint": {"command": "c1"},
            },
            {
                "name": "sherlock",
                "display_name": "S2",
                "description": "D",
                "install": {"method": "pip", "package": "p2"},
                "entrypoint": {"command": "c2"},
            },
        ]
    }
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        with pytest.raises(RegistryError, match="duplicate tool name: sherlock"):
            load_registry(Path(f.name))


def test_load_registry_empty():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"tools": []}, f)
        f.flush()
        tools = load_registry(Path(f.name))
        assert tools == []


def test_load_registry_missing_file():
    with pytest.raises(RegistryError, match="registry file not found"):
        load_registry(Path("/nonexistent/path.yaml"))


def test_load_registry_invalid_yaml():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: [")
        f.flush()
        with pytest.raises(RegistryError, match="invalid YAML"):
            load_registry(Path(f.name))


def test_load_registry_not_a_list():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"tools": "not a list"}, f)
        f.flush()
        with pytest.raises(RegistryError, match="must have a 'tools' list"):
            load_registry(Path(f.name))


def test_default_registry_path_env(monkeypatch, tmp_path):
    reg = tmp_path / "custom.yaml"
    reg.write_text("tools: []")
    monkeypatch.setenv("OTINSTALLER_REGISTRY", str(reg))
    assert default_registry_path() == reg


def test_default_registry_path_home(monkeypatch, tmp_path):
    monkeypatch.delenv("OTINSTALLER_REGISTRY", raising=False)
    home = tmp_path / ".otinstaller"
    home.mkdir()
    reg = home / "registry.yaml"
    reg.write_text("tools: []")
    monkeypatch.setattr("otinstaller.registry.get_home", lambda: home)
    assert default_registry_path() == reg


def test_default_registry_path_bundled(monkeypatch, tmp_path):
    monkeypatch.delenv("OTINSTALLER_REGISTRY", raising=False)
    monkeypatch.setattr("otinstaller.registry.get_home", lambda: tmp_path / "home")
    # Should fall back to bundled
    path = default_registry_path()
    assert "registry.yaml" in str(path)


def test_bundled_registry_loads():
    tools = load_registry(default_registry_path())
    names = [t.name for t in tools]
    # Should have 39 tools (40 - 2 denylisted + 1 theHarvester added back)
    assert len(tools) == 39
    assert "sherlock" in names
    assert "maigret" in names
    assert "theharvester" in names
    # Check a few more from the new registry
    assert "spiderfoot" in names
    assert "ghunt" in names
    assert "holehe" in names


def test_find_tool_case_insensitive():
    data = {
        "name": "sherlock",
        "display_name": "Sherlock",
        "description": "Search usernames",
        "install": {"method": "pip", "package": "sherlock-project"},
        "entrypoint": {"command": "sherlock"},
    }
    tool = parse_tool(data)
    assert find_tool([tool], "SHERLOCK") is tool
    assert find_tool([tool], "sherlock") is tool
    assert find_tool([tool], "Sherlock") is tool
    assert find_tool([tool], "other") is None


def test_search_tools_ranks_name_matches_first():
    data1 = {
        "name": "sherlock",
        "display_name": "Sherlock",
        "description": "Search",
        "install": {"method": "pip", "package": "s"},
        "entrypoint": {"command": "c"},
        "capabilities": ["username"],
    }
    data2 = {
        "name": "maigret",
        "display_name": "Maigret",
        "description": "Sherlock search",
        "install": {"method": "pip", "package": "m"},
        "entrypoint": {"command": "c"},
        "capabilities": ["username"],
    }
    t1 = parse_tool(data1)
    t2 = parse_tool(data2)
    results = search_tools([t1, t2], "sherlock")
    assert results[0].name == "sherlock"


def test_search_tools_requires_all_words():
    data = {
        "name": "sherlock",
        "display_name": "Sherlock",
        "description": "Search usernames",
        "install": {"method": "pip", "package": "s"},
        "entrypoint": {"command": "c"},
    }
    tool = parse_tool(data)
    assert search_tools([tool], "sherlock usernames") == [tool]
    assert search_tools([tool], "sherlock notthere") == []


def test_search_tools_empty_query():
    data = {
        "name": "sherlock",
        "display_name": "Sherlock",
        "description": "Search",
        "install": {"method": "pip", "package": "s"},
        "entrypoint": {"command": "c"},
    }
    tool = parse_tool(data)
    assert search_tools([tool], "") == []
    assert search_tools([tool], "   ") == []


def test_suggest_names():
    data = {
        "name": "sherlock",
        "display_name": "Sherlock",
        "description": "Search",
        "install": {"method": "pip", "package": "s"},
        "entrypoint": {"command": "c"},
    }
    tool = parse_tool(data)
    suggestions = suggest_names([tool], "sherlok")
    assert "sherlock" in suggestions


def test_tool_sorted_by_name():
    data1 = {
        "name": "ztool",
        "display_name": "Z",
        "description": "D",
        "install": {"method": "pip", "package": "z"},
        "entrypoint": {"command": "z"},
    }
    data2 = {
        "name": "atool",
        "display_name": "A",
        "description": "D",
        "install": {"method": "pip", "package": "a"},
        "entrypoint": {"command": "a"},
    }
    t1 = parse_tool(data1)
    t2 = parse_tool(data2)
    tools_list = [t1, t2]
    tools_list.sort(key=lambda t: t.name)
    assert tools_list[0].name == "atool"
    assert tools_list[1].name == "ztool"


def test_accepts_field_valid_values():
    data = {
        "name": "testtool",
        "display_name": "Test Tool",
        "description": "Test",
        "install": {"method": "pip", "package": "test"},
        "entrypoint": {"command": "test"},
        "accepts": ["username", "email", "domain", "ip", "phone", "url", "name"],
    }
    tool = parse_tool(data)
    assert tool.accepts == (
        "username",
        "email",
        "domain",
        "ip",
        "phone",
        "url",
        "name",
    )


def test_accepts_field_invalid_value():
    data = {
        "name": "testtool",
        "display_name": "Test Tool",
        "description": "Test",
        "install": {"method": "pip", "package": "test"},
        "entrypoint": {"command": "test"},
        "accepts": ["username", "invalid_value"],
    }
    with pytest.raises(RegistryError) as exc:
        parse_tool(data)
    assert "accepts value 'invalid_value' must be one of" in str(exc.value)
    assert "username" in str(exc.value)


def test_accepts_field_default_empty():
    data = {
        "name": "testtool",
        "display_name": "Test Tool",
        "description": "Test",
        "install": {"method": "pip", "package": "test"},
        "entrypoint": {"command": "test"},
    }
    tool = parse_tool(data)
    assert tool.accepts == ()


def test_bundled_registry_all_entries_parse_and_pass_denylist():
    """Regression test: every entry in the bundled registry must parse and pass denylist."""
    from otinstaller.denylist import check_tool, load_denylist

    tools = load_registry(default_registry_path())

    # Every entry must parse successfully (already done by load_registry)
    assert len(tools) == 39

    # Load denylist and check each tool
    denylist = load_denylist(Path("registry/denylist.yaml"))
    denied = []
    for tool in tools:
        reason = check_tool(tool, denylist)
        if reason:
            denied.append((tool.name, reason))

    assert denied == [], f"Denied tools found: {denied}"
