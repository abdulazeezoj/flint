import ast
import json
import tomllib
from pathlib import Path

import pytest

import flint.generator as generator_module
from flint.errors import FlintError, FlintUserError
from flint.generator import (
    Answers,
    get_framework,
    get_template,
    list_frameworks,
    list_templates,
    render,
    when_matches,
)


def make_answers(**overrides) -> Answers:
    defaults = dict(
        project_name="My Api",
        slug="my-api",
        package_name="my_api",
        framework="fastapi",
        template="hello-world",
        git_init=False,
        install=False,
        docker=False,
    )
    defaults.update(overrides)
    return Answers(**defaults)


def _assert_all_python_files_parse(target: Path) -> None:
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assert_valid_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


class TestWhenMatches:
    def test_empty_when_always_matches(self):
        assert when_matches({}, {}) is True
        assert when_matches({}, {"anything": "x"}) is True

    def test_single_key_match(self):
        assert when_matches({"worker": ["none"]}, {"worker": "none"}) is True
        assert when_matches({"worker": ["none"]}, {"worker": "celery"}) is False

    def test_multiple_keys_require_all(self):
        when = {"orm": ["sqlmodel"], "migrations": [True]}
        assert when_matches(when, {"orm": "sqlmodel", "migrations": True}) is True
        assert when_matches(when, {"orm": "sqlmodel", "migrations": False}) is False
        assert when_matches(when, {"orm": "sqlalchemy", "migrations": True}) is False

    def test_missing_key_does_not_match(self):
        assert when_matches({"worker": ["none"]}, {}) is False


def test_list_frameworks_includes_fastapi():
    frameworks = list_frameworks()
    ids = {f.id for f in frameworks}
    assert "fastapi" in ids


def test_get_framework_unknown_raises():
    with pytest.raises(FlintUserError):
        get_framework("does-not-exist")


def test_list_templates_includes_hello_world_and_restapi():
    templates = list_templates("fastapi")
    ids = {t.id for t in templates}
    assert {"hello-world", "restapi"} <= ids


def test_get_template_unknown_raises():
    with pytest.raises(FlintUserError):
        get_template("fastapi", "does-not-exist")


def test_get_template_full_id_and_docker_support():
    template = get_template("fastapi", "hello-world")
    assert template.full_id == "fastapi/hello-world"
    assert template.supports_docker is True


def test_hello_world_declares_config_option():
    template = get_template("fastapi", "hello-world")
    assert [o.key for o in template.options] == ["config"]
    assert template.options[0].type == "confirm"
    assert template.options[0].default is False


def test_restapi_declares_expected_options_and_layers():
    template = get_template("fastapi", "restapi")
    option_keys = [o.key for o in template.options]
    assert option_keys == ["database", "orm", "migrations", "worker", "redis"]

    layer_dirs = {layer.dir for layer in template.layers}
    assert layer_dirs == {
        "docker",
        "db-sqlmodel",
        "db-sqlalchemy",
        "migrations-sqlmodel",
        "migrations-sqlalchemy",
        "worker-taskiq",
        "worker-celery",
        "redis",
    }


def test_render_creates_expected_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    expected = {
        Path("pyproject.toml"),
        Path("README.md"),
        Path("AGENTS.md"),
        Path(".gitignore"),
        Path("src/my_api/__init__.py"),
        Path("src/my_api/main.py"),
        Path("tests/test_main.py"),
    }
    assert set(created) == expected
    for rel_path in expected:
        assert (target / rel_path).is_file()


def test_render_with_docker_adds_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers(docker=True))

    assert Path("Dockerfile") in created
    assert Path(".dockerignore") in created
    dockerfile = (target / "Dockerfile").read_text()
    assert "src/my_api/main.py" in dockerfile

    readme = (target / "README.md").read_text()
    assert "docker build -t my-api ." in readme


def test_render_without_docker_omits_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers(docker=False))

    assert Path("Dockerfile") not in created
    assert not (target / "Dockerfile").exists()
    assert "docker build" not in (target / "README.md").read_text()


def test_render_substitutes_package_name(tmp_path: Path):
    target = tmp_path / "my-api"
    render("fastapi", "hello-world", target, make_answers())

    main_py = (target / "src/my_api/main.py").read_text()
    assert 'FastAPI(title="My Api")' in main_py

    test_py = (target / "tests/test_main.py").read_text()
    assert "from my_api.main import app" in test_py

    readme = (target / "README.md").read_text()
    assert "My Api" in readme
    assert "src/my_api/main.py" in readme

    agents_md = (target / "AGENTS.md").read_text()
    assert "my_api" in agents_md


def test_render_hello_world_with_config_option(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "fastapi", "hello-world", target, make_answers(options={"config": True})
    )

    assert Path("src/my_api/config.py") in created
    assert Path(".env") in created
    main_py = (target / "src/my_api/main.py").read_text()
    assert "from my_api.config import settings" in main_py
    _assert_all_python_files_parse(target)


def test_render_hello_world_without_config_option_omits_config_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "fastapi", "hello-world", target, make_answers(options={"config": False})
    )

    assert Path("src/my_api/config.py") not in created
    assert Path(".env") not in created


def test_render_refuses_nonempty_directory_without_force(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    with pytest.raises(FlintUserError):
        render("fastapi", "hello-world", target, make_answers())


def test_render_force_overwrites_nonempty_directory(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    created = render("fastapi", "hello-world", target, make_answers(), force=True)
    assert (target / "pyproject.toml").is_file()
    assert len(created) == 7


def test_render_disabled_template_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    _write_meta(tmp_path / "widget" / "basic", "basic", enabled=False)

    with pytest.raises(FlintUserError):
        render(
            "widget",
            "basic",
            tmp_path / "out",
            make_answers(framework="widget", template="basic"),
        )


def test_render_disabled_framework_raises(tmp_path: Path):
    with pytest.raises(FlintUserError):
        render(
            "flask",
            "hello-world",
            tmp_path / "x",
            make_answers(framework="flask", template="hello-world"),
        )


def test_render_rolls_back_on_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "my-api"

    original_render_content = generator_module._render_content
    calls = {"count": 0}

    def flaky_render_content(source_path, context):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("boom")
        return original_render_content(source_path, context)

    monkeypatch.setattr(generator_module, "_render_content", flaky_render_content)

    with pytest.raises(FlintError):
        render("fastapi", "hello-world", target, make_answers())

    assert not target.exists()


def test_render_unknown_template_raises(tmp_path: Path):
    with pytest.raises(FlintUserError):
        render("fastapi", "does-not-exist", tmp_path / "x", make_answers())


def test_render_propagates_flint_error_without_wrapping_but_still_rolls_back(
    tmp_path: Path, monkeypatch
):
    # A FlintError raised mid-render (e.g. surfaced from a future layer
    # hook) should pass through unchanged rather than being wrapped in
    # the generic "Failed to generate project" message — but generation
    # is still all-or-nothing, so the partial directory must be rolled
    # back just like for any other exception.
    target = tmp_path / "my-api"

    def raise_user_error(layer_root, target_dir, context):
        raise FlintUserError("deliberate")

    monkeypatch.setattr(generator_module, "_render_layer", raise_user_error)

    with pytest.raises(FlintUserError, match="deliberate"):
        render("fastapi", "hello-world", target, make_answers())

    assert not target.exists()


def test_render_content_copies_non_jinja_files_verbatim(tmp_path: Path):
    source = tmp_path / "static.txt"
    source.write_text("{{ not_rendered }}", encoding="utf-8")

    result = generator_module._render_content(source, {"not_rendered": "should not appear"})

    assert result == "{{ not_rendered }}"


def _write_meta(directory: Path, id_: str, enabled: bool = True) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "template.json").write_text(
        json.dumps({"id": id_, "label": id_.title(), "description": "d", "enabled": enabled})
    )


def test_list_frameworks_skips_entries_without_template_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    (tmp_path / "stray.txt").write_text("not a framework")

    frameworks = generator_module.list_frameworks()
    assert [f.id for f in frameworks] == ["widget"]


def test_list_templates_skips_subdirs_without_template_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    _write_meta(tmp_path / "widget" / "basic", "basic")
    (tmp_path / "widget" / "docs").mkdir()  # a dir with no template.json

    templates = generator_module.list_templates("widget")
    assert [t.id for t in templates] == ["basic"]


def test_render_does_not_delete_preexisting_directory_on_failure(tmp_path: Path, monkeypatch):
    # created_before=True (the target dir existed before this render call,
    # e.g. a --force run) must never be cleaned up on failure — only
    # directories flint itself created get rolled back.
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "keepme.txt").write_text("do not delete")

    def raise_error(layer_root, target_dir, context):
        raise FlintUserError("deliberate")

    monkeypatch.setattr(generator_module, "_render_layer", raise_error)

    with pytest.raises(FlintUserError):
        render("fastapi", "hello-world", target, make_answers(), force=True)

    assert target.exists()
    assert (target / "keepme.txt").read_text() == "do not delete"


# --- restapi: the options/layers engine exercised through a real template ---


def make_restapi_answers(**option_overrides) -> Answers:
    options = dict(
        database="sqlite", orm="sqlmodel", migrations=True, worker="none", redis=False
    )
    options.update(option_overrides)
    return make_answers(template="restapi", options=options)


def test_restapi_in_memory_default(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers(database="none", orm="none", migrations=False)
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/routes/items.py") in created
    assert Path("src/my_api/db/session.py") not in created
    assert Path("alembic.ini") not in created
    routes = (target / "src/my_api/routes/items.py").read_text()
    assert "_items" in routes  # the in-memory store
    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_restapi_sqlite_sqlmodel_with_migrations(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers()  # sqlite + sqlmodel + migrations=True
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/db/session.py") in created
    assert Path("src/my_api/db/models.py") in created
    assert Path("alembic.ini") in created
    assert Path("alembic/env.py") in created
    assert Path("alembic/script.py.mako") in created
    assert Path("alembic/versions/.gitkeep") in created

    routes = (target / "src/my_api/routes/items.py").read_text()
    assert "get_session" in routes
    assert "sqlmodel" in (target / "src/my_api/db/session.py").read_text()

    env_py = (target / "alembic/env.py").read_text()
    assert "SQLModel.metadata" in env_py

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "sqlmodel>=0.0.22" in config["project"]["dependencies"]
    assert "alembic>=1.14.0" in config["project"]["dependencies"]


def test_restapi_postgres_sqlalchemy_no_migrations(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers(database="postgres", orm="sqlalchemy", migrations=False)
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/db/session.py") in created
    assert Path("alembic.ini") not in created

    session_py = (target / "src/my_api/db/session.py").read_text()
    assert "sqlalchemy" in session_py.lower()
    env_file = (target / ".env").read_text()
    assert "postgresql+asyncpg://" in env_file

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "asyncpg>=0.30.0" in config["project"]["dependencies"]
    assert "sqlalchemy>=2.0.36" in config["project"]["dependencies"]
    assert not any("alembic" in dep for dep in config["project"]["dependencies"])


def test_restapi_worker_taskiq_implies_redis(tmp_path: Path):
    # Whether a worker choice *implies* redis (skip_value resolution) is a
    # prompts.py concern (see test_prompts.py) — render() just applies
    # whatever options dict it's given, which here already has redis=True
    # to simulate what prompts.prompt_template_options would have resolved.
    target = tmp_path / "api"
    answers = make_restapi_answers(
        database="none", orm="none", migrations=False, worker="taskiq", redis=True
    )
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/worker.py") in created
    assert Path("src/my_api/tasks.py") in created
    assert Path("src/my_api/core/redis.py") in created

    main_py = (target / "src/my_api/main.py").read_text()
    assert "lifespan" in main_py
    assert "/tasks/add" in main_py
    _assert_all_python_files_parse(target)


def test_restapi_worker_celery(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers(database="none", orm="none", migrations=False, worker="celery")
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/worker.py") in created
    worker_py = (target / "src/my_api/worker.py").read_text()
    assert "Celery(" in worker_py
    main_py = (target / "src/my_api/main.py").read_text()
    assert "add.delay" in main_py
    _assert_all_python_files_parse(target)


def test_restapi_redis_standalone_toggle(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers(
        database="none", orm="none", migrations=False, worker="none", redis=True
    )
    created = render("fastapi", "restapi", target, answers)

    assert Path("src/my_api/core/redis.py") in created
    assert Path("src/my_api/worker.py") not in created


def test_restapi_all_features_combined(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_restapi_answers(
        database="postgres", orm="sqlalchemy", migrations=True, worker="celery", redis=True
    )
    created = render("fastapi", "restapi", target, answers, force=True)

    for expected in [
        "src/my_api/db/session.py",
        "alembic.ini",
        "src/my_api/worker.py",
        "src/my_api/core/redis.py",
    ]:
        assert Path(expected) in created, expected

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_render_skips_declared_layer_with_missing_directory(tmp_path: Path, monkeypatch):
    # A layer can be declared in template.json with a `when` that matches
    # but have no directory on disk (e.g. a template-authoring slip) —
    # render() skips it rather than failing generation over an unshipped
    # extra.
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    framework_dir = tmp_path / "widget"
    _write_meta(framework_dir, "widget")
    template_dir = framework_dir / "basic"
    (template_dir / "files").mkdir(parents=True)
    (template_dir / "files" / "README.md").write_text("hello")
    (template_dir / "template.json").write_text(
        json.dumps(
            {
                "id": "basic",
                "label": "Basic",
                "description": "d",
                "enabled": True,
                "layers": [{"dir": "docker", "when": {"docker": [True]}}],
            }
        )
    )

    target = tmp_path / "out"
    created = render(
        "widget", "basic", target, make_answers(framework="widget", template="basic", docker=True)
    )

    assert created == [Path("README.md")]
