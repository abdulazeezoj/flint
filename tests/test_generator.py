import json
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


def test_list_frameworks_includes_fastapi():
    frameworks = list_frameworks()
    ids = {f.id for f in frameworks}
    assert "fastapi" in ids


def test_get_framework_unknown_raises():
    with pytest.raises(FlintUserError):
        get_framework("does-not-exist")


def test_list_templates_includes_hello_world():
    templates = list_templates("fastapi")
    ids = {t.id for t in templates}
    assert "hello-world" in ids


def test_get_template_unknown_raises():
    with pytest.raises(FlintUserError):
        get_template("fastapi", "does-not-exist")


def test_get_template_full_id_and_docker_support():
    template = get_template("fastapi", "hello-world")
    assert template.full_id == "fastapi/hello-world"
    assert template.supports_docker is True


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


def test_render_disabled_template_raises(tmp_path: Path):
    with pytest.raises(FlintUserError):
        render("fastapi", "restapi", tmp_path / "x", make_answers(template="restapi"))


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


def _write_meta(directory: Path, id_: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "template.json").write_text(
        json.dumps({"id": id_, "label": id_.title(), "description": "d", "enabled": True})
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
