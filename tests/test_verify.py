"""Tests for the verification pipeline."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from otinstaller.registry import RegistryError, parse_tool
from pipeline.verify import (
    _get_console_scripts_from_entry_points,
    build_registry_entry,
    cleanup_sandbox,
    detect_entrypoint,
    load_verification_log,
    run_smoke_test,
)


class TestDetectEntrypoint:
    def test_exact_match(self):
        """Test exact match of console script to candidate name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "sherlock").write_text("#!/bin/sh\necho test")
            (venv_bin / "sherlock").chmod(0o755)

            result = detect_entrypoint(
                "sherlock", "sherlock-project/sherlock", venv_bin, "pip-repo", None
            )
            assert result == {"command": "sherlock"}

    def test_fuzzy_match_underscore_hyphen(self):
        """Test fuzzy match with underscore/hyphen swap."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "theharvester").write_text("#!/bin/sh\necho test")
            (venv_bin / "theharvester").chmod(0o755)

            result = detect_entrypoint(
                "theharvester", "laramies/theHarvester", venv_bin, "pip-repo", "theharvester"
            )
            assert result == {"command": "theharvester"}

    def test_fuzzy_match_repo_name(self):
        """Test fuzzy match using repo name when candidate name doesn't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "maigret").write_text("#!/bin/sh\necho test")
            (venv_bin / "maigret").chmod(0o755)

            result = detect_entrypoint("maigret", "soxoj/maigret", venv_bin, "pip-repo", "maigret")
            assert result == {"command": "maigret"}

    def test_script_fallback_git_requirements(self):
        """Test script fallback for git-requirements installs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            (repo_root / "spiderfoot.py").write_text("#!/usr/bin/env python3\nprint('test')")

            result = detect_entrypoint(
                "spiderfoot", "smicallef/spiderfoot", venv_bin, "git-requirements", None, repo_root
            )
            assert result == {"script": "spiderfoot.py"}

    def test_no_match_found(self):
        """Test no entrypoint detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "venv" / "bin"
            venv_bin.mkdir(parents=True)

            result = detect_entrypoint("unknown", "org/unknown", venv_bin, "pip-repo", None)
            assert result is None

    def test_entrypoint_from_entry_points_txt(self):
        """Test entrypoint detection via entry_points.txt when script
        name differs from candidate name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / "venv"
            venv_bin = venv / "bin"
            venv_bin.mkdir(parents=True)
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv / "lib" / pyver / "site-packages"
            dist_info = site_packages / "sherlock_project-0.16.2.dist-info"
            dist_info.mkdir(parents=True)
            (dist_info / "entry_points.txt").write_text(
                "[console_scripts]\nsherlock = sherlock_project.__main__:main\n"
            )

            # Create the actual binary in venv/bin (as pip would)
            (venv_bin / "sherlock").write_text("#!/bin/sh\necho test")
            (venv_bin / "sherlock").chmod(0o755)

            # Candidate name is "sherlock" but package is "sherlock-project"
            result = detect_entrypoint(
                "sherlock", "sherlock-project/sherlock", venv_bin, "pip-repo", "sherlock-project"
            )
            assert result == {"command": "sherlock"}

    def test_entrypoint_from_entry_points_txt_different_name(self):
        """Test entrypoint detection when console script name differs from candidate name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / "venv"
            venv_bin = venv / "bin"
            venv_bin.mkdir(parents=True)
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv / "lib" / pyver / "site-packages"
            dist_info = site_packages / "my_package-1.0.dist-info"
            dist_info.mkdir(parents=True)
            # Console script name is "actual-command" but candidate name is "mytool"
            (dist_info / "entry_points.txt").write_text(
                "[console_scripts]\nactual-command = my_package:main\n"
            )

            (venv_bin / "actual-command").write_text("#!/bin/sh\necho test")
            (venv_bin / "actual-command").chmod(0o755)

            result = detect_entrypoint("mytool", "org/mytool", venv_bin, "pip-repo", "my-package")
            assert result == {"command": "actual-command"}

    def test_get_console_scripts_from_entry_points(self):
        """Test _get_console_scripts_from_entry_points function directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / "venv"
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv / "lib" / pyver / "site-packages"
            dist_info = site_packages / "test_pkg-1.0.dist-info"
            dist_info.mkdir(parents=True)
            (dist_info / "entry_points.txt").write_text(
                "[console_scripts]\ncmd1 = test_pkg:main\ncmd2 = test_pkg:other\n"
            )

            scripts = _get_console_scripts_from_entry_points(venv, "test-pkg")
            assert "cmd1" in scripts
            assert "cmd2" in scripts
            assert len(scripts) == 2

    def test_get_console_scripts_from_entry_points_missing(self):
        """Test _get_console_scripts_from_entry_points with missing dist-info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / "venv"
            scripts = _get_console_scripts_from_entry_points(venv, "nonexistent")
            assert scripts == []


class TestRunSmokeTest:
    def test_normal_zero_exit(self):
        """Test smoke test with normal zero exit."""
        with patch("pipeline.verify.run_cmd") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["test", "--help"], returncode=0, stdout="usage: test\n", stderr=""
            )
            success, output, soft_pass = run_smoke_test(["test", "--help"], timeout=30)
            assert success is True
            assert soft_pass is False

    def test_help_fails_version_succeeds(self):
        """Test --help fails but --version succeeds."""
        with patch("pipeline.verify.run_cmd") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["test", "--help"], returncode=1, stdout="", stderr="error"
                ),
                subprocess.CompletedProcess(
                    args=["test", "--version"], returncode=0, stdout="1.0.0\n", stderr=""
                ),
            ]
            success, output, soft_pass = run_smoke_test(["test", "--help"], timeout=30)
            assert success is True
            assert soft_pass is False

    def test_all_three_fail(self):
        """Test --help, --version, -h all fail with error output (not usage)."""
        with patch("pipeline.verify.run_cmd") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["test", "--help"], returncode=1, stdout="", stderr="error: not found"
            )
            success, output, soft_pass = run_smoke_test(["test", "--help"], timeout=30)
            assert success is False

    def test_soft_pass_nonzero_but_usage_output(self):
        """Test soft pass: --help fails but produces usage-like output."""
        with patch("pipeline.verify.run_cmd") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["test", "--help"],
                    returncode=1,
                    stdout="usage: test [options]\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["test", "--version"], returncode=1, stdout="", stderr="error"
                ),
                subprocess.CompletedProcess(
                    args=["test", "-h"], returncode=1, stdout="", stderr="error"
                ),
            ]
            success, output, soft_pass = run_smoke_test(["test", "--help"], timeout=30)
            assert success is True
            assert soft_pass is True

    def test_soft_pass_with_traceback(self):
        """Test that traceback is not treated as soft pass."""
        with patch("pipeline.verify.run_cmd") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["test", "--help"],
                returncode=1,
                stdout="",
                stderr="Traceback (most recent call last):\n  File ...",
            )
            success, output, soft_pass = run_smoke_test(["test", "--help"], timeout=30)
            assert success is False


class TestBuildRegistryEntry:
    def test_passed_entry_parses(self):
        """Test that a passed entry produces a valid Tool."""
        log_entry = {
            "name": "sherlock",
            "repo": "sherlock-project/sherlock",
            "outcome": "passed",
            "entrypoint_command": "sherlock",
            "version": "0.14.3",
            "tested_at": "2026-09-24T12:00:00Z",
        }
        candidate = {
            "name": "sherlock",
            "repo": "sherlock-project/sherlock",
            "stars": 92545,
            "description": "Hunt down social media accounts by username across social networks",
            "license": "MIT",
            "detected_install_method": "pip-repo",
            "candidate_pip_package": "sherlock-project",
            "default_branch": "master",
        }
        tool = build_registry_entry(candidate, log_entry)
        # Should not raise
        parsed = parse_tool(tool)
        assert parsed.name == "sherlock"
        assert parsed.install.method == "pip"
        assert parsed.install.package == "sherlock-project"
        assert parsed.entrypoint.command == "sherlock"
        assert parsed.verified is not None
        assert parsed.verified.version == "0.14.3"

    def test_git_requirements_entry_parses(self):
        """Test git-requirements entry produces valid Tool with script entrypoint."""
        log_entry = {
            "name": "spiderfoot",
            "repo": "smicallef/spiderfoot",
            "outcome": "passed",
            "entrypoint_script": "sf.py",
            "version": "abc123",
            "tested_at": "2026-09-24T12:00:00Z",
        }
        candidate = {
            "name": "spiderfoot",
            "repo": "smicallef/spiderfoot",
            "stars": 22469,
            "description": "SpiderFoot automates OSINT for threat intelligence.",
            "license": "MIT",
            "detected_install_method": "git-requirements",
            "candidate_pip_package": None,
            "default_branch": "master",
        }
        tool = build_registry_entry(candidate, log_entry)
        parsed = parse_tool(tool)
        assert parsed.install.method == "git"
        assert parsed.install.url == "https://github.com/smicallef/spiderfoot.git"
        assert parsed.install.requirements == "requirements.txt"
        assert parsed.entrypoint.script == "sf.py"

    def test_invalid_entrypoint_caught(self):
        """Test that invalid entrypoint data is caught and logged as failure."""
        log_entry = {
            "name": "badtool",
            "repo": "org/badtool",
            "outcome": "passed",
            "entrypoint_command": "bad!command",  # Invalid characters
            "version": "1.0",
            "tested_at": "2026-09-24T12:00:00Z",
        }
        candidate = {
            "name": "badtool",
            "repo": "org/badtool",
            "stars": 100,
            "description": "Bad tool",
            "license": "MIT",
            "detected_install_method": "pip-repo",
            "candidate_pip_package": "badtool",
            "default_branch": "main",
        }
        tool_dict = build_registry_entry(candidate, log_entry)
        with pytest.raises(RegistryError):
            parse_tool(tool_dict)


class TestLoadVerificationLog:
    def test_resume_skips_existing(self):
        """Test that candidates already in log are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"name": "sherlock", "outcome": "passed"}) + "\n")
            f.write(json.dumps({"name": "maigret", "outcome": "failed"}) + "\n")
            log_path = Path(f.name)

        try:
            tested = load_verification_log(log_path)
            assert "sherlock" in tested
            assert "maigret" in tested
            assert len(tested) == 2
        finally:
            log_path.unlink()

    def test_malformed_log_line_warning(self, capsys):
        """Test that malformed JSON lines are warned and skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"name": "valid", "outcome": "passed"}\n')
            f.write("not valid json\n")
            f.write('{"name": "valid2", "outcome": "passed"}\n')
            log_path = Path(f.name)

        try:
            tested = load_verification_log(log_path)
            assert tested == {"valid", "valid2"}
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "malformed" in captured.out.lower()
        finally:
            log_path.unlink()


class TestFindRequirementsTxt:
    def test_find_at_root(self):
        """Test finding requirements.txt at repo root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            (repo / "requirements.txt").write_text("requests\n")

            from pipeline.verify import _find_requirements_txt

            found = _find_requirements_txt(repo)
            assert found == repo / "requirements.txt"

    def test_find_one_level_deep(self):
        """Test finding requirements.txt one level deep."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            subdir = repo / "subdir"
            subdir.mkdir()
            (subdir / "requirements.txt").write_text("requests\n")

            from pipeline.verify import _find_requirements_txt

            found = _find_requirements_txt(repo)
            assert found == subdir / "requirements.txt"

    def test_find_first_match(self):
        """Test that first found match is returned (root preferred)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            (repo / "requirements.txt").write_text("root\n")
            subdir = repo / "subdir"
            subdir.mkdir()
            (subdir / "requirements.txt").write_text("sub\n")

            from pipeline.verify import _find_requirements_txt

            found = _find_requirements_txt(repo)
            assert found == repo / "requirements.txt"

    def test_not_found(self):
        """Test None returned when no requirements.txt exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()

            from pipeline.verify import _find_requirements_txt

            found = _find_requirements_txt(repo)
            assert found is None


class TestCleanupSandbox:
    def test_cleanup_after_pass(self):
        """Test temp directory is removed after pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = Path(tmpdir) / "sandbox"
            sandbox.mkdir()
            (sandbox / "venv" / "bin").mkdir(parents=True)
            (sandbox / "venv" / "bin" / "tool").write_text("#!/bin/sh")

            cleanup_sandbox(sandbox)
            assert not sandbox.exists()

    def test_cleanup_after_fail(self):
        """Test temp directory is removed after failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = Path(tmpdir) / "sandbox"
            sandbox.mkdir()
            (sandbox / "venv").mkdir()

            cleanup_sandbox(sandbox)
            assert not sandbox.exists()
