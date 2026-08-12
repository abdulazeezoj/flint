import sys
from pathlib import Path

import questionary
import typer
from typer.testing import CliRunner

from flint import __version__, cli, generator, postgen
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
            "fastapi",
            "--template",
            "hello-world",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "pyproject.toml").is_file()
    assert (tmp_path / "my-api" / "src" / "my_api" / "main.py").is_file()
    assert not (tmp_path / "my-api" / "Dockerfile").exists()
    assert "Success!" in result.stdout


def test_new_with_docker_flag(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "hello-world",
            "--docker",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "Dockerfile").is_file()
    assert (tmp_path / "my-api" / ".dockerignore").is_file()


def test_new_docker_unsupported_warns_and_continues(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        generator.TemplateMeta, "supports_docker", property(lambda self: False)
    )

    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "hello-world",
            "--docker",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "doesn't support --docker yet" in result.stdout
    assert not (tmp_path / "my-api" / "Dockerfile").exists()


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
    assert not (tmp_path / "my-app" / "Dockerfile").exists()  # docker defaults off
    assert calls == ["git", "install"]


def test_run_new_interactive_full_flow(tmp_path: Path, monkeypatch, capsys):
    # Drives _run_new directly (bypassing CliRunner, which swaps out
    # sys.stdin for its own stream during invoke() and would clobber an
    # isatty() patch made beforehand) to exercise the fully-interactive
    # path: every prompt actually "asks", including the "Using uv..."
    # message that only prints when interactive.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: True})())

    monkeypatch.setattr(
        questionary, "text", lambda *a, **k: type("Q", (), {"ask": lambda self: "my-api"})()
    )
    monkeypatch.setattr(
        questionary,
        "select",
        lambda *a, **k: type(
            "Q", (), {"ask": lambda self: next(c.value for c in k["choices"] if not c.disabled)}
        )(),
    )
    monkeypatch.setattr(
        questionary, "confirm", lambda *a, **k: type("Q", (), {"ask": lambda self: True})()
    )
    monkeypatch.setattr(postgen, "git_init", lambda target_dir: True)
    monkeypatch.setattr(postgen, "install_dependencies", lambda target_dir: True)

    cli._run_new(
        name=None,
        framework=None,
        template=None,
        docker=None,
        git=None,
        install=None,
        yes=False,
        force=False,
    )

    out = capsys.readouterr().out
    assert "Using uv to manage dependencies." in out
    assert "Success!" in out
    assert (tmp_path / "my-api" / "Dockerfile").is_file()


def test_new_reraises_typer_exit_unchanged(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.prompts, "prompt_install", lambda *a, **k: (_ for _ in ()).throw(typer.Exit(7))
    )

    result = runner.invoke(
        app, ["new", "my-api", "--framework", "fastapi", "--template", "hello-world", "--yes"]
    )
    assert result.exit_code == 7


def test_new_unexpected_error_exits_2(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli.generator, "render", boom)

    result = runner.invoke(
        app, ["new", "my-api", "--framework", "fastapi", "--template", "hello-world", "--yes"]
    )
    assert result.exit_code == 2
    assert "Unexpected error" in result.stdout
    assert "boom" in result.stdout


def test_new_existing_nonempty_directory_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-api").mkdir()
    (tmp_path / "my-api" / "existing.txt").write_text("hi")

    result = runner.invoke(app, ["new", "my-api", "--framework", "fastapi", "--yes"])
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


def test_new_disabled_framework_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "my-api", "--framework", "flask", "--yes"])
    assert result.exit_code == 1
    assert "isn't available yet" in result.stdout


def test_new_unknown_template_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "does-not-exist",
            "--yes",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown --template" in result.stdout


def test_new_disabled_template_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["new", "my-api", "--framework", "fastapi", "--template", "restapi", "--yes"],
    )
    assert result.exit_code == 1
    assert "isn't available yet" in result.stdout


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
            "fastapi",
            "--template",
            "hello-world",
            "--no-git",
            "--no-install",
            "--yes",
            "--force",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "pyproject.toml").is_file()
