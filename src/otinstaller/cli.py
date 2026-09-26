"""CLI entry point."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from otinstaller import __version__
from otinstaller.config import (
    ensure_dir,
    get_distro,
    get_distro_family,
    get_env_file,
    get_home,
    get_logs_dir,
    get_results_dir,
    get_tools_dir,
)
from otinstaller.installer import (
    AlreadyInstalled,
    InstallError,
    install_tool,
    remove_tool,
)
from otinstaller.notice import (
    NOTICE_SHORT,
    NOTICE_TEXT,
    has_accepted,
    record_acceptance,
)
from otinstaller.registry import (
    RegistryError,
    default_registry_path,
    find_tool,
    load_registry,
    search_tools,
    suggest_names,
)
from otinstaller.results import write_meta
from otinstaller.runner import run_tool, run_tools_parallel
from otinstaller.state import list_installed

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


def version_callback(value: bool):
    if value:
        typer.echo(f"otinstaller {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=version_callback, is_eager=True, help="Show version and exit"
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    pass


def _load_registry(verbose: bool) -> list:
    try:
        path = default_registry_path()
        if verbose:
            typer.echo(f"Using registry: {path}", err=True)
        return load_registry(path)
    except RegistryError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1) from e


def _make_console(no_color: bool) -> Console:
    return Console(color_system=None if no_color else "auto")


def _print_table(console: Console, tools: list, json_output: bool) -> None:
    if json_output:
        data = [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "tier": t.tier,
                "capabilities": list(t.capabilities),
            }
            for t in tools
        ]
        typer.echo(json.dumps(data))
        return

    if not tools:
        typer.echo("no tools in the registry")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Tier")
    table.add_column("Description")
    for tool in tools:
        table.add_row(tool.name, tool.tier, tool.description)
    console.print(table)
    count = len(tools)
    typer.echo(f"{count} tool{'s' if count != 1 else ''}")


@app.command(name="list")
def list_tools(
    installed: Annotated[
        bool,
        typer.Option("--installed", help="List only installed tools"),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """List available tools."""
    if installed:
        tools = list_installed()
        console = _make_console(no_color)

        if json_output:
            from dataclasses import asdict

            data = [asdict(t) for t in tools]
            typer.echo(json.dumps(data, default=str))
            return

        if not tools:
            typer.echo("no tools installed")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Version")
        table.add_column("Method")
        table.add_column("Installed")
        for tool in tools:
            # Only show date part of installed_at
            installed_date = (
                tool.installed_at.split("T")[0] if "T" in tool.installed_at else tool.installed_at
            )
            table.add_row(tool.name, tool.version, tool.method, installed_date)
        console.print(table)
        count = len(tools)
        typer.echo(f"{count} tool{'s' if count != 1 else ''}")
        return

    tools = _load_registry(verbose)
    console = _make_console(no_color)
    _print_table(console, tools, json_output)


@app.command()
def search(
    query: Annotated[list[str], typer.Argument(help="Search query words")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Search for tools."""
    tools = _load_registry(verbose)
    console = _make_console(no_color)

    query_str = " ".join(query)
    results = search_tools(tools, query_str)

    if json_output:
        data = [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "tier": t.tier,
                "capabilities": list(t.capabilities),
            }
            for t in results
        ]
        typer.echo(json.dumps(data))
        return

    if not results:
        typer.echo(f"no tools match '{query_str}'")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Tier")
    table.add_column("Description")
    for tool in results:
        table.add_row(tool.name, tool.tier, tool.description)
    console.print(table)
    count = len(results)
    typer.echo(f"{count} tool{'s' if count != 1 else ''}")


@app.command()
def info(
    tool_name: Annotated[str, typer.Argument(help="Tool name")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Show tool information."""
    tools = _load_registry(verbose)

    tool = find_tool(tools, tool_name)
    if not tool:
        suggestions = suggest_names(tools, tool_name)
        msg = f"error: unknown tool '{tool_name}'"
        if suggestions:
            msg += f"\ndid you mean: {', '.join(suggestions)}?"
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)

    if json_output:
        from dataclasses import asdict

        typer.echo(json.dumps(asdict(tool), default=str))
        return

    console = _make_console(no_color)

    lines = []
    lines.append(f"{tool.display_name} ({tool.name})")
    lines.append(tool.description)
    lines.append(f"Tier: {tool.tier}")

    if tool.repo:
        lines.append(f"Repo: {tool.repo}")
    if tool.license:
        lines.append(f"License: {tool.license}")

    if tool.install.method == "pip":
        pkg = tool.install.package or ""
        ver = f" ({tool.install.version})" if tool.install.version else ""
        lines.append(f"Install: pip {pkg}{ver}")
    else:
        lines.append(f"Install: git {tool.install.url}")
        if tool.install.ref:
            lines.append(f"Ref: {tool.install.ref}")
        if tool.install.requirements:
            lines.append(f"Requirements: {tool.install.requirements}")
        if tool.install.as_package:
            lines.append("As package: yes")

    if tool.entrypoint.command:
        lines.append(f"Entrypoint: {tool.entrypoint.command}")
    elif tool.entrypoint.script:
        lines.append(f"Entrypoint: {tool.entrypoint.script}")

    if tool.capabilities:
        lines.append(f"Capabilities: {', '.join(tool.capabilities)}")

    api_keys = []
    if tool.api_keys.required:
        api_keys.append(f"required: {', '.join(tool.api_keys.required)}")
    if tool.api_keys.optional:
        api_keys.append(f"optional: {', '.join(tool.api_keys.optional)}")
    if api_keys:
        lines.append(f"API keys: {'; '.join(api_keys)}")
    else:
        lines.append("API keys: none")

    if tool.verified:
        lines.append(
            f"Verified: {tool.verified.date} with version {tool.verified.version} "
            f"on {tool.verified.os}, python {tool.verified.python}"
        )
    else:
        lines.append("Not verified yet")

    if "dual-use" in tool.capabilities:
        lines.append("Dual-use tool. See the responsible use notice in the README.")

    for line in lines:
        console.print(line)


@app.command()
def install(
    names: Annotated[list[str], typer.Argument(help="Tool names to install")],
    force: Annotated[bool, typer.Option("--force", help="Reinstall if already installed")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Install tools by name."""
    if sys.platform != "linux":
        typer.echo("error: otinstaller currently supports Linux only", err=True)
        raise typer.Exit(code=1)
    if not has_accepted():
        typer.echo("error: run 'otinstaller init' first", err=True)
        raise typer.Exit(code=1)

    tools_registry = _load_registry(verbose)

    # Resolve all names
    tools = []
    errors = []
    for name in names:
        tool = find_tool(tools_registry, name)
        if not tool:
            suggestions = suggest_names(tools_registry, name)
            msg = f"error: unknown tool '{name}'"
            if suggestions:
                msg += f"\ndid you mean: {', '.join(suggestions)}?"
            errors.append(msg)
        else:
            tools.append(tool)

    if errors:
        for err in errors:
            typer.echo(err, err=True)
        raise typer.Exit(code=1)

    # Print what will be installed
    has_dual_use = False
    for tool in tools:
        if tool.install.method == "pip":
            spec = tool.install.package or ""
            if tool.install.version:
                spec += f"=={tool.install.version}"
            typer.echo(f"{tool.name} (pip: {spec})")
        else:
            typer.echo(f"{tool.name} (git: {tool.install.url})")
        if "dual-use" in tool.capabilities:
            has_dual_use = True

    if has_dual_use:
        typer.echo(NOTICE_SHORT)

    # Confirmation
    if not yes:
        if not sys.stdin.isatty():
            typer.echo("error: confirmation needed, run with --yes", err=True)
            raise typer.Exit(code=1)
        answer = typer.prompt("Install? [y/N]", default="n")
        if answer.lower() != "y":
            typer.echo("cancelled")
            raise typer.Exit(code=1)

    # Install
    installed_count = 0
    skipped_count = 0
    failed_count = 0
    console = _make_console(no_color)

    for tool in tools:
        try:
            with console.status(f"Installing {tool.name}..."):
                result = install_tool(tool, force=force, stream=verbose)
            typer.echo(f"installed {result.name} {result.version}")
            installed_count += 1
        except AlreadyInstalled:
            typer.echo(f"{tool.name} is already installed (use --force to reinstall)")
            skipped_count += 1
        except InstallError as e:
            typer.echo(f"error: {tool.name}: {e}")
            log = get_logs_dir() / f"install-{tool.name}.log"
            if log.exists():
                typer.echo(f"log: {log}")
            failed_count += 1
        except Exception as e:
            typer.echo(f"error: {tool.name}: {e}")
            log = get_logs_dir() / f"install-{tool.name}.log"
            if log.exists():
                typer.echo(f"log: {log}")
            failed_count += 1

    typer.echo(f"{installed_count} installed, {skipped_count} skipped, {failed_count} failed")

    if failed_count > 0:
        raise typer.Exit(code=1)


@app.command()
def remove(
    names: Annotated[list[str] | None, typer.Argument(help="Tool names to remove")] = None,
    all_tools: Annotated[bool, typer.Option("--all", help="Remove all installed tools")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Remove installed tools."""
    if sys.platform != "linux":
        typer.echo("error: otinstaller currently supports Linux only", err=True)
        raise typer.Exit(code=1)
    if names is None:
        names = []

    if all_tools and names:
        typer.echo("error: cannot use both names and --all", err=True)
        raise typer.Exit(code=1)

    if not all_tools and not names:
        typer.echo("error: specify tool names or --all", err=True)
        raise typer.Exit(code=1)

    # Get list of tools to remove
    if all_tools:
        installed = list_installed()
        if not installed:
            typer.echo("nothing to remove")
            raise typer.Exit(code=0)
        tools_to_remove = [t.name for t in installed]
    else:
        tools_to_remove = names

    # Confirmation
    if not yes:
        if not sys.stdin.isatty():
            typer.echo("error: confirmation needed, run with --yes", err=True)
            raise typer.Exit(code=1)
        answer = typer.prompt("Remove? [y/N]", default="n")
        if answer.lower() != "y":
            typer.echo("cancelled")
            raise typer.Exit(code=1)

    # Remove
    removed_count = 0
    failed_count = 0

    for name in tools_to_remove:
        try:
            if remove_tool(name):
                typer.echo(f"removed {name}")
                removed_count += 1
            else:
                typer.echo(f"error: {name} is not installed")
                failed_count += 1
        except Exception as e:
            typer.echo(f"error: {name}: {e}")
            failed_count += 1

    if failed_count > 0:
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    case: Annotated[
        str | None, typer.Option("--case", help="Group runs under a named case")
    ] = None,
    target: Annotated[
        str | None, typer.Option("--target", help="Target for the run (default: first extra arg)")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Stream tool output to terminal")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
    parallel: Annotated[
        int, typer.Option("--parallel", "-p", help="Max concurrent tools (default: 4)")
    ] = 4,
):
    """Run one or more tools with arguments passed through after --.

    If a target argument after -- happens to match a registered tool name,
    it will be interpreted as an additional tool to run. Use --target to
    disambiguate in that case.
    """
    raw_args = list(ctx.args)
    # Click strips the -- separator when allow_extra_args=True, so it won't be in ctx.args.
    # Parse tool names from the registry: collect known tool names until first non-tool.
    if "--" in raw_args:
        # Should not happen with allow_extra_args=True, but handle just in case
        sep_index = raw_args.index("--")
        tool_names = raw_args[:sep_index]
        extra_args = raw_args[sep_index + 1 :]
    else:
        tools_registry = _load_registry(False)
        known_tools = {t.name for t in tools_registry}
        tool_names = []
        extra_args = []
        for arg in raw_args:
            if arg in known_tools:
                tool_names.append(arg)
            else:
                # First non-tool arg and everything after are extra args
                idx = raw_args.index(arg)
                extra_args = raw_args[idx:]
                break
        else:
            # All args were tool names
            tool_names = raw_args
            extra_args = []

    if sys.platform != "linux":
        typer.echo("error: otinstaller currently supports Linux only", err=True)
        raise typer.Exit(code=1)

    tools_registry = _load_registry(False)

    # Resolve all tools
    tools = []
    errors = []
    for name in tool_names:
        t = find_tool(tools_registry, name)
        if not t:
            suggestions = suggest_names(tools_registry, name)
            msg = f"error: unknown tool '{name}'"
            if suggestions:
                msg += f"\ndid you mean: {', '.join(suggestions)}?"
            errors.append(msg)
        else:
            tools.append((name, t))

    if errors:
        for err in errors:
            typer.echo(err, err=True)
        raise typer.Exit(code=1)

    # Check if all tools are installed
    from otinstaller.state import get_installed

    installed_tools = {}
    for name, _t in tools:
        installed = get_installed(name)
        if not installed:
            typer.echo(
                f"error: {name} is not installed, run 'otinstaller install {name}' first",
                err=True,
            )
            raise typer.Exit(code=1)
        installed_tools[name] = installed

    # Validate parallel option
    if parallel < 1:
        typer.echo("error: --parallel must be at least 1", err=True)
        raise typer.Exit(code=1)

    # Determine target (same for all tools)
    run_target = target if target is not None else (extra_args[0] if extra_args else "unspecified")

    # Prepare roots dict
    roots = {name: get_tools_dir() / name for name, _t in tools}

    # Single tool: use existing run_tool path
    if len(tools) == 1:
        name, t = tools[0]
        installed = installed_tools[name]
        root = roots[name]

        console = _make_console(no_color)
        use_spinner = not no_color and sys.stdout.isatty()

        try:
            if use_spinner:
                with console.status(f"running {name}..."):
                    meta = run_tool(
                        t,
                        root,
                        extra_args,
                        target=run_target,
                        case=case,
                        env_overrides=None,
                        stream=verbose,
                    )
            else:
                typer.echo(f"running {name}...")
                meta = run_tool(
                    t,
                    root,
                    extra_args,
                    target=run_target,
                    case=case,
                    env_overrides=None,
                    stream=verbose,
                )

            meta.tool_version = installed.version
            results_dir = get_results_dir()
            meta_path = results_dir / Path(meta.output_path).with_suffix(".meta.json")
            write_meta(meta, meta_path)

            typer.echo(f"tool exited {meta.exit_code}")
            typer.echo(f"saved to {meta.output_path}")
            typer.echo(f"sha256  {meta.sha256}")

            if meta.exit_code != 0:
                raise typer.Exit(code=meta.exit_code)

        except KeyboardInterrupt:
            msg = "interrupted, partial output saved to "
            if "meta" in locals() and hasattr(meta, "output_path"):
                msg += meta.output_path
            else:
                msg += "unknown"
            typer.echo(msg, err=True)
            raise typer.Exit(code=130) from None

    # Multiple tools: use run_tools_parallel
    else:
        tool_list = [t for _name, t in tools]
        try:
            results = asyncio.run(
                run_tools_parallel(
                    tool_list,
                    roots,
                    extra_args,
                    target=run_target,
                    case=case,
                    max_parallel=parallel,
                    stream=verbose,
                )
            )
        except KeyboardInterrupt:
            typer.echo("interrupted", err=True)
            raise typer.Exit(code=130) from None

        # Print results as they complete (results are in input order)
        ok_count = 0
        failed_count = 0
        for meta in results:
            meta.tool_version = installed_tools[meta.tool].version
            results_dir = get_results_dir()
            meta_path = results_dir / Path(meta.output_path).with_suffix(".meta.json")
            write_meta(meta, meta_path)

            if meta.exit_code == 0:
                typer.echo(f"{meta.tool} done (exit 0)")
                ok_count += 1
            else:
                typer.echo(f"{meta.tool} failed (exit {meta.exit_code})")
                failed_count += 1

        typer.echo(f"{ok_count} ok, {failed_count} failed")

        if failed_count > 0:
            raise typer.Exit(code=1)


@app.command()
def update(
    names: Annotated[list[str] | None, typer.Argument(help="Tool names to update")] = None,
    all_tools: Annotated[bool, typer.Option("--all", help="Update all installed tools")] = False,
):
    """Update installed tools."""
    if names is None:
        names = []
    typer.echo("not implemented yet")
    raise typer.Exit(code=2)


@app.command()
def example(tool: Annotated[str, typer.Argument(help="Tool name")]):
    """Show usage examples for a tool."""
    typer.echo("not implemented yet")
    raise typer.Exit(code=2)


@app.command()
def init(
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Accept notice without prompting")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Initialize configuration and directories."""
    # Create directories
    ensure_dir(get_home())
    ensure_dir(get_tools_dir())
    ensure_dir(get_logs_dir())

    # Handle notice acceptance
    if not has_accepted():
        console = _make_console(no_color)
        console.print(NOTICE_TEXT)
        if not yes:
            if not sys.stdin.isatty():
                typer.echo("error: confirmation needed, run with --yes", err=True)
                raise typer.Exit(code=1)
            answer = typer.prompt("Do you accept? [y/N]", default="n")
            if answer.lower() != "y":
                typer.echo("notice not accepted", err=True)
                raise typer.Exit(code=1)
        record_acceptance()

    # Handle .env file
    env_file = get_env_file()
    env_content = (
        "# API keys for tools managed by otinstaller.\n"
        "# Add one KEY=value per line. Keep this file private.\n"
    )
    if not env_file.exists():
        env_file.write_text(env_content)
        os.chmod(env_file, 0o600)
    else:
        # Fix permissions if needed
        try:
            current_mode = env_file.stat().st_mode & 0o777
            if current_mode != 0o600:
                os.chmod(env_file, 0o600)
                typer.echo(f"fixed permissions on {env_file}")
        except OSError:
            pass

    # Print summary
    typer.echo(f"Home directory: {get_home()}")
    typer.echo(f"Tools directory: {get_tools_dir()}")
    typer.echo(f"Env file: {env_file}")


keys_app = typer.Typer(no_args_is_help=True, help="Manage API keys.")
app.add_typer(keys_app, name="keys")


@keys_app.command("check")
def keys_check(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
):
    """Check API keys configuration."""
    import sys

    if sys.platform != "linux":
        typer.echo("error: otinstaller currently supports Linux only", err=True)
        raise typer.Exit(code=1)

    from otinstaller.keys import load_env_file, missing_required_keys
    from otinstaller.registry import default_registry_path, load_registry

    tools = load_registry(default_registry_path())

    # Collect all key names mentioned by any tool
    all_key_names: set[str] = set()
    for tool in tools:
        all_key_names.update(tool.api_keys.required)
        all_key_names.update(tool.api_keys.optional)

    if not all_key_names:
        if json_output:
            import json

            typer.echo(json.dumps({"keys": {}, "tools_missing_keys": {}, "coverage_hints": {}}))
        else:
            typer.echo("no tools in the registry need API keys")
        return

    # Check each key
    key_status: dict[str, bool] = {}
    for key in sorted(all_key_names):
        key_status[key] = key in load_env_file()

    # Check tools
    tools_missing_keys: dict[str, list[str]] = {}
    for tool in tools:
        missing = missing_required_keys(tool, load_env_file())
        if missing:
            tools_missing_keys[tool.name] = missing

    # Coverage hints
    coverage_hints: dict[str, int] = {}
    for key in sorted(all_key_names):
        if key not in load_env_file():
            count = 0
            for tool in tools:
                if key in tool.api_keys.required or key in tool.api_keys.optional:
                    # Check if tool would be fully satisfied with this key
                    missing = missing_required_keys(tool, load_env_file())
                    if key in missing and len(missing) == 1:
                        count += 1
            if count > 0:
                coverage_hints[key] = count

    if json_output:
        import json

        output = {
            "keys": {k: "set" if v else "missing" for k, v in key_status.items()},
            "tools_missing_keys": tools_missing_keys,
            "coverage_hints": coverage_hints,
        }
        import json

        typer.echo(json.dumps(output))
        return

    # Human-readable output
    for key, present in key_status.items():
        status = "✓" if present else "✗"
        typer.echo(f"{status} {key}")

    if tools_missing_keys:
        typer.echo("\nthese tools need keys you don't have:")
        for tool_name, missing in tools_missing_keys.items():
            typer.echo(f"  {tool_name}: missing {', '.join(missing)}")

    if coverage_hints:
        typer.echo("\ncoverage hints:")
        for key, count in sorted(coverage_hints.items(), key=lambda x: -x[1]):
            typer.echo(f"  Adding {key} would unlock {count} more tool(s)")


@app.command()
def resume():
    """Resume interrupted jobs."""
    typer.echo("not implemented yet")
    raise typer.Exit(code=2)


@app.command()
def doctor(
    verbose: Annotated[bool, typer.Option("--verbose", help="Verbose output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output")] = False,
):
    """Run diagnostics."""
    import shutil
    import subprocess
    import sys
    import tempfile

    problems = 0

    # 1. Platform check
    if sys.platform != "linux":
        typer.echo("[problem] platform is not Linux")
        problems += 1
        if not verbose:
            raise typer.Exit(code=1)
    else:
        typer.echo("[ok] platform is Linux")

    # 2. Distro detection (informational)
    distro = get_distro()
    typer.echo(f"[ok] distro: {distro}")

    # 3. Python version
    major, minor = sys.version_info[:2]
    if major == 3 and 10 <= minor <= 12:
        typer.echo(f"[ok] python {major}.{minor} is supported")
    else:
        typer.echo(
            f"[problem] python {major}.{minor} is not supported, this project targets 3.10-3.12"
        )
        problems += 1

    # 4. git check
    if shutil.which("git"):
        typer.echo("[ok] git found")
    else:
        typer.echo("[problem] git not found")
        family = get_distro_family()
        if family == "debian":
            typer.echo("  install with: sudo apt install git")
        elif family == "arch":
            typer.echo("  install with: sudo pacman -S git")
        else:
            typer.echo("  install git with your package manager")
        problems += 1

    # 5. venv module check
    venv_ok = False
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "test_venv"
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
        )
        if result.returncode == 0:
            venv_ok = True

    if venv_ok:
        typer.echo("[ok] venv module works")
    else:
        typer.echo("[problem] venv module failed")
        family = get_distro_family()
        py_version = f"python{major}.{minor}"
        if family == "debian":
            typer.echo(f"  install with: sudo apt install {py_version}-venv")
        elif family == "arch":
            typer.echo("  should be included with python on Arch, check your install")
        else:
            typer.echo("  install python-venv with your package manager")
        problems += 1

    # 6. Home directory writable
    home_ok = False
    try:
        home = get_home()
        home.mkdir(parents=True, exist_ok=True)
        test_file = home / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        home_ok = True
    except Exception:
        pass

    if home_ok:
        typer.echo("[ok] home directory writable")
    else:
        typer.echo("[problem] home directory not writable")
        problems += 1

    if problems > 0:
        raise typer.Exit(code=1)
