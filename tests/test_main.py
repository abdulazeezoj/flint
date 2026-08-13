"""Covers the `python -m spindle` / `python -m spindle.cli` entry-point guards.

runpy re-executes the module with __name__ == "__main__" in-process (unlike
subprocess), so coverage.py sees it.
"""

import runpy
import sys

import pytest

from spindle import __version__


def test_dunder_main_invokes_cli(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["spindle", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("spindle", run_name="__main__")
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_module_main_guard(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["spindle", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("spindle.cli", run_name="__main__")
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_dunder_main_plain_import_does_not_invoke_cli():
    # A normal import (__name__ == "spindle.__main__", not "__main__") must
    # not call main() — just re-exports it. Covers the guard's "not taken"
    # branch, which the runpy-based tests above (run_name="__main__")
    # never exercise.
    import spindle.__main__ as dunder_main

    assert dunder_main.main is not None
