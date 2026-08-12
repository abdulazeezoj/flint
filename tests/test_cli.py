from pathlib import Path

from typer.testing import CliRunner

from flint import __version__, postgen
from flint.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "flint" in result.stdout.lower()


def test_new_non_interactive_happy_path(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi-hello-world",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "pyproject.toml").is_file()
    assert (tmp_path / "my-api" / "src" / "my_api" / "main.py").is_file()
    assert "Success!" in result.stdout


def test_bare_invocation_defaults_to_new(tmp_path: Path, monkeypatch):
    # Bare `flint` defaults git-init and install to True (FR1); stub both
    # out so this test stays hermetic (no real subprocess/network calls)
    # while still verifying the defaults are wired through.
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr(postgen, "git_init", lambda target_dir: calls.append("git") or True)
    monkeypatch.setattr(
        postgen, "install_dependencies", lambda target_dir: calls.append("install") or True
    )

    result = runner.invoke(app, [])
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-app" / "pyproject.toml").is_file()
    assert calls == ["git", "install"]


def test_new_existing_nonempty_directory_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-api").mkdir()
    (tmp_path / "my-api" / "existing.txt").write_text("hi")

    result = runner.invoke(
        app, ["new", "my-api", "--framework", "fastapi-hello-world", "--yes"]
    )
    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_new_invalid_name_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "!!!", "--yes"])
    assert result.exit_code == 1


def test_new_unknown_framework_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["new", "my-api", "--framework", "does-not-exist", "--yes"]
    )
    assert result.exit_code == 1
    assert "Unknown --framework" in result.stdout


def test_new_force_overwrites(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-api").mkdir()
    (tmp_path / "my-api" / "existing.txt").write_text("hi")

    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi-hello-world",
            "--no-git",
            "--no-install",
            "--yes",
            "--force",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "pyproject.toml").is_file()
