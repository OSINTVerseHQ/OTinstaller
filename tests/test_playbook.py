"""Playbook tests."""

import yaml

from otinstaller.cli import _playbook_files, _target_tool_args, _unattended_skip_reason
from otinstaller.registry import default_registry_path, load_registry


def _load_playbooks():
    """Load the playbooks that ship with the package."""
    playbooks = []
    for pf in _playbook_files():
        with pf.open() as f:
            data = yaml.safe_load(f)
        data["filename"] = pf.stem
        playbooks.append(data)
    return playbooks


def _infer_playbook_target_type(playbook_name: str) -> str:
    """Infer the expected target type from playbook name."""
    for target_type in ("domain", "username", "email", "url", "phone"):
        if target_type in playbook_name:
            return target_type
    return "domain"


_SAMPLE = {
    "domain": "example.com",
    "username": "someuser",
    "email": "someone@example.com",
    "url": "https://example.com",
    "phone": "+15555550100",
}


def test_playbooks_are_bundled(tmp_path, monkeypatch):
    """pip users have no ./playbooks folder, so the playbooks must ship in the package."""
    monkeypatch.chdir(tmp_path)
    names = {pf.stem for pf in _playbook_files()}
    assert {"domain-recon", "username-investigation"} <= names


def test_local_playbook_overrides_bundled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "playbooks").mkdir()
    mine = tmp_path / "playbooks" / "domain-recon.yaml"
    mine.write_text("name: domain-recon\ntools: [dnstwist]\n")
    files = {pf.stem: pf for pf in _playbook_files()}
    assert files["domain-recon"].resolve() == mine.resolve()


def test_playbook_tools_take_the_target():
    """Every tool in a bundled playbook can be given that playbook's target and runs unattended."""
    playbooks = _load_playbooks()
    assert playbooks
    tools_by_name = {t.name: t for t in load_registry(default_registry_path())}

    for pb in playbooks:
        name = pb["filename"]
        target_type = _infer_playbook_target_type(name)
        for tool_name in pb.get("tools", []):
            tool = tools_by_name.get(tool_name)
            assert tool is not None, f"Tool '{tool_name}' in playbook '{name}' not in registry"
            args = _target_tool_args(tool, target_type, _SAMPLE[target_type])
            assert args is not None, (
                f"Tool '{tool_name}' in playbook '{name}' has no input type for '{target_type}'"
            )
            assert _SAMPLE[target_type] in args
            assert _unattended_skip_reason(tool, include_credentialed=True) is None, tool_name


def test_target_args_use_each_tools_flag():
    """auto and playbooks pass the target the way the tool expects it, not as a bare word."""
    tools = {t.name: t for t in load_registry(default_registry_path())}
    assert _target_tool_args(tools["theharvester"], "domain", "example.com") == [
        "--domain",
        "example.com",
    ]
    assert _target_tool_args(tools["h8mail"], "email", "a@example.com") == ["-t", "a@example.com"]
    # default_args are kept, as with typed inputs
    assert _target_tool_args(tools["bbot"], "domain", "example.com")[-2:] == ["-t", "example.com"]
    assert _target_tool_args(tools["sherlock"], "username", "someuser") == ["someuser"]
    # a type the tool has no input for, or one with no typed input at all
    assert _target_tool_args(tools["theharvester"], "email", "a@example.com") is None
    assert _target_tool_args(tools["bbot"], "ip", "8.8.8.8") is None


def test_unattended_runs_skip_prompting_and_setup_tools():
    tools = {t.name: t for t in load_registry(default_registry_path())}
    assert _unattended_skip_reason(tools["ghunt"], include_credentialed=True)  # interactive
    assert _unattended_skip_reason(tools["instagram-monitor"], include_credentialed=True)
    assert _unattended_skip_reason(tools["toutatis"], include_credentialed=False)  # needs setup
    assert _unattended_skip_reason(tools["toutatis"], include_credentialed=True) is None
    assert _unattended_skip_reason(tools["sherlock"], include_credentialed=False) is None
