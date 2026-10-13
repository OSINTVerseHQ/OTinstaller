"""Playbook tests."""

from pathlib import Path

import yaml

from otinstaller.registry import default_registry_path, load_registry


def _load_playbooks():
    """Load all playbook YAML files."""
    playbook_dir = Path("playbooks")
    if not playbook_dir.exists():
        return []
    playbooks = []
    for pf in sorted(playbook_dir.glob("*.yaml")):
        with pf.open() as f:
            data = yaml.safe_load(f)
        data["filename"] = pf.stem
        playbooks.append(data)
    return playbooks


def _infer_playbook_target_type(playbook_name: str) -> str:
    """Infer the expected target type from playbook name."""
    if "domain" in playbook_name:
        return "domain"
    if "username" in playbook_name:
        return "username"
    if "email" in playbook_name:
        return "email"
    if "ip" in playbook_name:
        return "ip"
    if "url" in playbook_name:
        return "url"
    # Default fallback
    return "domain"


def test_playbook_tools_accept_target_type():
    """Static test: every playbook's tools accept that playbook's target type."""
    playbooks = _load_playbooks()
    registry = load_registry(default_registry_path())
    tools_by_name = {t.name: t for t in registry}

    for pb in playbooks:
        name = pb["filename"]
        expected_type = _infer_playbook_target_type(name)
        tools = pb.get("tools", [])

        for tool_name in tools:
            tool = tools_by_name.get(tool_name)
            assert tool is not None, (
                f"Tool '{tool_name}' in playbook '{name}' not found in registry"
            )
            accepts = tool.accepts or []
            assert expected_type in accepts, (
                f"Tool '{tool_name}' in playbook '{name}' does not accept "
                f"target type '{expected_type}' (accepts: {accepts})"
            )


def test_playbook_at_least_one_tool_compatible():
    """At least one tool in each playbook accepts the playbook's target type."""
    playbooks = _load_playbooks()
    registry = load_registry(default_registry_path())
    tools_by_name = {t.name: t for t in registry}

    for pb in playbooks:
        name = pb["filename"]
        expected_type = _infer_playbook_target_type(name)
        tools = pb.get("tools", [])

        compatible = [
            tool_name
            for tool_name in tools
            if tools_by_name.get(tool_name) and expected_type in tools_by_name[tool_name].accepts
        ]
        assert compatible, (
            f"Playbook '{name}' has no tools compatible with target type '{expected_type}'"
        )
