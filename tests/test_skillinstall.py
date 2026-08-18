from pathlib import Path

import pytest

from brupy import generator as generator_module
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
    root, written = skillinstall.install("project")

    assert root == tmp_path
    assert Path(".agents/skills/brupy") in written
    assert Path(".claude/skills/brupy") in written
    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()
    link = tmp_path / ".claude/skills/brupy"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / ".agents/skills/brupy").resolve()


def test_install_user_scope(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(skillinstall.Path, "home", lambda: tmp_path)
    root, written = skillinstall.install("user")

    assert root == tmp_path
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
    # The actual os.symlink() call now lives in generator.py's shared
    # write_claude_skill_symlink() helper, not skillinstall.py itself.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        generator_module.os,
        "symlink",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no symlink permission")),
    )

    root, written = skillinstall.install("project")

    assert root == tmp_path
    assert written == [Path(".agents/skills/brupy")]
    assert (tmp_path / ".agents/skills/brupy/SKILL.md").is_file()
    assert not (tmp_path / ".claude/skills/brupy").exists()


def test_install_refuses_when_only_claude_link_conflicts(tmp_path: Path, monkeypatch):
    # `.agents/skills/brupy` doesn't exist yet, but `.claude/skills/brupy`
    # already does (e.g. left over from a different tool) — the error
    # must name the path that's actually in the way, not agents_target.
    monkeypatch.chdir(tmp_path)
    claude_link = tmp_path / ".claude" / "skills" / "brupy"
    claude_link.mkdir(parents=True)

    with pytest.raises(BrupyUserError, match=r"\.claude/skills/brupy.*already exists"):
        skillinstall.install("project")


def test_install_force_replaces_real_directory_at_claude_link(tmp_path: Path, monkeypatch):
    # Regression test: .claude/skills/brupy pre-existing as a real
    # directory (not a symlink) used to crash install() with
    # IsADirectoryError from Path.unlink() even when --force was passed.
    monkeypatch.chdir(tmp_path)
    claude_link = tmp_path / ".claude" / "skills" / "brupy"
    claude_link.mkdir(parents=True)
    (claude_link / "stray.md").write_text("leftover")

    root, written = skillinstall.install("project", force=True)

    assert root == tmp_path
    assert Path(".claude/skills/brupy") in written
    assert claude_link.is_symlink()
    assert claude_link.resolve() == (tmp_path / ".agents/skills/brupy").resolve()
