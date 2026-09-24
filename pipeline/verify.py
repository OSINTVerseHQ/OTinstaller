#!/usr/bin/env python3
"""
Verify candidate tools by installing in isolated sandboxes and running smoke tests.

Reads pipeline/candidates.yaml, attempts installation for each likely_installable
candidate, records results in pipeline/verification_log.jsonl, and generates
registry/generated_registry.yaml for passed tools.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from otinstaller.registry import RegistryError, parse_tool

CANDIDATES_PATH = Path("pipeline/candidates.yaml")
LOG_PATH = Path("pipeline/verification_log.jsonl")
OUTPUT_REGISTRY_PATH = Path("registry/generated_registry.yaml")

INSTALL_TIMEOUT = 200
TOTAL_TIMEOUT = 300
SMOKE_TIMEOUT = 60


def load_candidates() -> list[dict[str, Any]]:
    with CANDIDATES_PATH.open() as f:
        return yaml.safe_load(f) or []


def load_verification_log(log_path: Path) -> set[str]:
    tested = set()
    if log_path.exists():
        with log_path.open() as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    tested.add(entry.get("name", ""))
                except json.JSONDecodeError as e:
                    print(f"  WARNING: malformed JSON line {i} in {log_path}: {e}")
                    continue
    return tested


def append_log_entry(log_path: Path, entry: dict[str, Any]) -> None:
    with log_path.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def run_cmd(
    cmd: list[str], cwd: Path | None = None, timeout: int = 60
) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def create_venv(sandbox: Path) -> Path:
    venv_path = sandbox / "venv"
    run_cmd([sys.executable, "-m", "venv", str(venv_path)], timeout=60)
    return venv_path


def pip_install(
    venv: Path, *spec: str, timeout: int = INSTALL_TIMEOUT
) -> subprocess.CompletedProcess:
    pip = venv / "bin" / "pip"
    return run_cmd([str(pip), "install", *spec], timeout=timeout)


def git_clone(repo: str, dest: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    url = f"https://github.com/{repo}.git"
    return run_cmd(["git", "clone", "--depth", "1", url, str(dest)], timeout=timeout)


def _get_console_scripts_from_entry_points(venv: Path, package_name: str) -> list[str]:
    """Read console scripts from installed package's entry_points.txt."""
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = venv / "lib" / pyver / "site-packages"
    normalized = package_name.replace("-", "_")
    dist_info_dirs = list(site_packages.glob(f"{normalized}-*.dist-info"))
    if not dist_info_dirs:
        # Try with hyphens
        dist_info_dirs = list(site_packages.glob(f"{package_name.replace('_', '-')}-*.dist-info"))
    for dist_info in dist_info_dirs:
        entry_points_file = dist_info / "entry_points.txt"
        if entry_points_file.exists():
            console_scripts = []
            in_console_section = False
            for line in entry_points_file.read_text().splitlines():
                line = line.strip()
                if line == "[console_scripts]":
                    in_console_section = True
                    continue
                if line.startswith("[") and in_console_section:
                    break
                if in_console_section and line and "=" in line:
                    script_name = line.split("=")[0].strip()
                    console_scripts.append(script_name)
            if console_scripts:
                return console_scripts
    return []


def detect_entrypoint(
    candidate_name: str,
    repo: str,
    venv_bin: Path,
    install_method: str,
    candidate_pip_package: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, str] | None:
    scripts = list(venv_bin.glob("*"))
    script_names = [s.name for s in scripts if s.is_file() and os.access(s, os.X_OK)]

    # First, try to get console scripts from installed package metadata
    if install_method == "pip-repo" and candidate_pip_package:
        venv = venv_bin.parent
        console_scripts = _get_console_scripts_from_entry_points(venv, candidate_pip_package)
        for script in console_scripts:
            if script in script_names:
                return {"command": script}

    # Exact match
    if candidate_name in script_names:
        return {"command": candidate_name}

    # Fuzzy: swap underscores/hyphens
    variants = {
        candidate_name.replace("_", "-"),
        candidate_name.replace("-", "_"),
    }
    if candidate_pip_package:
        variants.add(candidate_pip_package.replace("_", "-"))
        variants.add(candidate_pip_package.replace("-", "_"))

    for v in variants:
        if v in script_names:
            return {"command": v}

    # Fuzzy: repo name
    repo_short = repo.split("/")[-1]
    if repo_short in script_names:
        return {"command": repo_short}

    # Git-requirements: look for matching script at repo root
    if install_method == "git-requirements" and repo_root:
        py_files = list(repo_root.glob("*.py"))
        # 1. Exact match on candidate name or repo name
        for py_file in py_files:
            stem = py_file.stem
            if stem in (candidate_name, repo_short):
                return {"script": py_file.name}

        # 2. Common entrypoint names
        common_names = {"main", "cli", "run", "app", "server", "start"}
        for py_file in py_files:
            stem = py_file.stem
            if stem.lower() in common_names:
                return {"script": py_file.name}

        # 3. If only one .py file at root, use it
        if len(py_files) == 1:
            return {"script": py_files[0].name}

        # 4. Check for shebang or __main__ block
        for py_file in py_files:
            try:
                content = py_file.read_text()
                if content.startswith("#!") or 'if __name__ == "__main__"' in content:
                    return {"script": py_file.name}
            except OSError:
                pass

    return None


def run_smoke_test(
    entrypoint_cmd: list[str], timeout: int = SMOKE_TIMEOUT
) -> tuple[bool, str, bool]:
    soft_pass_output = ""
    help_output = ""
    for arg in ("--help", "--version", "-h"):
        try:
            result = run_cmd(entrypoint_cmd + [arg], timeout=timeout)
            if result.returncode == 0:
                return True, result.stdout + result.stderr, False
            output = result.stdout + result.stderr
            if arg == "--help":
                help_output = output
            # Track soft pass candidate: nonzero but produced output without traceback
            if output and "Traceback" not in output:
                soft_pass_output = output
        except subprocess.TimeoutExpired:
            return False, "", False
        except FileNotFoundError:
            continue
    # If we got here, all args failed. Soft pass only if --help produced usage-like output.
    if soft_pass_output and _looks_like_usage(help_output):
        return True, soft_pass_output, True
    return False, "", False


def _looks_like_usage(text: str) -> bool:
    text_lower = text.lower()
    usage_indicators = (
        "usage:",
        "usage ",
        "options:",
        "options ",
        "--help",
        "-h",
        "--version",
        "usage",
    )
    return any(ind in text_lower for ind in usage_indicators)


def get_version(
    venv: Path,
    install_method: str,
    candidate_pip_package: str | None,
    repo_root: Path | None,
) -> str:
    if install_method == "pip-repo" and candidate_pip_package:
        pip = venv / "bin" / "pip"
        result = run_cmd([str(pip), "show", candidate_pip_package], timeout=30)
        for line in result.stdout.splitlines():
            if line.startswith("Version: "):
                return line.split("Version: ")[1].strip()
    if install_method == "git-requirements" and repo_root:
        result = run_cmd(["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"], timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    return "unknown"


def _find_requirements_txt(root: Path) -> Path | None:
    """Find requirements.txt at root or one level deep."""
    root_req = root / "requirements.txt"
    if root_req.exists():
        return root_req
    # Search one level deep
    for subdir in root.iterdir():
        if subdir.is_dir():
            sub_req = subdir / "requirements.txt"
            if sub_req.exists():
                return sub_req
    return None


def cleanup_sandbox(sandbox: Path) -> None:
    import shutil

    if sandbox.exists():
        shutil.rmtree(sandbox, ignore_errors=True)


def attempt_install(
    candidate: dict[str, Any], sandbox: Path
) -> tuple[bool, str, dict[str, Any] | None]:
    name = candidate["name"]
    repo = candidate["repo"]
    install_method = candidate["detected_install_method"]
    candidate_pip_package = candidate.get("candidate_pip_package")

    venv = create_venv(sandbox)
    venv_bin = venv / "bin"
    repo_root = None

    try:
        if install_method == "pip-repo":
            if candidate_pip_package:
                result = pip_install(venv, candidate_pip_package)
            else:
                result = pip_install(venv, f"git+https://github.com/{repo}.git")
            if result.returncode != 0:
                return False, f"pip install failed: {result.stderr[:200]}", None

        elif install_method == "git-requirements":
            repo_root = sandbox / "repo"
            result = git_clone(repo, repo_root)
            if result.returncode != 0:
                return False, f"git clone failed: {result.stderr[:200]}", None

            req_file = _find_requirements_txt(repo_root)
            if not req_file:
                return False, "requirements.txt not found at root or one level deep", None

            result = pip_install(venv, "-r", str(req_file))
            if result.returncode != 0:
                return False, f"requirements install failed: {result.stderr[:200]}", None

        else:
            return False, "no known install path", None

        entrypoint = detect_entrypoint(
            name, repo, venv_bin, install_method, candidate_pip_package, repo_root
        )
        if not entrypoint:
            return False, "no entrypoint detected", None

        if "command" in entrypoint:
            entrypoint_cmd = [str(venv_bin / entrypoint["command"])]
        else:
            script_path = repo_root / entrypoint["script"]
            entrypoint_cmd = [sys.executable, str(script_path)]

        smoke_ok, smoke_output, soft_pass = run_smoke_test(entrypoint_cmd)
        if not smoke_ok:
            return False, "smoke test failed", None

        version = get_version(venv, install_method, candidate_pip_package, repo_root)

        return (
            True,
            "passed" + (" (soft)" if soft_pass else ""),
            {
                "entrypoint": entrypoint,
                "version": version,
                "smoke_output": smoke_output[:500],
            },
        )

    except subprocess.TimeoutExpired:
        return False, "timeout", None
    except Exception as e:
        return False, f"error: {e}", None


def build_registry_entry(candidate: dict[str, Any], log_entry: dict[str, Any]) -> dict[str, Any]:
    name = candidate["name"]
    repo = candidate["repo"]
    install_method = candidate["detected_install_method"]
    candidate_pip_package = candidate.get("candidate_pip_package")
    version = log_entry["version"]

    display_name = repo.split("/")[-1].replace("-", " ").replace("_", " ").title()
    description = candidate["description"]
    # Strip emojis and trim to one sentence
    description = re.sub(r"[^\x00-\x7F]+", "", description).strip()
    description = description.split(".")[0].strip() + "."
    license_ = candidate.get("license", "unknown")
    stars = candidate.get("stars")

    entrypoint_command = log_entry.get("entrypoint_command")
    entrypoint_script = log_entry.get("entrypoint_script")

    if install_method == "pip-repo":
        install = {
            "method": "pip",
            "package": candidate_pip_package or name,
            "version": version,
        }
        if entrypoint_command:
            entrypoint_dict = {"command": entrypoint_command}
        else:
            entrypoint_dict = {"script": entrypoint_script}
    else:  # git-requirements
        install = {
            "method": "git",
            "url": f"https://github.com/{repo}.git",
            "requirements": "requirements.txt",
        }
        entrypoint_dict = {"script": entrypoint_script}

    # Get OS info
    os_info = "Linux"
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    os_info = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        pass

    python_version = sys.version.split()[0]

    return {
        "name": name,
        "display_name": display_name,
        "description": description,
        "repo": repo,
        "license": license_,
        "stars": stars,
        "tier": "community",
        "install": install,
        "entrypoint": entrypoint_dict,
        "smoke_args": ["--help"],
        "capabilities": [],
        "topics": [],
        "api_keys": {"required": [], "optional": []},
        "verified": {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "version": version,
            "os": os_info,
            "python": python_version,
        },
    }


def write_registry(entries: list[dict[str, Any]]) -> None:
    OUTPUT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = {"tools": entries}
    with OUTPUT_REGISTRY_PATH.open("w") as f:
        yaml.dump(content, f, sort_keys=False, allow_unicode=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify candidate tools")
    parser.add_argument("--limit", type=int, help="Limit number of candidates to test")
    parser.add_argument("--resume", action="store_true", help="Skip already tested candidates")
    args = parser.parse_args()

    candidates = load_candidates()

    tested = load_verification_log(LOG_PATH) if args.resume else set()

    if args.resume:
        print(f"Resuming: {len(tested)} candidates already tested")

    to_test = [c for c in candidates if c.get("likely_installable") and c["name"] not in tested]
    skipped_not_likely = [c for c in candidates if not c.get("likely_installable")]
    skipped_resumed = [c for c in candidates if c.get("likely_installable") and c["name"] in tested]

    print(f"Total candidates: {len(candidates)}")
    print(f"Skipped (not likely installable): {len(skipped_not_likely)}")
    if args.resume:
        print(f"Skipped (resumed): {len(skipped_resumed)}")
    print(f"To test: {len(to_test)}")

    if args.limit:
        to_test = to_test[: args.limit]
        print(f"Limited to first {args.limit}")

    stats = {
        "passed": 0,
        "failed": 0,
        "timeout": 0,
        "skipped_not_likely": len(skipped_not_likely),
        "skipped_resumed": len(skipped_resumed),
    }
    failure_reasons = {}
    registry_entries = []

    for i, candidate in enumerate(to_test, 1):
        name = candidate["name"]
        print(f"[{i}/{len(to_test)}] Testing {name}...")

        sandbox = Path(tempfile.mkdtemp(prefix=f"otverify-{name}-"))
        try:
            success, reason, details = attempt_install(candidate, sandbox)

            if success:
                outcome = "passed"
            elif reason == "timeout":
                outcome = "timeout"
            else:
                outcome = "failed"

            log_data = {
                "name": name,
                "repo": candidate["repo"],
                "outcome": outcome,
                "reason": reason if not success else None,
                "tested_at": datetime.now(timezone.utc).isoformat(),
            }

            if success:
                log_data["entrypoint_command"] = details["entrypoint"].get("command")
                log_data["entrypoint_script"] = details["entrypoint"].get("script")
                log_data["version"] = details["version"]
                log_data["smoke_output"] = details["smoke_output"]
                stats["passed"] += 1
                # Build registry entry and validate
                try:
                    registry_entry = build_registry_entry(candidate, log_data)
                    parse_tool(registry_entry)  # Validate
                    registry_entries.append(registry_entry)
                except RegistryError as e:
                    print(f"  WARNING: registry validation failed for {name}: {e}")
                    # Don't add to registry_entries, but keep the passed log
            else:
                if reason == "timeout":
                    stats["timeout"] += 1
                else:
                    stats["failed"] += 1
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

            append_log_entry(LOG_PATH, log_data)
            print(f"  {log_data['outcome']}: {reason}")

        finally:
            cleanup_sandbox(sandbox)

    if registry_entries:
        write_registry(registry_entries)

    # Also generate registry from full log (for resumed runs)
    all_passed = []
    if LOG_PATH.exists():
        with LOG_PATH.open() as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("outcome") == "passed":
                        all_passed.append(entry)
                except json.JSONDecodeError as e:
                    print(f"  WARNING: malformed JSON line {i} in {LOG_PATH}: {e}")
                    continue

    # Build registry entries for all passed tools from log
    candidates_by_name = {c["name"]: c for c in candidates}
    full_registry_entries = []
    for log_entry in all_passed:
        name = log_entry["name"]
        candidate = candidates_by_name.get(name)
        if not candidate:
            continue
        try:
            registry_entry = build_registry_entry(candidate, log_entry)
            parse_tool(registry_entry)
            full_registry_entries.append(registry_entry)
        except RegistryError as e:
            print(f"  WARNING: registry validation failed for {name} (from log): {e}")

    if full_registry_entries:
        write_registry(full_registry_entries)

    print("\n=== Verification Summary ===")
    print(f"Total candidates: {len(candidates)}")
    print(f"Tested: {len(to_test)}")
    print(f"Passed: {stats['passed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Timeout: {stats['timeout']}")
    print(f"Skipped (not likely installable): {stats['skipped_not_likely']}")
    if args.resume:
        print(f"Skipped (resumed): {stats['skipped_resumed']}")
    print(f"Registry entries written: {len(registry_entries)}")

    if failure_reasons:
        print("Failure breakdown:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
