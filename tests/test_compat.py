"""Python-version compatibility tests."""

from otinstaller.compat import incompatibility
from otinstaller.registry import Entrypoint, Install, Tool


def make_tool(requires_python=None, name="testtool"):
    return Tool(
        name=name,
        display_name="Test Tool",
        description="A test tool",
        install=Install(method="pip", package="testpkg"),
        entrypoint=Entrypoint(command=name),
        requires_python=requires_python,
    )


def test_no_constraint_is_always_compatible():
    assert incompatibility(make_tool(None), (3, 14, 4)) is None


def test_satisfied_constraints():
    assert incompatibility(make_tool("<3.13"), (3, 12, 14)) is None
    assert incompatibility(make_tool(">=3.10"), (3, 14, 4)) is None
    assert incompatibility(make_tool("==3.14.4"), (3, 14, 4)) is None
    assert incompatibility(make_tool("!=3.13"), (3, 14, 4)) is None


def test_violated_constraint_message():
    problem = incompatibility(make_tool("<3.13"), (3, 14, 4))
    assert problem == (
        "testtool requires Python <3.13 (you are running 3.14.4). "
        "Install Python 3.12 and recreate your venv — see README."
    )


def test_violated_lower_bound():
    problem = incompatibility(make_tool(">=3.10"), (3, 9, 0))
    assert problem.startswith("testtool requires Python >=3.10 (you are running 3.9.0)")


def test_minor_version_compare_ignores_micro():
    assert incompatibility(make_tool("<3.13"), (3, 12, 99)) is None


def test_current_python_used_when_version_not_given(monkeypatch):
    monkeypatch.setattr("otinstaller.compat.current_python", lambda: (3, 14, 4))
    problem = incompatibility(make_tool("<3.13"))
    assert problem is not None
    assert "(you are running 3.14.4)" in problem
