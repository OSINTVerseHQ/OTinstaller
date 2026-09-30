#!/usr/bin/env python3
"""Generate static status page from pipeline verification log."""

import json
from pathlib import Path

LOG_PATH = Path("pipeline/verification_log.jsonl")
OUTPUT_PATH = Path("docs/status.html")


def load_verification_log():
    """Load and parse the verification log."""
    tools = {}
    with LOG_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            name = entry["name"]
            if name not in tools or entry.get("tested_at", "") > tools[name].get("tested_at", ""):
                tools[name] = entry
    return tools


def load_registry():
    """Load registry to get all tool names."""
    import yaml

    with open("src/otinstaller/data/registry.yaml") as f:
        data = yaml.safe_load(f)
    return {t["name"]: t for t in data["tools"]}


def generate_html(tools_data, registry):
    """Generate HTML status page."""
    rows = []
    for name, _ in sorted(registry.items()):
        verification = tools_data.get(name)
        if verification:
            status = verification.get("outcome", "unknown")
            tested_at = verification.get("tested_at", "N/A")
            if tested_at != "N/A":
                tested_at = tested_at.split("T")[0]
            version = verification.get("version", "")
            status_class = "pass" if status == "passed" else "fail"
        else:
            status = "not tested"
            tested_at = "N/A"
            version = ""
            status_class = "pending"

        rows.append(f"""
        <tr class="{status_class}">
            <td>{name}</td>
            <td>{status}</td>
            <td>{tested_at}</td>
            <td>{version}</td>
        </tr>""")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>otinstaller - Tool Verification Status</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1rem; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #f5f5f5; }}
        tr.pass {{ background: #e8f5e9; }}
        tr.fail {{ background: #fdeaea; }}
        tr.pending {{ background: #fff8e1; }}
        .legend {{ margin-top: 1rem; font-size: 0.85rem; color: #555; }}
        .legend span {{
            display: inline-block; width: 1rem; height: 1rem;
            margin-right: 0.5rem; vertical-align: middle;
        }}
    </style>
</head>
<body>
    <h1>otinstaller Tool Verification Status</h1>
    <p class="meta">
        Generated from pipeline/verification_log.jsonl —
        {len(registry)} registry entries, {len(tools_data)} verified
    </p>
    <table>
        <thead>
            <tr>
                <th>Tool</th>
                <th>Status</th>
                <th>Last Verified</th>
                <th>Version</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    <div class="legend">
        <span style="background:#e8f5e9;"></span> Passed &nbsp;
        <span style="background:#fdeaea;"></span> Failed &nbsp;
        <span style="background:#fff8e1;"></span> Not tested
    </div>
</body>
</html>"""
    return html


def main():
    tools_data = load_verification_log()
    registry = load_registry()
    html = generate_html(tools_data, registry)
    OUTPUT_PATH.write_text(html)
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
