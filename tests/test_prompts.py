"""Exercises the interactive branches of prompts.py.

questionary drives a real TTY via prompt_toolkit, so these tests
monkeypatch its `.ask()` calls rather than emulating a terminal — see
PRODUCT_ARCH.md §6.
"""

import questionary
import pytest

from flint import prompts
from flint.errors import FlintUserError
from flint.generator import FrameworkMeta, TemplateMeta

FASTAPI = FrameworkMeta(id="fastapi", label="FastAPI", description="", enabled=True, path=None)
FLASK_SOON = FrameworkMeta(id="flask", label="Flask", description="", enabled=False, path=None)

HELLO_WORLD = TemplateMeta(
    id="hello-world",
    label="Hello World",
    description="",
    enabled=True,
    path=None,
    framework_id="fastapi",
)
RESTAPI_SOON = TemplateMeta(
    id="restapi",
    label="REST API",
    description="",
    enabled=False,
    path=None,
    framework_id="fastapi",
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
        questionary, "select", lambda *a, **k: type("Q", (), {"ask": lambda self: "fastapi"})()
    )
    result = prompts.prompt_framework(None, [FASTAPI, FLASK_SOON], interactive=True)
    assert result == "fastapi"


def test_prompt_framework_flag_disabled_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_framework("flask", [FASTAPI, FLASK_SOON], interactive=True)


def test_prompt_framework_flag_unknown_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_framework("does-not-exist", [FASTAPI, FLASK_SOON], interactive=True)


def test_prompt_framework_non_interactive_picks_first_enabled():
    result = prompts.prompt_framework(None, [FASTAPI, FLASK_SOON], interactive=False)
    assert result == "fastapi"


def test_prompt_template_interactive_select(monkeypatch):
    monkeypatch.setattr(
        questionary, "select", lambda *a, **k: type("Q", (), {"ask": lambda self: "hello-world"})()
    )
    result = prompts.prompt_template(None, [HELLO_WORLD, RESTAPI_SOON], interactive=True)
    assert result == "hello-world"


def test_prompt_template_flag_disabled_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_template("restapi", [HELLO_WORLD, RESTAPI_SOON], interactive=True)


def test_prompt_template_non_interactive_picks_first_enabled():
    result = prompts.prompt_template(None, [HELLO_WORLD, RESTAPI_SOON], interactive=False)
    assert result == "hello-world"


def test_prompt_docker_interactive_default_false(monkeypatch):
    seen = {}

    def fake_confirm(question, default):
        seen["default"] = default
        return type("Q", (), {"ask": lambda self: default})()

    monkeypatch.setattr(questionary, "confirm", fake_confirm)
    assert prompts.prompt_docker(None, interactive=True) is False
    assert seen["default"] is False


def test_prompt_docker_flag_skips_prompt(monkeypatch):
    monkeypatch.setattr(questionary, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not prompt")))
    assert prompts.prompt_docker(True, interactive=True) is True


def test_prompt_docker_non_interactive_defaults_false():
    assert prompts.prompt_docker(None, interactive=False) is False


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
