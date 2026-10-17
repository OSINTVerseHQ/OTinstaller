"""Opt-in crash reports, sent to Sentry only when the user has said yes.

Nothing is sent unless all of these hold:
- the user answered yes when asked (or ran `otinstaller crash-reports on`),
- DO_NOT_TRACK is not set and OTINSTALLER_CRASH_REPORTS is not "off",
- a Sentry DSN is configured (SENTRY_DSN below, or OTINSTALLER_SENTRY_DSN),
- sentry-sdk can be imported.

Only crashes of otinstaller itself are reported, never a tool's own failure. A report
holds the exception type, a cleaned message, where in otinstaller's code it happened,
and the otinstaller, Python and OS versions. It never holds targets, command arguments,
tool output, results, API keys, file paths, the host name or the user name.
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import re
import sys
from pathlib import Path

from otinstaller.config import get_home

# The maintainers' Sentry project. Empty means crash reports are never sent.
SENTRY_DSN = "https://2603ace50faa78d2a81521294feda773@o4512260870176768.ingest.us.sentry.io/4512261029953536"

_ON = {"1", "on", "true", "yes"}
_OFF = {"0", "off", "false", "no"}

PROMPT_TEXT = """CRASH REPORTS
If otinstaller itself crashes, it can send a short report so we can fix it.
A report has the error, where in otinstaller's code it happened, and the
otinstaller, Python and OS versions. It never includes your targets, command
arguments, tool output, results, API keys, file paths or user name.
Change this any time: otinstaller crash-reports on / off"""


def _settings_path() -> Path:
    return get_home() / "crash_reports.json"


def _read() -> dict:
    try:
        return json.loads(_settings_path().read_text())
    except (OSError, ValueError):
        return {}


def was_asked() -> bool:
    """True once the user has answered (or set it with the command)."""
    return "enabled" in _read()


def set_enabled(enabled: bool) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "enabled": bool(enabled),
        "changed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data))
    os.chmod(path, 0o600)


def status() -> tuple[bool, str]:
    """(enabled, reason) after environment overrides."""
    dnt = os.environ.get("DO_NOT_TRACK", "").strip().lower()
    if dnt and dnt not in _OFF:
        return False, "off (DO_NOT_TRACK is set)"
    env = os.environ.get("OTINSTALLER_CRASH_REPORTS", "").strip().lower()
    if env in _OFF:
        return False, "off (OTINSTALLER_CRASH_REPORTS)"
    if env in _ON:
        return True, "on (OTINSTALLER_CRASH_REPORTS)"
    if _read().get("enabled") is True:
        return True, "on"
    return False, "off"


def is_enabled() -> bool:
    return status()[0]


def dsn() -> str:
    return os.environ.get("OTINSTALLER_SENTRY_DSN", "").strip() or SENTRY_DSN


def ask(print_fn, prompt_fn) -> None:
    """Ask once, default no. Callers only call this on a terminal."""
    if was_asked():
        return
    print_fn(PROMPT_TEXT)
    answer = prompt_fn("Send crash reports? [y/N]", default="n", show_default=False)
    set_enabled(str(answer).strip().lower() == "y")


# --- scrubbing ---------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_IPV4 = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")
_IPV6 = re.compile(r"\b[0-9a-f]{0,4}(:[0-9a-f]{0,4}){2,7}\b", re.IGNORECASE)
_PHONE = re.compile(r"\+?\d[\d ().-]{6,}\d")
_PATH = re.compile(r"(~|\.{0,2})?/[^\s'\"]+")
_DOMAIN = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?!py\b|pyc\b|yaml\b|yml\b|json\b|txt\b|log\b|toml\b|db\b|cfg\b)[a-z]{2,24}\b",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"(['\"])(?:(?!\1).){1,200}\1")


def scrub_text(text: str) -> str:
    """Remove anything that could be a target, a credential or a path."""
    if not text:
        return text
    text = _URL.sub("<url>", text)
    text = _EMAIL.sub("<email>", text)
    text = _PATH.sub("<path>", text)
    text = _IPV4.sub("<ip>", text)
    text = _IPV6.sub("<ip>", text)
    text = _PHONE.sub("<number>", text)
    text = _DOMAIN.sub("<domain>", text)
    text = _QUOTED.sub("'<value>'", text)
    return text[:500]


def _frame_path(path: str | None) -> str | None:
    """Keep only the part of a source path inside a package (otinstaller/cli.py)."""
    if not path:
        return path
    # sentry-sdk already gives a path relative to the package (otinstaller/cli.py)
    if not path.startswith(("/", "~", "\\")) and ":" not in path and ".." not in path:
        return path
    parts = [p for p in re.split(r"[\\/]", path) if p]
    for marker in ("site-packages", "dist-packages", "src"):
        if marker in parts:
            return "/".join(parts[parts.index(marker) + 1 :])
    return parts[-1] if parts else None


def scrub_event(event: dict, hint: dict | None = None) -> dict | None:
    """Rebuild the event from an allow-list: anything not listed here is dropped."""
    clean: dict = {
        "event_id": event.get("event_id"),
        "timestamp": event.get("timestamp"),
        "sdk": event.get("sdk"),
        "level": event.get("level", "error"),
        "platform": "python",
        "release": event.get("release"),
        "environment": event.get("environment"),
        "tags": {k: v for k, v in (event.get("tags") or {}).items() if k == "command"},
        "contexts": {
            "os": {"name": platform.system(), "version": platform.release()},
            "runtime": {"name": "CPython", "version": platform.python_version()},
        },
    }
    values = []
    for exc in (event.get("exception") or {}).get("values") or []:
        frames = []
        for fr in (exc.get("stacktrace") or {}).get("frames") or []:
            frame = {
                "filename": _frame_path(fr.get("filename") or fr.get("abs_path")),
                "module": fr.get("module"),
                "function": fr.get("function"),
                "lineno": fr.get("lineno"),
                "in_app": fr.get("in_app"),
            }
            frames.append({k: v for k, v in frame.items() if v is not None})
        value = {
            "type": exc.get("type"),
            "module": exc.get("module"),
            "value": scrub_text(exc.get("value") or ""),
        }
        value = {k: v for k, v in value.items() if v is not None}
        # Sentry rejects an empty frame list ("processing error"), so leave it out
        if frames:
            value["stacktrace"] = {"frames": frames}
        values.append(value)
    if not values:
        return None  # only exceptions are ever sent
    clean["exception"] = {"values": values}
    return clean


# --- sending -----------------------------------------------------------------

_ready = False


def setup() -> bool:
    """Start Sentry if the user opted in and a DSN is set. Never raises."""
    global _ready
    if _ready:
        return True
    if not is_enabled() or not dsn():
        return False
    try:
        import sentry_sdk

        from otinstaller import __version__

        sentry_sdk.init(
            dsn=dsn(),
            release=f"otinstaller@{__version__}",
            environment="production",
            include_local_variables=False,
            include_source_context=False,
            max_breadcrumbs=0,
            traces_sample_rate=0,
            default_integrations=False,
            auto_enabling_integrations=False,
            server_name="",
            before_send=scrub_event,
        )
    except Exception:
        return False
    _ready = True
    return True


def report(exc: BaseException, command: str | None = None) -> None:
    """Send one crash report if crash reports are on. Never raises."""
    if not setup():
        return
    try:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            if command:
                scope.set_tag("command", command)
            sentry_sdk.capture_exception(exc)
        sentry_sdk.flush(timeout=2)
    except Exception:
        pass


def command_name(argv: list[str] | None = None) -> str | None:
    """The otinstaller subcommand being run (never its arguments)."""
    argv = sys.argv if argv is None else argv
    for arg in argv[1:]:
        if not arg.startswith("-"):
            return arg if re.fullmatch(r"[a-z][a-z-]{0,20}", arg) else None
    return None
