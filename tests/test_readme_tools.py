import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("readme_tools", ROOT / "scripts" / "readme_tools.py")
readme_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readme_tools)


def test_readme_tool_catalogue_is_up_to_date():
    text = (ROOT / "README.md").read_text()
    expected = readme_tools.render(text, readme_tools.load_tools())
    assert text == expected, "README tool catalogue is stale: run python scripts/readme_tools.py"


def test_catalogue_lists_every_tool_once():
    tools = readme_tools.load_tools()
    block = readme_tools.build(tools)
    for tool in tools:
        assert block.count(f"/tools/{tool['name']})") == 1, tool["name"]
