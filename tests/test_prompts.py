"""Exercises the interactive branches of prompts.py.

questionary drives a real TTY via prompt_toolkit, so these tests
monkeypatch its `.ask()` calls rather than emulating a terminal — see
PRODUCT_ARCH.md §6.
"""

import questionary
import pytest

from flint import prompts
from flint.errors import FlintUserError
from flint.generator import TemplateMeta

FASTAPI = TemplateMeta(
    id="fastapi-hello-world",
    label="FastAPI — Hello World",
    description="",
    enabled=True,
    path=None,
)
FLASK_SOON = TemplateMeta(
    id="flask-hello-world", label="Flask", description="", enabled=False, path=None
)


def test_prompt_project_name_interactive_accepts_valid_answer(monkeypatch):
    monkeypatch.setattr(questionary, "text", lambda *a, **k: type("Q", (), {"ask": lambda self: "My Api"})())

    project_name, slug, package_name = prompts.prompt_project_name(None, interactive=True)
    assert project_name == "My Api"
    assert slug == "my-api"
    assert package_name == "my_api"


def test_prompt_project_name_interactive_reprompts_on_invalid(monkeypatch, capsys):
    answers = iter(["!!!", "my-api"])
    monkeypatch.setattr(
        questionary, "text", lambda *a, **k: type("Q", (), {"ask": lambda self: next(answers)})()
    )

    project_name, slug, package_name = prompts.prompt_project_name(None, interactive=True)
    assert slug == "my-api"
    assert "does not contain" in capsys.readouterr().out


def test_prompt_project_name_uses_flag_without_prompting(monkeypatch):
    monkeypatch.setattr(questionary, "text", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not prompt")))
    project_name, slug, package_name = prompts.prompt_project_name("my-api", interactive=True)
    assert (project_name, slug, package_name) == ("my-api", "my-api", "my_api")


def test_prompt_project_name_non_interactive_uses_default():
    project_name, slug, package_name = prompts.prompt_project_name(None, interactive=False)
    assert project_name == prompts.DEFAULT_PROJECT_NAME


def test_prompt_framework_interactive_select(monkeypatch):
    monkeypatch.setattr(
        questionary, "select", lambda *a, **k: type("Q", (), {"ask": lambda self: "fastapi-hello-world"})()
    )
    result = prompts.prompt_framework(None, [FASTAPI, FLASK_SOON], interactive=True)
    assert result == "fastapi-hello-world"


def test_prompt_framework_flag_disabled_template_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_framework("flask-hello-world", [FASTAPI, FLASK_SOON], interactive=True)


def test_prompt_framework_flag_unknown_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_framework("does-not-exist", [FASTAPI, FLASK_SOON], interactive=True)


def test_prompt_framework_non_interactive_picks_first_enabled():
    result = prompts.prompt_framework(None, [FASTAPI, FLASK_SOON], interactive=False)
    assert result == "fastapi-hello-world"


def test_prompt_git_init_interactive(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: False})()
    )
    assert prompts.prompt_git_init(None, interactive=True) is False


def test_prompt_install_interactive(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: True})()
    )
    assert prompts.prompt_install(None, interactive=True) is True


def test_prompt_cancelled_raises(monkeypatch):
    monkeypatch.setattr(questionary, "text", lambda *a, **k: type("Q", (), {"ask": lambda self: None})())
    with pytest.raises(FlintUserError):
        prompts.prompt_project_name(None, interactive=True)
