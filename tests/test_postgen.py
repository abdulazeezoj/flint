"""Direct unit tests for postgen.py's subprocess-driving steps.

git_init/install_dependencies are never actually invoked by the CLI tests
(those pass --no-git --no-install, or stub postgen entirely), so they
need their own coverage here. subprocess.run is monkeypatched throughout
to keep this hermetic — no real git/uv/network involved.
"""

import subprocess
from pathlib import Path

from brupy import postgen


def _summary_kwargs(**overrides):
    kwargs = dict(
        project_name="My Api",
        slug="my-api",
        template_full_id="fastapi/hello-world",
        target_dir=Path("my-api"),
        created=[Path("pyproject.toml")],
        git_ok=False,
        installed_ok=False,
        installed_requested=False,
        run_command="uv run fastapi dev src/my_api/main.py",
    )
    kwargs.update(overrides)
    return kwargs


class _FakeCompletedProcess:
    def __init__(self, args):
        self.args = args
        self.returncode = 0


def test_git_init_not_found(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(postgen.shutil, "which", lambda name: None)
    assert postgen.git_init(tmp_path) is False
    assert "git not found" in capsys.readouterr().out


def test_git_init_success(tmp_path: Path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompletedProcess(cmd)

    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(postgen.subprocess, "run", fake_run)

    assert postgen.git_init(tmp_path) is True
    assert [c[0:2] for c in calls] == [["git", "init"], ["git", "add"], ["git", "-c"]]


def test_git_init_failure(tmp_path: Path, monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr=b"fatal: boom")

    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(postgen.subprocess, "run", fake_run)

    assert postgen.git_init(tmp_path) is False
    assert "git init failed" in capsys.readouterr().out


def test_install_dependencies_not_found(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(postgen.shutil, "which", lambda name: None)
    assert postgen.install_dependencies(tmp_path) is False
    assert "uv not found" in capsys.readouterr().out


def test_install_dependencies_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(
        postgen.subprocess, "run", lambda cmd, **kwargs: _FakeCompletedProcess(cmd)
    )
    assert postgen.install_dependencies(tmp_path) is True


def test_install_dependencies_failure(tmp_path: Path, monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr=b"error: boom")

    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(postgen.subprocess, "run", fake_run)

    assert postgen.install_dependencies(tmp_path) is False
    assert "uv sync failed" in capsys.readouterr().out


def test_install_frontend_dependencies_no_package_json(tmp_path: Path):
    # No package.json at all (the common case — most templates don't
    # have a frontend toolchain) is a silent no-op, not a warning.
    assert postgen.install_frontend_dependencies(tmp_path) is False


def test_install_frontend_dependencies_bun_not_found(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(postgen.shutil, "which", lambda name: None)
    assert postgen.install_frontend_dependencies(tmp_path) is False
    assert "bun not found" in capsys.readouterr().out


def test_install_frontend_dependencies_success(tmp_path: Path, monkeypatch):
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/bun")
    monkeypatch.setattr(
        postgen.subprocess, "run", lambda cmd, **kwargs: _FakeCompletedProcess(cmd)
    )
    assert postgen.install_frontend_dependencies(tmp_path) is True


def test_install_frontend_dependencies_failure(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "package.json").write_text("{}")

    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr=b"error: boom")

    monkeypatch.setattr(postgen.shutil, "which", lambda name: "/usr/bin/bun")
    monkeypatch.setattr(postgen.subprocess, "run", fake_run)

    assert postgen.install_frontend_dependencies(tmp_path) is False
    assert "bun install failed" in capsys.readouterr().out


def test_print_summary_frontend_installed_shows_checkmark(capsys):
    postgen.print_summary(
        **_summary_kwargs(
            installed_requested=True,
            created=[Path("package.json")],
            frontend_installed_ok=True,
        )
    )
    out = capsys.readouterr().out
    assert "Installed frontend dependencies (bun install)" in out
    assert "bun install" not in out.split("Next steps:")[1]


def test_print_summary_frontend_not_installed_suggests_bun_install(capsys):
    postgen.print_summary(
        **_summary_kwargs(
            installed_requested=True,
            created=[Path("package.json")],
            frontend_installed_ok=False,
        )
    )
    out = capsys.readouterr().out
    assert "Installed frontend dependencies" not in out
    assert "  bun install" in out


def test_print_summary_dev_py_suggested_as_run_command(capsys):
    postgen.print_summary(**_summary_kwargs(created=[Path("dev.py")]))
    out = capsys.readouterr().out
    assert "uv run dev.py" in out
    assert "uv run fastapi dev" not in out


def test_print_summary_omits_options_line_when_none(capsys):
    postgen.print_summary(**_summary_kwargs(options=None))
    assert "Options:" not in capsys.readouterr().out


def test_print_summary_omits_options_line_when_empty_dict(capsys):
    postgen.print_summary(**_summary_kwargs(options={}))
    assert "Options:" not in capsys.readouterr().out


def test_print_summary_shows_options_line_when_present(capsys):
    postgen.print_summary(**_summary_kwargs(options={"config": True}))
    assert "Options: config=True" in capsys.readouterr().out
