"""Pytest configuration for tests."""

import sys
from pathlib import Path

# Add the project root and pipeline directory to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _never_send_crash_reports(monkeypatch):
    """The real Sentry DSN is in the code; tests must never reach it."""
    monkeypatch.setenv("DO_NOT_TRACK", "1")
