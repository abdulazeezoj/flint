import sys
from pathlib import Path

import questionary
import typer
from typer.testing import CliRunner

from flint import __version__, cli, generator, postgen, prefs
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
    assert "uv run fastapi dev src/my_api/main.py" in result.stdout


def test_new_flask_uses_flask_run_command(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "flask",
            "--template",
            "hello-world",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "my-api" / "src" / "my_api" / "main.py").is_file()
    assert "uv run flask --app src/my_api/main.py run" in result.stdout
    assert "fastapi dev" not in result.stdout


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
        option=[],
        docker=None,
        git=None,
        install=None,
        yes=False,
        force=False,
        remember=True,
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
    templates_dir = tmp_path / "templates"
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (templates_dir / "widget").mkdir(parents=True)
    (templates_dir / "widget" / "template.json").write_text(
        '{"id": "widget", "label": "Widget", "description": "d", "enabled": false}'
    )
    (templates_dir / "widget" / "basic").mkdir()
    (templates_dir / "widget" / "basic" / "template.json").write_text(
        '{"id": "basic", "label": "Basic", "description": "d", "enabled": true}'
    )
    monkeypatch.setattr(generator, "TEMPLATES_DIR", templates_dir)
    monkeypatch.chdir(work_dir)

    result = runner.invoke(app, ["new", "my-api", "--framework", "widget", "--yes"])
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


def test_new_rest_api_with_options(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "--option",
            "database=none",
            "-o",
            "worker=none",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Options: database=none, orm=none, migrations=False, worker=none," in (
        result.stdout
    )
    assert "broker=none," in result.stdout
    assert "redis=False" in result.stdout
    assert (tmp_path / "my-api" / "src" / "my_api" / "routes" / "items.py").is_file()
    assert not (tmp_path / "my-api" / "src" / "my_api" / "db").exists()


def test_new_option_unknown_key_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "--option",
            "bogus=x",
            "--yes",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown option" in result.stdout


def test_new_option_invalid_value_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "my-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "--option",
            "database=mysql",
            "--yes",
        ],
    )
    assert result.exit_code == 1
    assert "not a valid value" in result.stdout


def test_new_option_malformed_flag_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["new", "my-api", "--framework", "fastapi", "--template", "hello-world", "-o", "config"],
    )
    assert result.exit_code == 1
    assert "key=value" in result.stdout


def test_new_remembers_choices_across_runs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "first-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "-o",
            "database=postgres",
            "-o",
            "orm=sqlalchemy",
            "--docker",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert prefs.PREFS_FILE.is_file()

    # Second run supplies no framework/template/options at all — should
    # fall back to what was just remembered, not the template's own
    # hardcoded defaults (sqlite/sqlmodel/no docker).
    result2 = runner.invoke(
        app, ["new", "second-api", "--no-git", "--no-install", "--yes"]
    )
    assert result2.exit_code == 0, result2.stdout
    assert "Options: database=postgres, orm=sqlalchemy" in result2.stdout
    assert (tmp_path / "second-api" / "Dockerfile").is_file()


def test_new_no_remember_does_not_persist_or_read(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "new",
            "first-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "-o",
            "database=postgres",
            "--no-git",
            "--no-install",
            "--yes",
            "--no-remember",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert not prefs.PREFS_FILE.exists()

    result2 = runner.invoke(
        app,
        [
            "new",
            "second-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert "Options: database=sqlite" in result2.stdout


def test_new_remembered_defaults_never_override_explicit_flags(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(
        app,
        [
            "new",
            "first-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "-o",
            "database=postgres",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    result2 = runner.invoke(
        app,
        [
            "new",
            "second-api",
            "--framework",
            "fastapi",
            "--template",
            "rest-api",
            "-o",
            "database=sqlite",
            "--no-git",
            "--no-install",
            "--yes",
        ],
    )
    assert result2.exit_code == 0, result2.stdout
    assert "Options: database=sqlite" in result2.stdout


def test_new_stale_remembered_option_falls_back_to_template_default(tmp_path: Path, monkeypatch):
    # A remembered value that's no longer valid for an option (e.g. hand-
    # edited or from a since-changed template) must be ignored rather
    # than raising or silently corrupting generation.
    monkeypatch.chdir(tmp_path)
    prefs.save_prefs(
        {
            "last_framework": "fastapi",
            "last_templates": {"fastapi": "rest-api"},
            "templates": {
                "fastapi/rest-api": {
                    "options": {"database": "mysql"},
                    "docker": False,
                    "git_init": False,
                    "install": False,
                }
            },
        }
    )
    result = runner.invoke(app, ["new", "my-api", "--no-git", "--no-install", "--yes"])
    assert result.exit_code == 0, result.stdout
    assert "Options: database=sqlite" in result.stdout


def test_new_prints_options_summary_line(tmp_path: Path, monkeypatch):
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
    assert "Options: config=False" in result.stdout
