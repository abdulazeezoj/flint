from pathlib import Path

import pytest

from flint.errors import FlintError, FlintUserError
from flint.generator import Answers, get_template, list_templates, render


def make_answers(**overrides) -> Answers:
    defaults = dict(
        project_name="My Api",
        slug="my-api",
        package_name="my_api",
        framework="fastapi-hello-world",
        git_init=False,
        install=False,
    )
    defaults.update(overrides)
    return Answers(**defaults)


def test_list_templates_includes_fastapi_hello_world():
    templates = list_templates()
    ids = {t.id for t in templates}
    assert "fastapi-hello-world" in ids


def test_get_template_unknown_raises():
    with pytest.raises(FlintUserError):
        get_template("does-not-exist")


def test_render_creates_expected_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi-hello-world", target, make_answers())

    expected = {
        Path("pyproject.toml"),
        Path("README.md"),
        Path(".gitignore"),
        Path("src/my_api/__init__.py"),
        Path("src/my_api/main.py"),
        Path("tests/test_main.py"),
    }
    assert set(created) == expected
    for rel_path in expected:
        assert (target / rel_path).is_file()


def test_render_substitutes_package_name(tmp_path: Path):
    target = tmp_path / "my-api"
    render("fastapi-hello-world", target, make_answers())

    main_py = (target / "src/my_api/main.py").read_text()
    assert 'FastAPI(title="My Api")' in main_py

    test_py = (target / "tests/test_main.py").read_text()
    assert "from my_api.main import app" in test_py

    readme = (target / "README.md").read_text()
    assert "My Api" in readme
    assert "src/my_api/main.py" in readme


def test_render_refuses_nonempty_directory_without_force(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    with pytest.raises(FlintUserError):
        render("fastapi-hello-world", target, make_answers())


def test_render_force_overwrites_nonempty_directory(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    created = render("fastapi-hello-world", target, make_answers(), force=True)
    assert (target / "pyproject.toml").is_file()
    assert len(created) == 6


def test_render_rolls_back_on_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "my-api"

    import flint.generator as generator_module

    original_render_content = generator_module._render_content
    calls = {"count": 0}

    def flaky_render_content(source_path, context):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("boom")
        return original_render_content(source_path, context)

    monkeypatch.setattr(generator_module, "_render_content", flaky_render_content)

    with pytest.raises(FlintError):
        render("fastapi-hello-world", target, make_answers())

    assert not target.exists()


def test_render_unknown_template_raises(tmp_path: Path):
    with pytest.raises(FlintUserError):
        render("does-not-exist", tmp_path / "x", make_answers())
