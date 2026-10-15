"""Init command tests."""

from typer.testing import CliRunner

from otinstaller.cli import app

runner = CliRunner()


def test_init_creates_directories_and_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0
    assert (tmp_path / "tools").exists()
    assert (tmp_path / "logs").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "accepted.json").exists()


def test_init_runs_twice(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0


def test_init_fixes_env_permissions(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    # Create env file with loose permissions
    env = tmp_path / ".env"
    env.write_text("KEY=value\n")
    env.chmod(0o644)
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0
    assert "fixed permissions" in result.output


def test_init_refuses_without_yes_when_not_tty(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    result = runner.invoke(app, ["init"], input="")
    assert result.exit_code == 1
    assert "confirmation needed" in result.output


def test_init_accepts_with_yes(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0


def test_init_env_contents_not_printed(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    result = runner.invoke(app, ["init", "--yes"])
    assert "API keys" not in result.output  # contents not printed
    env = tmp_path / ".env"
    content = env.read_text()
    assert "# API keys for tools managed by otinstaller." in content
    assert "# Add one KEY=value per line. Keep this file private." in content


class _Tty:
    def isatty(self):
        return True


def _fake_terminal(monkeypatch):
    import otinstaller.cli as cli

    monkeypatch.setattr(cli.sys, "stdin", _Tty())
    monkeypatch.setattr(cli.sys, "stdout", _Tty())
    monkeypatch.setattr(
        cli, "_make_console", lambda no_color: type("C", (), {"print": lambda *a: None})()
    )


def test_install_on_terminal_offers_the_notice(monkeypatch, tmp_path):
    """A new user can run install first: on a terminal it shows the notice and asks."""
    import otinstaller.cli as cli
    from otinstaller.notice import has_accepted

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    _fake_terminal(monkeypatch)
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: "y")

    cli._require_notice()

    assert has_accepted()
    env = tmp_path / ".env"
    assert env.exists()
    assert env.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "tools").exists()


def test_install_on_terminal_declined_notice_exits(monkeypatch, tmp_path):
    import pytest
    import typer

    import otinstaller.cli as cli
    from otinstaller.notice import has_accepted

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    _fake_terminal(monkeypatch)
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: "n")

    with pytest.raises(typer.Exit) as exc:
        cli._require_notice()
    assert exc.value.exit_code == 1
    assert not has_accepted()


def test_install_without_terminal_never_accepts_notice(monkeypatch, tmp_path):
    """Scripts and pipes get an error with the fix, and are never asked or auto-accepted."""
    import otinstaller.cli as cli
    from otinstaller.notice import has_accepted

    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))

    def no_prompt(*a, **k):
        raise AssertionError("must not prompt without a terminal")

    monkeypatch.setattr(cli.typer, "prompt", no_prompt)
    result = runner.invoke(app, ["install", "sherlock", "--yes"])
    assert result.exit_code == 1
    assert "otinstaller init --yes" in result.output
    assert not has_accepted()
