"""Dedicated test module for the `flask/full-stack` template.

Kept as a standalone file (not appended to `test_generator.py`) for the
same reason as `test_flask_rest_api.py`: `flask`'s own `template.json`
ships with `"enabled": false` (see `src/flint/templates/flask/template.json`),
so every test here uses the `enable_flask` fixture below to monkeypatch
`generator.get_framework` for the duration of the test, exactly the way
`test_flask_rest_api.py` already does.
"""

import ast
import dataclasses
import tomllib
from pathlib import Path

import pytest

import flint.generator as generator_module
from flint.generator import Answers, get_template, render


@pytest.fixture(autouse=True)
def enable_flask(monkeypatch):
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
        template="full-stack",
        git_init=False,
        install=False,
        docker=False,
    )
    defaults.update(overrides)
    return Answers(**defaults)


def make_full_stack_answers(**option_overrides) -> Answers:
    docker = option_overrides.pop("docker", False)
    options = dict(
        database="sqlite",
        orm="flask-sqlalchemy",
        migrations=True,
        worker="none",
        broker="none",
        redis=False,
        css="vanilla",
    )
    options.update(option_overrides)
    return make_answers(options=options, docker=docker)


def _assert_all_python_files_parse(target: Path) -> None:
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assert_valid_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _skill_ids(created: list[Path]) -> set[str]:
    return {
        p.parts[2] for p in created if p.parts[:2] == (".agents", "skills") and len(p.parts) > 3
    }


class TestTemplateMetadata:
    def test_flask_full_stack_is_listed(self):
        from flint.generator import list_templates

        ids = {t.id for t in list_templates("flask")}
        assert "full-stack" in ids

    def test_declares_rest_apis_options_plus_css(self):
        # Deliberately kept in lockstep with rest-api's non-presentation
        # options, plus one extra (css) unique to this template — see this
        # template's README.md "Options" section.
        full_stack = get_template("flask", "full-stack")
        rest_api = get_template("flask", "rest-api")
        full_stack_keys = [o.key for o in full_stack.options]
        assert full_stack_keys == [o.key for o in rest_api.options] + ["css"]

    def test_css_option_offers_vanilla_and_tailwind(self):
        template = get_template("flask", "full-stack")
        css_option = next(o for o in template.options if o.key == "css")
        assert css_option.default == "vanilla"
        assert {c["value"] for c in css_option.choices} == {"vanilla", "tailwind"}

    def test_supports_docker(self):
        template = get_template("flask", "full-stack")
        assert template.full_id == "flask/full-stack"
        assert template.supports_docker is True


class TestFullStackRender:
    def test_in_memory_default(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(database="none", orm="none", migrations=False)
        created = render("flask", "full-stack", target, answers)

        assert Path("src/my_api/routes/todos.py") in created
        assert Path("src/my_api/templates/index.html") in created
        assert Path("src/my_api/templates/base.html") in created
        assert Path("src/my_api/templates/partials/todo_item.html") in created
        assert Path("src/my_api/static/css/style.css") in created
        assert Path("src/my_api/core/db.py") not in created
        assert Path("migrations/env.py") not in created

        routes = (target / "src/my_api/routes/todos.py").read_text()
        assert "_todos" in routes  # the in-memory store
        assert "Blueprint" in routes

        main_py = (target / "src/my_api/main.py").read_text()
        # No eager module-level `app = create_app()` — importing main.py
        # must never require the configured database to be reachable.
        main_tree = ast.parse(main_py)
        top_level_names = {
            t.id
            for node in main_tree.body
            if isinstance(node, ast.Assign)
            for t in node.targets
            if isinstance(t, ast.Name)
        }
        assert "app" not in top_level_names

        _assert_all_python_files_parse(target)
        _assert_valid_toml(target / "pyproject.toml")

    def test_sqlite_flask_sqlalchemy_with_migrations(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers()  # sqlite + flask-sqlalchemy + migrations=True
        created = render("flask", "full-stack", target, answers)

        assert Path("src/my_api/core/db.py") in created
        assert Path("src/my_api/models.py") in created
        assert Path("migrations/env.py") in created

        routes = (target / "src/my_api/routes/todos.py").read_text()
        assert "db.session" in routes
        models_py = (target / "src/my_api/models.py").read_text()
        assert "class Todo" in models_py
        db_py = (target / "src/my_api/core/db.py").read_text()
        assert "Migrate" in db_py  # migrations layer overrides core/db.py

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "flask-sqlalchemy>=3.1.0" in config["project"]["dependencies"]
        assert "flask-migrate>=4.0.0" in config["project"]["dependencies"]

    def test_postgres_manual_sqlalchemy_no_migrations(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(database="postgres", orm="sqlalchemy", migrations=False)
        created = render("flask", "full-stack", target, answers)

        assert Path("src/my_api/core/db.py") in created
        assert Path("migrations/env.py") not in created

        models_py = (target / "src/my_api/models.py").read_text()
        assert "class Todo(Base)" in models_py
        db_py = (target / "src/my_api/core/db.py").read_text()
        assert "scoped_session" in db_py
        env_file = (target / ".env").read_text()
        assert "postgresql+psycopg://" in env_file

        _assert_all_python_files_parse(target)
        config = _assert_valid_toml(target / "pyproject.toml")
        assert "psycopg[binary]>=3.1.0" in config["project"]["dependencies"]
        assert not any("flask-sqlalchemy" in dep for dep in config["project"]["dependencies"])

    def test_worker_celery_redis_broker(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(
            database="none",
            orm="none",
            migrations=False,
            worker="celery",
            broker="redis",
            redis=True,
        )
        created = render("flask", "full-stack", target, answers)

        assert Path("src/my_api/worker.py") in created
        assert Path("src/my_api/core/redis.py") in created
        worker_py = (target / "src/my_api/worker.py").read_text()
        assert "Celery(" in worker_py
        main_py = (target / "src/my_api/main.py").read_text()
        assert "add.delay" in main_py

        _assert_all_python_files_parse(target)

    def test_all_features_combined(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(
            database="postgres",
            orm="sqlalchemy",
            migrations=True,
            worker="celery",
            broker="redis",
            redis=True,
            docker=True,
        )
        created = render("flask", "full-stack", target, answers, force=True)

        for expected in [
            "src/my_api/core/db.py",
            "src/my_api/models.py",
            "src/my_api/worker.py",
            "src/my_api/tasks/example.py",
            "src/my_api/core/redis.py",
            "src/my_api/templates/index.html",
            "src/my_api/static/css/style.css",
            "Dockerfile",
        ]:
            assert Path(expected) in created, expected

        _assert_all_python_files_parse(target)
        _assert_valid_toml(target / "pyproject.toml")

    def test_no_leftover_jinja_in_runtime_templates(self, tmp_path: Path):
        # Same rationale as fastapi/full-stack's equivalent test: the
        # templates/ and static/ files carry the *generated app's own*
        # runtime Jinja2 syntax and must survive flint's generator untouched
        # (they have no .jinja suffix specifically so they're copied
        # verbatim — see this template's README.md gotcha #1).
        target = tmp_path / "app"
        answers = make_full_stack_answers()
        render("flask", "full-stack", target, answers)

        index_html = (target / "src/my_api/templates/index.html").read_text()
        assert "{% for todo in todos %}" in index_html

        todo_item_html = (target / "src/my_api/templates/partials/todo_item.html").read_text()
        assert "{{ todo.title }}" in todo_item_html

        for path in target.rglob("*"):
            if path.is_dir() or "templates" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "{{" not in text, path
            assert "{%" not in text, path


class TestFullStackCSS:
    def test_vanilla_is_default(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers()  # css="vanilla" by default
        created = render("flask", "full-stack", target, answers)

        assert Path("src/my_api/static/css/style.css") in created
        assert Path("src/my_api/static/css/input.css") not in created
        config = _assert_valid_toml(target / "pyproject.toml")
        assert not any("pytailwindcss" in dep for dep in config["project"]["dependencies"])

    def test_tailwind(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(css="tailwind")
        created = render("flask", "full-stack", target, answers)

        # input.css (source, tracked) ships; style.css (build output) does
        # not — it's produced by the Tailwind CLI, not by flint.
        assert Path("src/my_api/static/css/input.css") in created
        assert Path("src/my_api/static/css/style.css") not in created

        input_css = (target / "src/my_api/static/css/input.css").read_text()
        assert '@import "tailwindcss"' in input_css
        assert "--color-accent" in input_css

        index_html = (target / "src/my_api/templates/index.html").read_text()
        assert "bg-accent" in index_html  # Tailwind utility classes

        config = _assert_valid_toml(target / "pyproject.toml")
        assert any("pytailwindcss" in dep for dep in config["project"]["dependencies"])

        gitignore = (target / ".gitignore").read_text()
        assert "static/css/style.css" in gitignore

        _assert_all_python_files_parse(target)

    def test_tailwind_docker_build_step(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(css="tailwind", docker=True)
        created = render("flask", "full-stack", target, answers, force=True)

        assert Path("Dockerfile") in created
        dockerfile = (target / "Dockerfile").read_text()
        assert "uv run tailwindcss" in dockerfile
        assert "--minify" in dockerfile


class TestFullStackSkills:
    def test_flask_sqlalchemy_with_migrations(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers()  # sqlite + flask-sqlalchemy + migrations=True
        created = render("flask", "full-stack", target, answers)

        assert _skill_ids(created) == {
            "flask",
            "pydantic-settings",
            "pytest",
            "flask-sqlalchemy",
            "flask-migrate",
        }

    def test_no_database_no_worker_no_redis(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(database="none", orm="none", migrations=False)
        created = render("flask", "full-stack", target, answers)

        assert _skill_ids(created) == {"flask", "pydantic-settings", "pytest"}
