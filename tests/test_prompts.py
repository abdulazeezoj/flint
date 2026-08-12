"""Exercises the interactive branches of prompts.py.

questionary drives a real TTY via prompt_toolkit, so these tests
monkeypatch its `.ask()` calls rather than emulating a terminal — see
PRODUCT_ARCH.md §6.
"""

import questionary
import pytest

from flint import prompts
from flint.errors import FlintUserError
from flint.generator import FrameworkMeta, TemplateLayer, TemplateMeta, TemplateOption

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
SOON_TEMPLATE = TemplateMeta(
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
    result = prompts.prompt_template(None, [HELLO_WORLD, SOON_TEMPLATE], interactive=True)
    assert result == "hello-world"


def test_prompt_template_flag_disabled_rejected():
    with pytest.raises(FlintUserError):
        prompts.prompt_template("restapi", [HELLO_WORLD, SOON_TEMPLATE], interactive=True)


def test_prompt_template_non_interactive_picks_first_enabled():
    result = prompts.prompt_template(None, [HELLO_WORLD, SOON_TEMPLATE], interactive=False)
    assert result == "hello-world"


def test_prompt_framework_remembered_default_used_interactive(monkeypatch):
    seen = {}

    def fake_select(question, choices, default):
        seen["default"] = default
        return type("Q", (), {"ask": lambda self: default})()

    monkeypatch.setattr(questionary, "select", fake_select)
    result = prompts.prompt_framework(
        None, [FASTAPI, FLASK_SOON], interactive=True, default_id="fastapi"
    )
    assert result == "fastapi"
    assert seen["default"] == "fastapi"


def test_prompt_framework_remembered_default_used_non_interactive():
    result = prompts.prompt_framework(
        None, [FASTAPI, FLASK_SOON], interactive=False, default_id="fastapi"
    )
    assert result == "fastapi"


def test_prompt_framework_stale_remembered_default_falls_back_to_first_enabled():
    # "flask" is remembered but disabled — must not be selectable just
    # because it was the last choice.
    result = prompts.prompt_framework(
        None, [FASTAPI, FLASK_SOON], interactive=False, default_id="flask"
    )
    assert result == "fastapi"


def test_prompt_framework_unknown_remembered_default_falls_back_to_first_enabled():
    result = prompts.prompt_framework(
        None, [FASTAPI, FLASK_SOON], interactive=False, default_id="does-not-exist"
    )
    assert result == "fastapi"


def test_prompt_template_remembered_default_used_non_interactive():
    result = prompts.prompt_template(
        None, [HELLO_WORLD, SOON_TEMPLATE], interactive=False, default_id="hello-world"
    )
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


def test_prompt_docker_remembered_default_used_interactive(monkeypatch):
    seen = {}

    def fake_confirm(question, default):
        seen["default"] = default
        return type("Q", (), {"ask": lambda self: default})()

    monkeypatch.setattr(questionary, "confirm", fake_confirm)
    assert prompts.prompt_docker(None, interactive=True, remembered=True) is True
    assert seen["default"] is True


def test_prompt_docker_remembered_default_used_non_interactive():
    assert prompts.prompt_docker(None, interactive=False, remembered=True) is True


def test_prompt_docker_no_remembered_value_defaults_false_non_interactive():
    assert prompts.prompt_docker(None, interactive=False, remembered=None) is False


def test_prompt_git_init_interactive(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: False})()
    )
    assert prompts.prompt_git_init(None, interactive=True) is False


def test_prompt_git_init_remembered_default_used_non_interactive():
    assert prompts.prompt_git_init(None, interactive=False, remembered=False) is False


def test_prompt_git_init_no_remembered_value_defaults_true_non_interactive():
    assert prompts.prompt_git_init(None, interactive=False, remembered=None) is True


def test_prompt_install_interactive(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: True})()
    )
    assert prompts.prompt_install(None, interactive=True) is True


def test_prompt_install_remembered_default_used_non_interactive():
    assert prompts.prompt_install(None, interactive=False, remembered=False) is False


def test_prompt_cancelled_raises(monkeypatch):
    monkeypatch.setattr(questionary, "text", lambda *a, **k: type("Q", (), {"ask": lambda self: None})())
    with pytest.raises(FlintUserError):
        prompts.prompt_project_name(None, interactive=True)


def test_prompt_framework_select_cancelled_raises(monkeypatch):
    monkeypatch.setattr(
        questionary, "select", lambda *a, **k: type("Q", (), {"ask": lambda self: None})()
    )
    with pytest.raises(FlintUserError):
        prompts.prompt_framework(None, [FASTAPI, FLASK_SOON], interactive=True)


def test_prompt_docker_cancelled_raises(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: None})()
    )
    with pytest.raises(FlintUserError):
        prompts.prompt_docker(None, interactive=True)


def test_prompt_git_init_cancelled_raises(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: None})()
    )
    with pytest.raises(FlintUserError):
        prompts.prompt_git_init(None, interactive=True)


def test_prompt_install_cancelled_raises(monkeypatch):
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: None})()
    )
    with pytest.raises(FlintUserError):
        prompts.prompt_install(None, interactive=True)


# --- parse_option_flags ---


def test_parse_option_flags_parses_key_value_pairs():
    assert prompts.parse_option_flags(["database=sqlite", "migrations=true"]) == {
        "database": "sqlite",
        "migrations": "true",
    }


def test_parse_option_flags_empty_list():
    assert prompts.parse_option_flags([]) == {}


def test_parse_option_flags_rejects_missing_equals():
    with pytest.raises(FlintUserError):
        prompts.parse_option_flags(["database"])


def test_parse_option_flags_last_duplicate_wins():
    assert prompts.parse_option_flags(["database=sqlite", "database=postgres"]) == {
        "database": "postgres"
    }


# --- prompt_template_options ---

DATABASE_OPTION = TemplateOption(
    key="database",
    label="Database",
    type="select",
    default="sqlite",
    choices=[
        {"value": "none", "label": "None"},
        {"value": "sqlite", "label": "SQLite"},
    ],
)
ORM_OPTION = TemplateOption(
    key="orm",
    label="ORM",
    type="select",
    default="sqlmodel",
    choices=[{"value": "sqlmodel", "label": "SQLModel"}],
    when={"database": ["sqlite"]},
    skip_value="none",
)
MIGRATIONS_OPTION = TemplateOption(
    key="migrations",
    label="Add migrations?",
    type="confirm",
    default=True,
    when={"database": ["sqlite"]},
    skip_value=False,
)
WIDGET_TEMPLATE = TemplateMeta(
    id="widget",
    label="Widget",
    description="",
    enabled=True,
    path=None,
    framework_id="fastapi",
    options=[DATABASE_OPTION, ORM_OPTION, MIGRATIONS_OPTION],
    layers=[TemplateLayer(dir="docker", when={"docker": [True]})],
)


def test_prompt_template_options_unknown_key_rejected():
    with pytest.raises(FlintUserError, match="Unknown option"):
        prompts.prompt_template_options(WIDGET_TEMPLATE, {"bogus": "x"}, interactive=False)


def test_prompt_template_options_provided_select_value_used():
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {"database": "none"}, interactive=False
    )
    assert resolved["database"] == "none"


def test_prompt_template_options_provided_invalid_select_value_rejected():
    with pytest.raises(FlintUserError, match="not a valid value"):
        prompts.prompt_template_options(
            WIDGET_TEMPLATE, {"database": "mysql"}, interactive=False
        )


@pytest.mark.parametrize("raw,expected", [("true", True), ("1", True), ("yes", True),
                                           ("false", False), ("0", False), ("no", False)])
def test_prompt_template_options_provided_confirm_value_parsed(raw, expected):
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE,
        {"database": "sqlite", "orm": "sqlmodel", "migrations": raw},
        interactive=False,
    )
    assert resolved["migrations"] is expected


def test_prompt_template_options_provided_invalid_confirm_value_rejected():
    with pytest.raises(FlintUserError, match="not a valid boolean"):
        prompts.prompt_template_options(
            WIDGET_TEMPLATE,
            {"database": "sqlite", "orm": "sqlmodel", "migrations": "maybe"},
            interactive=False,
        )


def test_prompt_template_options_when_not_matched_uses_skip_value_without_prompting(monkeypatch):
    monkeypatch.setattr(
        questionary, "select", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not prompt"))
    )
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not prompt"))
    )
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {"database": "none"}, interactive=True
    )
    assert resolved == {"database": "none", "orm": "none", "migrations": False}


def test_prompt_template_options_non_interactive_uses_defaults():
    resolved = prompts.prompt_template_options(WIDGET_TEMPLATE, {}, interactive=False)
    assert resolved == {"database": "sqlite", "orm": "sqlmodel", "migrations": True}


def test_prompt_template_options_interactive_prompts_for_unprovided(monkeypatch):
    monkeypatch.setattr(
        questionary,
        "select",
        lambda *a, **k: type(
            "Q", (), {"ask": lambda self: next(c.value for c in k["choices"])}
        )(),
    )
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: False})()
    )
    resolved = prompts.prompt_template_options(WIDGET_TEMPLATE, {}, interactive=True)
    # The select stub always picks the first choice ("none" for database),
    # which means orm's `when` (database in ["sqlite"]) no longer matches,
    # so orm resolves to its skip_value ("none") instead of being prompted.
    assert resolved == {"database": "none", "orm": "none", "migrations": False}


def test_prompt_template_options_cancelled_raises(monkeypatch):
    monkeypatch.setattr(
        questionary, "select", lambda *a, **k: type("Q", (), {"ask": lambda self: None})()
    )
    with pytest.raises(FlintUserError):
        prompts.prompt_template_options(WIDGET_TEMPLATE, {}, interactive=True)


def test_prompt_template_options_remembered_value_used_non_interactive():
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {}, interactive=False, last={"database": "none"}
    )
    # database's remembered "none" is used, which then makes orm/migrations
    # resolve to their skip_value rather than sqlite's own defaults.
    assert resolved == {"database": "none", "orm": "none", "migrations": False}


def test_prompt_template_options_remembered_confirm_value_used_non_interactive():
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE,
        {},
        interactive=False,
        last={"database": "sqlite", "orm": "sqlmodel", "migrations": False},
    )
    assert resolved["migrations"] is False


def test_prompt_template_options_stale_remembered_value_falls_back_to_default():
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {}, interactive=False, last={"database": "mysql"}
    )
    assert resolved["database"] == "sqlite"


def test_prompt_template_options_remembered_value_used_as_interactive_default(monkeypatch):
    seen = {}

    def fake_select(question, choices, default):
        seen["default"] = default
        return type("Q", (), {"ask": lambda self: default})()

    monkeypatch.setattr(questionary, "select", fake_select)
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: k["default"]})()
    )
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {}, interactive=True, last={"database": "none"}
    )
    assert seen["default"] == "none"
    assert resolved["database"] == "none"


def test_prompt_template_options_explicit_flag_wins_over_remembered():
    resolved = prompts.prompt_template_options(
        WIDGET_TEMPLATE, {"database": "sqlite"}, interactive=False, last={"database": "none"}
    )
    assert resolved["database"] == "sqlite"


def test_prompt_template_options_real_restapi_template_default_flow():
    from flint.generator import get_template

    restapi = get_template("fastapi", "restapi")
    resolved = prompts.prompt_template_options(restapi, {}, interactive=False)
    assert resolved == {
        "database": "sqlite",
        "orm": "sqlmodel",
        "migrations": True,
        "worker": "none",
        "redis": False,
    }


def test_prompt_template_options_real_restapi_worker_implies_redis():
    from flint.generator import get_template

    restapi = get_template("fastapi", "restapi")
    resolved = prompts.prompt_template_options(
        restapi, {"worker": "taskiq"}, interactive=False
    )
    assert resolved["redis"] is True
