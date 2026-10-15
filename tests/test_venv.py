"""Venv tests."""

from otinstaller.installer.venv import create_venv, venv_bin, venv_python


def test_create_venv(monkeypatch, tmp_path):
    log = tmp_path / "test.log"
    venv_path = tmp_path / "venv"
    create_venv(venv_path, log, upgrade_pip=False)
    python = venv_path / "bin" / "python"
    assert python.exists()


def test_create_venv_upgrades_pip(monkeypatch, tmp_path):
    """Old bundled pips install setup.py-only packages with broken '#!python' scripts."""
    import otinstaller.installer.venv as venv_mod

    calls = []
    monkeypatch.setattr(venv_mod, "run", lambda args, **kw: calls.append(args))
    create_venv(tmp_path / "venv", tmp_path / "log")
    assert calls[0][1:3] == ["-m", "venv"]
    assert calls[1][-4:] == ["pip", "install", "--upgrade", "pip"]


def test_create_venv_keeps_going_if_pip_upgrade_fails(monkeypatch, tmp_path):
    import otinstaller.installer.venv as venv_mod

    def fake_run(args, **kw):
        if "--upgrade" in args:
            raise RuntimeError("no network")

    monkeypatch.setattr(venv_mod, "run", fake_run)
    log = tmp_path / "log"
    create_venv(tmp_path / "venv", log)
    assert "could not upgrade pip" in log.read_text()


def test_venv_python(monkeypatch, tmp_path):
    root = tmp_path / "tool"
    venv_dir = root / "venv"
    venv_dir.mkdir(parents=True)
    (venv_dir / "bin").mkdir()
    (venv_dir / "bin" / "python").write_text("#!/bin/sh\necho test")
    (venv_dir / "bin" / "python").chmod(0o755)
    assert venv_python(root) == venv_dir / "bin" / "python"


def test_venv_bin(monkeypatch, tmp_path):
    root = tmp_path / "tool"
    venv_dir = root / "venv"
    venv_dir.mkdir(parents=True)
    (venv_dir / "bin").mkdir()
    (venv_dir / "bin" / "myscript").write_text("#!/bin/sh\necho test")
    (venv_dir / "bin" / "myscript").chmod(0o755)
    assert venv_bin(root, "myscript") == venv_dir / "bin" / "myscript"
