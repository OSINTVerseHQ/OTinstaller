#!/usr/bin/env python3
import sys

sys.path.insert(0, "src")

import tempfile
from pathlib import Path

from click.testing import CliRunner

from otinstaller.cli import app
from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

# Create example file in temp dir
with tempfile.TemporaryDirectory() as tmpdir:
    examples_dir = Path(tmpdir) / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    example_file = examples_dir / "testtool.txt"
    example_file.write_text("example output for testtool\n")

    from click.testing import CliRunner

    from otinstaller.registry import ApiKeys, Entrypoint, Install, Tool

    tool = Tool(
        name="testtool",
        display_name="Test Tool",
        description="A tool with example",
        install=Install(method="pip", package="testtool"),
        entrypoint=Entrypoint(command="testtool"),
        api_keys=ApiKeys(required=(), optional=()),
        capabilities=[],
        tier="community",
        example="examples/testtool.txt",  # Use relative path
    )

    # Try to run the example command
    import sys

    from otinstaller.cli import app

    sys.platform = "linux"

    # We need to mock the example file loading

    # Create the example file in the package data location
    examples_dir = Path("/home/otinstaller/src/otinstaller/data/examples")
    example_file = examples_dir / "testtool.txt"
    example_file.write_text("example output for testtool\n")

    runner = CliRunner()
    runner = CliRunner()
    result = runner.invoke(app, ["example", "testtool"])
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.output[:500]}")
