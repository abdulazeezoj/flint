from pathlib import Path

import pytest

from brupy import skillinstall
from brupy.errors import BrupyUserError


def test_agent_skill_dir_has_real_content():
    # AGENT_SKILL_DIR is the packaged copy install() reads from — this
    # repo's own .agents/skills/brupy/ is a symlink to it (see
    # PRODUCT_ARCH.md §2), so if this is empty the packaged CLI would
    # silently install nothing.
    assert (skillinstall.AGENT_SKILL_DIR / "SKILL.md").is_file()


def test_install_unknown_scope_raises():
    with pytest.raises(BrupyUserError, match="Unknown scope"):
        skillinstall.install("global")


def test_install_project_scope(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    written = skillinstall.install("project")

    assert Path(".agents/skills/brupy") in written
    assert Path(".claude/skills/brupy") in written
    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()
    link = tmp_path / ".claude/skills/brupy"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / ".agents/skills/brupy").resolve()


def test_install_user_scope(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(skillinstall.Path, "home", lambda: tmp_path)
    written = skillinstall.install("user")

    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/brupy").is_symlink()
    assert written == [Path(".agents/skills/brupy"), Path(".claude/skills/brupy")]


def test_install_refuses_existing_without_force(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skillinstall.install("project")

    with pytest.raises(BrupyUserError, match="already exists"):
        skillinstall.install("project")


def test_install_force_overwrites(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skillinstall.install("project")
    stray = tmp_path / ".agents/skills/brupy/stray.md"
    stray.write_text("leftover from a previous install")

    skillinstall.install("project", force=True)

    assert not stray.exists()
    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()


def test_install_skips_claude_symlink_it_cannot_create(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        skillinstall.os,
        "symlink",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no symlink permission")),
    )

    written = skillinstall.install("project")

    assert written == [Path(".agents/skills/brupy")]
    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()
    assert not (tmp_path / ".claude/skills/brupy").exists()
