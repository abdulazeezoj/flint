"""Tests for the flask/hello-world template.

Deliberately a standalone file (not appended to test_generator.py) so it
doesn't collide with the parallel flask/rest-api agent's own new test
file (see the task brief this was built from).

flask/template.json ships with "enabled": false (PRODUCT_ARCH.md §4 — a
disabled framework is a stub until it's ready; the orchestrating agent
flips this on once both Flask templates have landed). `render()` checks
the *framework's* enabled flag before the template's own, so exercising
this template's actual rendering needs the framework flipped on for the
duration of a test — the `enabled_flask_framework` fixture below does
that by monkeypatching `generator.get_framework`, never by editing the
on-disk `flask/template.json` (which this test suite must leave alone).
"""

import ast
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

import conjure.generator as generator_module
from conjure.errors import ConjureUserError
from conjure.generator import Answers, get_template, render


@pytest.fixture(autouse=True)
def enabled_flask_framework(monkeypatch):
    """Make the `flask` framework appear enabled for these tests only.

    `generator.render()` calls `get_framework` by bare name from within
    the same module, so monkeypatching `generator_module.get_framework`
    is enough to intercept every call `render()` makes internally (the
    same technique the existing suite uses for `_render_layer`).
    """
    original_get_framework = generator_module.get_framework

    def patched(framework_id: str):
        meta = original_get_framework(framework_id)
        if framework_id == "flask":
            meta = replace(meta, enabled=True)
        return meta

    monkeypatch.setattr(generator_module, "get_framework", patched)


def make_answers(**overrides) -> Answers:
    defaults = dict(
        project_name="My Api",
        slug="my-api",
        package_name="my_api",
        framework="flask",
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


def test_get_template_full_id_and_docker_support():
    template = get_template("flask", "hello-world")
    assert template.full_id == "flask/hello-world"
    assert template.supports_docker is True


def test_hello_world_declares_config_option():
    template = get_template("flask", "hello-world")
    assert [o.key for o in template.options] == ["config"]
    assert template.options[0].type == "confirm"
    assert template.options[0].default is False


def test_hello_world_declares_docker_and_config_layers():
    template = get_template("flask", "hello-world")
    layer_dirs = {layer.dir for layer in template.layers}
    assert layer_dirs == {"docker", "config"}


def test_render_creates_expected_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("flask", "hello-world", target, make_answers())

    expected = {
        Path("pyproject.toml"),
        Path("README.md"),
        Path("AGENTS.md"),
        Path(".gitignore"),
        Path("src/my_api/__init__.py"),
        Path("src/my_api/main.py"),
        Path("tests/test_main.py"),
    }
    # Subset check, not exact equality — hello-world also always pulls
    # in the flask/pytest skills (see test_render_includes_expected_skills).
    assert expected <= set(created)
    for rel_path in expected:
        assert (target / rel_path).is_file()

    _assert_all_python_files_parse(target)


def test_render_includes_expected_skills(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("flask", "hello-world", target, make_answers())

    skill_paths = {p for p in created if p.parts[:2] == (".agents", "skills")}
    skill_ids = {p.parts[2] for p in skill_paths if len(p.parts) > 3}
    assert skill_ids == {"flask", "pytest"}
    assert Path(".agents/skills/README.md") in skill_paths
    assert not (target / ".agents/skills/pydantic-settings").exists()
    _assert_valid_toml(target / "pyproject.toml")


def test_render_with_docker_adds_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("flask", "hello-world", target, make_answers(docker=True))

    assert Path("Dockerfile") in created
    assert Path(".dockerignore") in created
    dockerfile = (target / "Dockerfile").read_text()
    assert "--chdir" in dockerfile
    assert "src" in dockerfile
    assert "my_api.main:app" in dockerfile

    pyproject = (target / "pyproject.toml").read_text()
    assert "gunicorn" in pyproject

    readme = (target / "README.md").read_text()
    assert "docker build -t my-api ." in readme

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_render_without_docker_omits_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("flask", "hello-world", target, make_answers(docker=False))

    assert Path("Dockerfile") not in created
    assert Path(".dockerignore") not in created
    assert not (target / "Dockerfile").exists()
    assert "docker build" not in (target / "README.md").read_text()

    pyproject = (target / "pyproject.toml").read_text()
    assert "gunicorn" not in pyproject


def test_render_substitutes_package_name(tmp_path: Path):
    target = tmp_path / "my-api"
    render("flask", "hello-world", target, make_answers())

    main_py = (target / "src/my_api/main.py").read_text()
    assert "Flask(__name__)" in main_py
    assert '{"message": "Hello, World!"}' in main_py

    test_py = (target / "tests/test_main.py").read_text()
    assert "from my_api.main import app" in test_py

    readme = (target / "README.md").read_text()
    assert "My Api" in readme
    assert "src/my_api/main" in readme

    agents_md = (target / "AGENTS.md").read_text()
    assert "my_api" in agents_md

    pyproject = (target / "pyproject.toml").read_text()
    assert 'name = "my-api"' in pyproject


def test_render_hello_world_with_config_option(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "flask", "hello-world", target, make_answers(options={"config": True})
    )

    assert Path("src/my_api/core/config.py") in created
    assert Path(".env") in created
    assert Path(".env.example") in created
    assert (target / ".env").read_text() == (target / ".env.example").read_text()

    main_py = (target / "src/my_api/main.py").read_text()
    assert "from my_api.core.config import settings" in main_py
    assert "Flask(__name__)" in main_py

    pyproject = (target / "pyproject.toml").read_text()
    assert "pydantic-settings" in pyproject

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_render_hello_world_without_config_option_omits_config_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "flask", "hello-world", target, make_answers(options={"config": False})
    )

    assert Path("src/my_api/core/config.py") not in created
    assert Path(".env") not in created
    assert Path(".env.example") not in created

    pyproject = (target / "pyproject.toml").read_text()
    assert "pydantic-settings" not in pyproject


def test_render_config_and_docker_together(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "flask",
        "hello-world",
        target,
        make_answers(docker=True, options={"config": True}),
    )

    assert Path("src/my_api/core/config.py") in created
    assert Path("Dockerfile") in created

    pyproject = (target / "pyproject.toml").read_text()
    assert "pydantic-settings" in pyproject
    assert "gunicorn" in pyproject

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_render_refuses_nonempty_directory_without_force(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    with pytest.raises(ConjureUserError):
        render("flask", "hello-world", target, make_answers())
