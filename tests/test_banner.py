import io

from rich.console import Console
from typer.testing import CliRunner

from otinstaller import banner
from otinstaller.cli import app


def _render(width: int, color: bool = True) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=width, force_terminal=color, color_system="truecolor")
    banner.render_banner(console, color=color)
    return buf.getvalue()


def test_wide_terminal_gets_big_art():
    assert banner.pick_art(120) is banner.WIDE_ART


def test_medium_terminal_gets_narrow_art():
    assert banner.pick_art(70) is banner.NARROW_ART


def test_tiny_terminal_gets_no_art():
    assert banner.pick_art(30) is None
    assert "OTinstaller" in _render(30, color=False)


def test_banner_lines_fit_terminal_width():
    for width in (40, 60, 80, 100, 140):
        for line in _render(width, color=False).splitlines():
            assert len(line) <= width


def test_no_color_has_no_ansi_codes():
    assert "\x1b[" not in _render(120, color=False)


def test_no_color_env_disables_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\x1b[38" not in _render(120)


def test_banner_disabled_for_json(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert banner.banner_enabled(json_output=True) is False


def test_banner_disabled_by_env(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setenv("OTINSTALLER_NO_BANNER", "1")
    assert banner.banner_enabled() is False


def test_banner_hidden_when_not_a_tty():
    result = CliRunner().invoke(app, ["about"])
    assert result.exit_code == 0
    assert "██" not in result.output


def test_bare_invocation_shows_help():
    result = CliRunner().invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output
