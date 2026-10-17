"""Opt-in crash reports."""

import json

import pytest
from typer.testing import CliRunner

from otinstaller import crash_reports
from otinstaller.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    monkeypatch.setenv("OTINSTALLER_HOME", str(tmp_path))
    for var in ("DO_NOT_TRACK", "OTINSTALLER_CRASH_REPORTS", "OTINSTALLER_SENTRY_DSN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(crash_reports, "_ready", False)


def test_off_until_the_user_says_yes():
    assert not crash_reports.is_enabled()
    assert not crash_reports.was_asked()
    crash_reports.set_enabled(True)
    assert crash_reports.is_enabled()
    crash_reports.set_enabled(False)
    assert not crash_reports.is_enabled()
    assert crash_reports.was_asked()


def test_do_not_track_and_env_override(monkeypatch):
    crash_reports.set_enabled(True)
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert not crash_reports.is_enabled()
    monkeypatch.delenv("DO_NOT_TRACK")
    monkeypatch.setenv("OTINSTALLER_CRASH_REPORTS", "off")
    assert not crash_reports.is_enabled()


def test_ask_defaults_to_no_and_asks_once():
    asked = []
    crash_reports.ask(lambda *a: None, lambda *a, **k: asked.append(1) or "")
    assert not crash_reports.is_enabled()
    crash_reports.ask(lambda *a: None, lambda *a, **k: asked.append(1) or "y")
    assert len(asked) == 1


def test_nothing_is_set_up_without_opt_in_or_dsn(monkeypatch):
    monkeypatch.setattr(crash_reports, "SENTRY_DSN", "https://k@o1.ingest.sentry.io/1")
    assert crash_reports.setup() is False  # not opted in
    crash_reports.set_enabled(True)
    monkeypatch.setattr(crash_reports, "SENTRY_DSN", "")
    assert crash_reports.setup() is False  # no DSN


def test_scrub_text_removes_targets_and_paths():
    msg = (
        "failed for john.doe@example.com at https://site.example/x?a=1 from 10.0.0.1 "
        "in /home/alice/.otinstaller/tools/x/run.py on example.org call +1 555 010 0199 "
        "value 'johndoe123'"
    )
    out = crash_reports.scrub_text(msg)
    for leaked in (
        "john.doe",
        "example.com",
        "site.example",
        "10.0.0.1",
        "alice",
        "example.org",
        "555",
        "johndoe123",
    ):
        assert leaked not in out, leaked
    assert out.startswith("failed for <email>")


def test_scrub_event_keeps_only_the_allow_list():
    event = {
        "level": "error",
        "release": "otinstaller@0.1.0",
        "server_name": "alice-laptop",
        "user": {"username": "alice"},
        "extra": {"sys.argv": ["ot", "run", "sherlock", "--", "u:johndoe"]},
        "breadcrumbs": {"values": [{"message": "secret"}]},
        "tags": {"command": "run", "target": "johndoe"},
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "bad input 'johndoe'",
                    "stacktrace": {
                        "frames": [
                            {
                                "abs_path": "/home/alice/venv/lib/python3.12/site-packages/"
                                "otinstaller/cli.py",
                                "function": "run",
                                "lineno": 10,
                                "vars": {"target": "johndoe"},
                                "context_line": "x = target",
                            }
                        ]
                    },
                }
            ]
        },
    }
    clean = crash_reports.scrub_event(event)
    text = json.dumps(clean)
    for leaked in ("alice", "johndoe", "secret", "sys.argv", "context_line", "vars"):
        assert leaked not in text, leaked
    frame = clean["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert frame["filename"] == "otinstaller/cli.py"
    assert clean["tags"] == {"command": "run"}
    assert crash_reports.scrub_event({"message": "hello"}) is None


def test_report_sends_a_scrubbed_event(monkeypatch):
    """End to end through sentry-sdk with a fake transport."""
    import sentry_sdk
    from sentry_sdk.transport import Transport

    sent = []

    class Capture(Transport):
        def capture_envelope(self, envelope):
            sent.append(envelope)

        def flush(self, timeout, callback=None):
            return None

    real_init = sentry_sdk.init
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: real_init(transport=Capture(), **kw))
    monkeypatch.setenv("OTINSTALLER_SENTRY_DSN", "https://key@o1.ingest.sentry.io/1")
    crash_reports.set_enabled(True)
    try:
        raise RuntimeError("could not open /home/alice/results/johndoe.txt for a@b.co")
    except RuntimeError as exc:
        crash_reports.report(exc, "run")
    try:
        assert sent, "no event was sent"
        body = "".join(
            json.dumps(item.payload.json)
            if item.payload.json is not None
            else (item.payload.bytes or b"").decode()
            for e in sent
            for item in e.items
        )
        assert "RuntimeError" in body
        for leaked in ("alice", "johndoe", "a@b.co"):
            assert leaked not in body, leaked
    finally:
        sentry_sdk.get_client().close()


def test_scrub_event_leaves_out_empty_stack_traces():
    """An exception that was never raised has no frames; Sentry rejects "frames": []."""
    event = {
        "event_id": "a" * 32,
        "exception": {"values": [{"type": "RuntimeError", "value": "x", "module": None}]},
    }
    value = crash_reports.scrub_event(event)["exception"]["values"][0]
    assert "stacktrace" not in value
    assert "module" not in value
    assert value["type"] == "RuntimeError"


@pytest.mark.parametrize(
    "path,expected",
    [
        ("otinstaller/cli.py", "otinstaller/cli.py"),
        ("/home/alice/.local/lib/python3.12/site-packages/otinstaller/a.py", "otinstaller/a.py"),
        ("/home/alice/work/run.py", "run.py"),
        ("../../home/alice/x.py", "x.py"),
        ("C:\\Users\\alice\\x.py", "x.py"),
    ],
)
def test_frame_paths_never_keep_the_user_folder(path, expected):
    got = crash_reports._frame_path(path)
    assert got == expected
    assert "alice" not in got


def test_crash_reports_test_sends_a_stack_trace(monkeypatch):
    """The test report is raised and caught, so Sentry gets a real stack trace."""
    got = []
    monkeypatch.setattr(crash_reports, "report", lambda exc, cmd=None: got.append(exc))
    crash_reports.set_enabled(True)
    result = runner.invoke(app, ["crash-reports", "test"])
    assert result.exit_code == 0
    assert got and got[0].__traceback__ is not None


def test_main_reports_crashes_but_not_normal_exits(monkeypatch):
    import otinstaller.cli as cli

    reported = []
    monkeypatch.setattr(crash_reports, "report", lambda exc, cmd=None: reported.append(cmd))

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "app", boom)
    with pytest.raises(RuntimeError):
        cli.run_cli()
    assert len(reported) == 1

    def normal_exit():
        raise SystemExit(0)

    monkeypatch.setattr(cli, "app", normal_exit)
    with pytest.raises(SystemExit):
        cli.run_cli()
    assert len(reported) == 1


def test_command_name_never_returns_arguments():
    assert crash_reports.command_name(["ot", "--no-color", "install", "sherlock"]) == "install"
    assert crash_reports.command_name(["ot", "u:johndoe"]) is None


def test_crash_reports_command():
    result = runner.invoke(app, ["crash-reports"])
    assert result.exit_code == 0
    assert "crash reports off" in result.output
    result = runner.invoke(app, ["crash-reports", "on"])
    assert "crash reports on" in result.output
    assert crash_reports.is_enabled()
    result = runner.invoke(app, ["crash-reports", "off", "--json"])
    assert json.loads(result.output) == {"enabled": False, "status": "off"}
    assert runner.invoke(app, ["crash-reports", "maybe"]).exit_code == 2


def test_init_with_yes_never_turns_crash_reports_on():
    result = runner.invoke(app, ["init", "--yes"])
    assert result.exit_code == 0
    assert not crash_reports.was_asked()
    assert not crash_reports.is_enabled()


def test_crash_reports_test_command(monkeypatch):
    sent = []
    monkeypatch.setattr(crash_reports, "report", lambda exc, cmd=None: sent.append(str(exc)))
    assert runner.invoke(app, ["crash-reports", "test"]).exit_code == 1  # off
    assert not sent
    crash_reports.set_enabled(True)
    result = runner.invoke(app, ["crash-reports", "test"])
    assert result.exit_code == 0
    assert sent and "test report" in sent[0]
