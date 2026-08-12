"""Direct unit tests for postgen.py's subprocess-driving steps.

git_init/install_dependencies are never actually invoked by the CLI tests
(those pass --no-git --no-install, or stub postgen entirely), so they
need their own coverage here. subprocess.run is monkeypatched throughout
to keep this hermetic — no real git/uv/network involved.
"""

import subprocess
from pathlib import Path

from flint import postgen


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
