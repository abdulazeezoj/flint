"""Dedicated test module for the `flask/rest-api` template.

Kept as a standalone file (not appended to `test_generator.py`) so it can
land independently of any other in-flight work on `test_generator.py`
without a merge conflict.

`flask`'s own `template.json` ships with `"enabled": false` (the Flask
framework isn't switched on for end users yet — see
`src/conjure/templates/flask/template.json`). `generator.render()` refuses
to render *any* template under a disabled framework, so every test here
uses the `enable_flask` fixture below to monkeypatch
`generator.get_framework` for the duration of the test, exactly the way
`test_generator.py` already monkeypatches template metadata elsewhere to
exercise otherwise-unreachable branches. This never touches the real
`template.json` on disk.
"""

import ast
import dataclasses
import tomllib
from pathlib import Path

import pytest

import conjure.generator as generator_module
from conjure.generator import Answers, get_template, render


@pytest.fixture(autouse=True)
def enable_flask(monkeypatch):
    """Make the `flask` framework resolve as enabled for this test only,
    without touching `src/conjure/templates/flask/template.json` (which must
    stay `"enabled": false` until the orchestrating session flips it after
    both Flask templates have landed)."""
    real_get_framework = generator_module.get_framework

    def patched(framework_id: str):
        meta = real_get_framework(framework_id)
        if framework_id == "flask":
            meta = dataclasses.replace(meta, enabled=True)
        return meta

    monkeypatch.setattr(generator_module, "get_framework", patched)


def make_answers(**overrides) -> Answers:
    defaults = dict(
        project_name="My Api",
        slug="my-api",
        package_name="my_api",
        framework="flask",
        template="rest-api",
        git_init=False,
        install=False,
        docker=False,
    )
    defaults.update(overrides)
    return Answers(**defaults)


def make_rest_api_answers(**option_overrides) -> Answers:
    docker = option_overrides.pop("docker", False)
    options = dict(
        database="sqlite",
        orm="flask-sqlalchemy",
        migrations=True,
        worker="none",
        broker="none",
        redis=False,
    )
    options.update(option_overrides)
    return make_answers(template="rest-api", options=options, docker=docker)


def _assert_all_python_files_parse(target: Path) -> None:
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assert_valid_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _paths(created: list[Path]) -> set[str]:
    # Excludes .agents/skills/** — every combo below also always pulls in
    # a resolved set of skills (see TestRestApiSkills), which would
    # otherwise need repeating in each of these project-file-focused
    # assertions.
    return {str(p) for p in created if p.parts[:2] != (".agents", "skills")}


class TestTemplateMetadata:
    def test_flask_rest_api_is_listed(self):
        # list_templates() itself doesn't care about framework.enabled —
        # only render() does — so this exercises the template.json parse
        # path without needing the enable_flask fixture's monkeypatch.
        from conjure.generator import list_templates

        ids = {t.id for t in list_templates("flask")}
        assert "rest-api" in ids

    def test_declares_expected_options_and_layers(self):
        template = get_template("flask", "rest-api")
        option_keys = [o.key for o in template.options]
        assert option_keys == ["database", "orm", "migrations", "worker", "broker", "redis"]

        layer_dirs = {layer.dir for layer in template.layers}
        assert layer_dirs == {
            "docker",
            "db-flask-sqlalchemy",
            "db-sqlalchemy",
            "migrations-flask-sqlalchemy",
            "migrations-sqlalchemy",
            "worker-celery",
            "redis",
        }

    def test_supports_docker(self):
        template = get_template("flask", "rest-api")
        assert template.full_id == "flask/rest-api"
        assert template.supports_docker is True

    def test_orm_option_only_offers_flask_sqlalchemy_and_sqlalchemy(self):
        # No taskiq-equivalent async ORM offered — Flask is sync/WSGI, see
        # the template's maintainer README for the "guided vs manual" split
        # rationale (mirrors, not mimics, fastapi/rest-api's sqlmodel vs
        # sqlalchemy choice).
        template = get_template("flask", "rest-api")
        orm_option = next(o for o in template.options if o.key == "orm")
        assert {c["value"] for c in orm_option.choices} == {"flask-sqlalchemy", "sqlalchemy"}

    def test_worker_option_only_offers_none_and_celery(self):
        # Taskiq is deliberately dropped for this template: it's async-first
        # and doesn't pair naturally with a sync WSGI app.
        template = get_template("flask", "rest-api")
        worker_option = next(o for o in template.options if o.key == "worker")
        assert {c["value"] for c in worker_option.choices} == {"none", "celery"}


class TestRestApiRender:
    def test_in_memory_default(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="none", orm="none", migrations=False)
        created = render("flask", "rest-api", target, answers)

        assert _paths(created) == {
            ".env",
            ".env.example",
            ".gitignore",
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "src/my_api/__init__.py",
            "src/my_api/core/__init__.py",
            "src/my_api/core/config.py",
            "src/my_api/main.py",
            "src/my_api/routes/__init__.py",
            "src/my_api/routes/items.py",
            "src/my_api/schemas.py",
            "tests/test_main.py",
        }
        routes = (target / "src/my_api/routes/items.py").read_text()
        assert "_items" in routes  # the in-memory store
        assert "Blueprint" in routes

        main_py = (target / "src/my_api/main.py").read_text()
        # No eager module-level `app = create_app()` — importing main.py
        # must never require the configured database to be reachable (see
        # main.py.jinja's docstring / this template's README "gotchas").
        main_tree = ast.parse(main_py)
        top_level_names = {
            target.id
            for node in main_tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        assert "app" not in top_level_names

        _assert_all_python_files_parse(target)
        _assert_valid_toml(target / "pyproject.toml")

    def test_sqlite_flask_sqlalchemy_with_migrations(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers()  # sqlite + flask-sqlalchemy + migrations=True
        created = render("flask", "rest-api", target, answers)

        assert _paths(created) == {
            ".env",
            ".env.example",
            ".gitignore",
            "AGENTS.md",
            "README.md",
            "migrations/README",
            "migrations/alembic.ini",
            "migrations/env.py",
            "migrations/script.py.mako",
            "migrations/versions/.gitkeep",
            "pyproject.toml",
            "src/my_api/__init__.py",
            "src/my_api/core/__init__.py",
            "src/my_api/core/config.py",
            "src/my_api/core/db.py",
            "src/my_api/main.py",
            "src/my_api/models.py",
            "src/my_api/routes/__init__.py",
            "src/my_api/routes/items.py",
            "src/my_api/schemas.py",
            "tests/conftest.py",
            "tests/test_main.py",
        }

        routes = (target / "src/my_api/routes/items.py").read_text()
        assert "db.session" in routes
        db_py = (target / "src/my_api/core/db.py").read_text()
        assert "flask_sqlalchemy" in db_py
        assert "Migrate" in db_py  # migrations layer overrides core/db.py

        env_py = (target / "migrations/env.py").read_text()
        assert "current_app.extensions['migrate']" in env_py

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "flask-sqlalchemy>=3.1.0" in config["project"]["dependencies"]
        assert "flask-migrate>=4.0.0" in config["project"]["dependencies"]
        assert not any(dep.startswith("alembic") for dep in config["project"]["dependencies"])

    def test_postgres_manual_sqlalchemy_no_migrations(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="postgres", orm="sqlalchemy", migrations=False)
        created = render("flask", "rest-api", target, answers)

        assert _paths(created) == {
            ".env",
            ".env.example",
            ".gitignore",
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "src/my_api/__init__.py",
            "src/my_api/core/__init__.py",
            "src/my_api/core/config.py",
            "src/my_api/core/db.py",
            "src/my_api/main.py",
            "src/my_api/models.py",
            "src/my_api/routes/__init__.py",
            "src/my_api/routes/items.py",
            "src/my_api/schemas.py",
            "tests/conftest.py",
            "tests/test_main.py",
        }

        db_py = (target / "src/my_api/core/db.py").read_text()
        assert "scoped_session" in db_py
        assert "flask_sqlalchemy" not in db_py
        env_file = (target / ".env").read_text()
        assert "postgresql+psycopg://" in env_file
        assert (target / ".env.example").read_text() == env_file

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "psycopg[binary]>=3.1.0" in config["project"]["dependencies"]
        assert "sqlalchemy>=2.0.36" in config["project"]["dependencies"]
        assert not any("alembic" in dep for dep in config["project"]["dependencies"])
        assert not any("flask-sqlalchemy" in dep for dep in config["project"]["dependencies"])

    def test_worker_celery_redis_broker(self, tmp_path: Path):
        # broker="redis" here simulates what prompts.prompt_template_options
        # would already have resolved redis=True to via skip_value — render()
        # just applies whatever options dict it's given (see test_prompts.py
        # for that resolution logic itself).
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none",
            orm="none",
            migrations=False,
            worker="celery",
            broker="redis",
            redis=True,
        )
        created = render("flask", "rest-api", target, answers)

        assert _paths(created) == {
            ".env",
            ".env.example",
            ".gitignore",
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "src/my_api/__init__.py",
            "src/my_api/core/__init__.py",
            "src/my_api/core/config.py",
            "src/my_api/core/redis.py",
            "src/my_api/main.py",
            "src/my_api/routes/__init__.py",
            "src/my_api/routes/items.py",
            "src/my_api/schemas.py",
            "src/my_api/tasks/__init__.py",
            "src/my_api/tasks/example.py",
            "src/my_api/worker.py",
            "tests/test_main.py",
        }

        worker_py = (target / "src/my_api/worker.py").read_text()
        assert "Celery(" in worker_py
        assert "settings.redis_url" in worker_py
        main_py = (target / "src/my_api/main.py").read_text()
        assert "/tasks/add" in main_py
        assert "add.delay" in main_py
        _assert_all_python_files_parse(target)

    def test_worker_celery_rabbitmq_broker(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none",
            orm="none",
            migrations=False,
            worker="celery",
            broker="rabbitmq",
            redis=False,
        )
        created = render("flask", "rest-api", target, answers)

        assert Path("src/my_api/worker.py") in created
        assert Path("src/my_api/core/redis.py") not in created  # not implied by rabbitmq

        worker_py = (target / "src/my_api/worker.py").read_text()
        assert 'broker=settings.rabbitmq_url, backend="rpc://"' in worker_py

        env_file = (target / ".env").read_text()
        assert "RABBITMQ_URL=amqp://" in env_file
        assert "REDIS_URL" not in env_file

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "celery>=5.4.0" in config["project"]["dependencies"]
        assert not any(dep.startswith("redis") for dep in config["project"]["dependencies"])

    def test_redis_standalone_toggle(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none", orm="none", migrations=False, worker="none", broker="none", redis=True
        )
        created = render("flask", "rest-api", target, answers)

        assert Path("src/my_api/core/redis.py") in created
        assert Path("src/my_api/worker.py") not in created

    def test_rabbitmq_broker_with_redis_caching_still_independent(self, tmp_path: Path):
        # broker=rabbitmq and redis=True (caching) aren't mutually exclusive
        # — this is exactly the decoupling the `broker` option exists for
        # (mirrors fastapi/rest-api's identical `broker`/`redis` design,
        # PRODUCT_ARCH.md §4.1).
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none",
            orm="none",
            migrations=False,
            worker="celery",
            broker="rabbitmq",
            redis=True,
        )
        created = render("flask", "rest-api", target, answers)

        assert Path("src/my_api/core/redis.py") in created
        env_file = (target / ".env").read_text()
        assert "RABBITMQ_URL=amqp://" in env_file
        assert "REDIS_URL=redis://" in env_file

    def test_all_features_combined_flask_sqlalchemy(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="sqlite",
            orm="flask-sqlalchemy",
            migrations=True,
            worker="celery",
            broker="redis",
            redis=True,
        )
        created = render("flask", "rest-api", target, answers, force=True)

        for expected in [
            "src/my_api/core/db.py",
            "src/my_api/models.py",
            "migrations/alembic.ini",
            "migrations/env.py",
            "src/my_api/worker.py",
            "src/my_api/tasks/example.py",
            "src/my_api/core/redis.py",
        ]:
            assert Path(expected) in created, expected

        db_py = (target / "src/my_api/core/db.py").read_text()
        assert "Migrate" in db_py

        _assert_all_python_files_parse(target)
        _assert_valid_toml(target / "pyproject.toml")

    def test_all_features_combined_manual_sqlalchemy_postgres(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="postgres",
            orm="sqlalchemy",
            migrations=True,
            worker="celery",
            broker="rabbitmq",
            redis=False,
        )
        created = render("flask", "rest-api", target, answers, force=True)

        for expected in [
            "src/my_api/core/db.py",
            "src/my_api/models.py",
            "alembic.ini",
            "alembic/env.py",
            "alembic/script.py.mako",
            "alembic/versions/.gitkeep",
            "src/my_api/worker.py",
            "src/my_api/tasks/example.py",
        ]:
            assert Path(expected) in created, expected
        assert Path("src/my_api/core/redis.py") not in created
        assert Path("migrations/env.py") not in created  # bare alembic, not Flask-Migrate

        env_py = (target / "alembic/env.py").read_text()
        assert "prepend_sys_path" not in env_py  # that lives in alembic.ini, not env.py
        alembic_ini = (target / "alembic.ini").read_text()
        assert "prepend_sys_path = src" in alembic_ini

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "alembic>=1.14.0" in config["project"]["dependencies"]
        assert "psycopg[binary]>=3.1.0" in config["project"]["dependencies"]

    def test_docker_layer(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(docker=True)
        created = render("flask", "rest-api", target, answers)

        assert Path("Dockerfile") in created
        assert Path(".dockerignore") in created
        dockerfile = (target / "Dockerfile").read_text()
        assert "gunicorn" in dockerfile
        assert 'my_api.main:create_app()' in dockerfile

        config = _assert_valid_toml(target / "pyproject.toml")
        assert "gunicorn>=23.0.0" in config["project"]["dependencies"]
        _assert_all_python_files_parse(target)

    def test_pyproject_always_a_valid_toml_and_python_files_always_parse(self, tmp_path: Path):
        # A light combinatorial sweep beyond the named scenarios above —
        # catches whitespace-control regressions (PRODUCT_ARCH.md §4.3)
        # that only show up for less obvious combinations.
        combos = [
            dict(database="sqlite", orm="flask-sqlalchemy", migrations=False),
            dict(database="sqlite", orm="sqlalchemy", migrations=True),
            dict(database="postgres", orm="flask-sqlalchemy", migrations=True),
            dict(worker="celery", broker="redis", redis=False),
            dict(worker="celery", broker="rabbitmq", redis=True),
        ]
        for i, overrides in enumerate(combos):
            target = tmp_path / f"combo-{i}"
            answers = make_rest_api_answers(**overrides)
            render("flask", "rest-api", target, answers)
            _assert_all_python_files_parse(target)
            _assert_valid_toml(target / "pyproject.toml")


def _skill_ids(created: list[Path]) -> set[str]:
    # .agents/skills/README.md is the generated index, not a skill id.
    return {
        p.parts[2]
        for p in created
        if p.parts[:2] == (".agents", "skills") and len(p.parts) > 3
    }


class TestRestApiSkills:
    def test_flask_sqlalchemy_with_migrations_and_worker(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers()  # sqlite + flask-sqlalchemy + migrations=True
        created = render("flask", "rest-api", target, answers)

        assert _skill_ids(created) == {
            "flask",
            "pydantic-settings",
            "pytest",
            "flask-sqlalchemy",
            "flask-migrate",
        }
        assert Path(".agents/skills/README.md") in created

    def test_manual_sqlalchemy_with_migrations(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="sqlite", orm="sqlalchemy", migrations=True)
        created = render("flask", "rest-api", target, answers)

        assert _skill_ids(created) == {
            "flask",
            "pydantic-settings",
            "pytest",
            "sqlalchemy",
            "alembic",
        }

    def test_no_database_no_worker_no_redis(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="none", orm="none", migrations=False)
        created = render("flask", "rest-api", target, answers)

        assert _skill_ids(created) == {"flask", "pydantic-settings", "pytest"}

    def test_celery_and_redis_add_their_skills(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none", orm="none", migrations=False,
            worker="celery", broker="redis", redis=True,
        )
        created = render("flask", "rest-api", target, answers)

        assert _skill_ids(created) == {"flask", "pydantic-settings", "pytest", "celery", "redis"}
