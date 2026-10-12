"""Build the README tool catalogue from the registry.

Run `python scripts/readme_tools.py` to rewrite the block between the
markers in README.md. `tests/test_readme_tools.py` fails when it is stale.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src" / "otinstaller" / "data" / "registry.yaml"
README = ROOT / "README.md"
START = "<!-- tool-catalogue:start -->"
END = "<!-- tool-catalogue:end -->"
DOCS = "https://osintverse.gitbook.io/otinstaller/tools/"
GROUPS = [
    ("username", "Username"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("domain", "Domain"),
    ("ip", "IP address"),
    ("url", "URL"),
    ("name", "Name"),
]


def load_tools() -> list[dict]:
    return yaml.safe_load(REGISTRY.read_text())["tools"]


def _desc(tool: dict) -> str:
    text = " ".join((tool.get("description") or "").split())
    text = text.split(". ")[0].rstrip(".")
    if len(text) > 110:
        text = text[:107].rsplit(" ", 1)[0] + "..."
    return text.replace("|", "/")


def _inputs(tool: dict) -> str:
    keys = list((tool.get("input_types") or {}).keys())
    return " ".join(f"`{k}:`" for k in keys) if keys else "args after `--`"


def _notes(tool: dict) -> str:
    notes = []
    if tool.get("needs_config"):
        notes.append("needs a login or API key")
    if tool.get("long_running"):
        notes.append("monitors continuously")
    return ", ".join(notes)


def _row(tool: dict) -> str:
    name = tool.get("display_name") or tool["name"]
    link = f"[{name}](https://github.com/{tool['repo']})" if tool.get("repo") else name
    docs = f"[docs]({DOCS}{tool['name']})"
    return f"| {link} ({docs}) | {_desc(tool)} | {_inputs(tool)} | {_notes(tool)} |"


def build(tools: list[dict]) -> str:
    counts = {key: 0 for key, _ in GROUPS}
    for tool in tools:
        for kind in tool.get("accepts") or []:
            if kind in counts:
                counts[kind] += 1
    summary = ", ".join(f"{counts[k]} {label.lower()}" for k, label in GROUPS if counts[k])
    lines = [
        START,
        f"The registry ships **{len(tools)} tools**. By what they accept: {summary}.",
        "A tool that accepts several input types is listed under the first one.",
        "",
    ]
    placed = set()
    for key, label in GROUPS:
        group = sorted(
            (t for t in tools if (t.get("accepts") or [None])[0] == key),
            key=lambda t: t["name"],
        )
        if not group:
            continue
        lines += [
            "<details>",
            f"<summary><b>{label}</b> ({len(group)})</summary>",
            "",
            "| Tool | What it does | Typed inputs | Notes |",
            "| --- | --- | --- | --- |",
        ]
        for t in group:
            lines.append(_row(t))
            placed.add(t["name"])
        lines += ["", "</details>", ""]
    rest = sorted((t for t in tools if t["name"] not in placed), key=lambda t: t["name"])
    if rest:
        lines += ["<details>", f"<summary><b>Other</b> ({len(rest)})</summary>", ""]
        lines += ["| Tool | What it does | Typed inputs | Notes |", "| --- | --- | --- | --- |"]
        lines += [_row(t) for t in rest]
        lines += ["", "</details>", ""]
    lines.append(END)
    return "\n".join(lines)


def render(readme: str, tools: list[dict]) -> str:
    head, _, tail = readme.partition(START)
    _, _, rest = tail.partition(END)
    return head + build(tools) + rest


def main() -> int:
    text = README.read_text()
    if START not in text or END not in text:
        print("markers not found in README.md", file=sys.stderr)
        return 1
    README.write_text(render(text, load_tools()))
    print("README tool catalogue updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
