"""Installs the portable `brupy` agent skill — how to invoke this CLI
to scaffold a project — into a project or the user's home directory,
so a coding agent picks it up without ever having cloned brupy's own
source repo.

The skill's real content ships inside the installed package itself
(`AGENT_SKILL_DIR`, packaged alongside `templates/`/`skills/`); this
repo's own `.agents/skills/brupy/` is a symlink to that same directory
(see PRODUCT_ARCH.md §2), so there's exactly one copy of it whether
you're reading brupy's source or a `pip`/`uv`-installed wheel.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from brupy.errors import BrupyUserError
from brupy.generator import write_claude_skill_symlink

AGENT_SKILL_DIR = Path(__file__).parent / "agent_skill"
_SKILL_ID = "brupy"

_VALID_SCOPES = ("project", "user")


def install(scope: str, force: bool = False) -> tuple[Path, list[Path]]:
    """Copy the bundled `brupy` skill into `<root>/.agents/skills/brupy/`
    and symlink `<root>/.claude/skills/brupy` to it — `<root>` is the
    current directory for ``scope="project"``, the user's home directory
    for ``scope="user"``. Returns `(root, written)`, where `written` is
    the paths written relative to `root` (the `.claude/skills/` symlink
    is best-effort and may be absent from the list on a platform that
    refuses it, same as `generator.py`'s per-project symlinks) — callers
    never need to re-derive `root` themselves.

    Raises `BrupyUserError` for an unknown scope, or if either target
    already exists and `force` isn't set.

    ``Path.cwd()``/``Path.home()`` are resolved here, at call time, not
    cached at import time — tests monkeypatch them per-case, and a
    module-level cache would silently pin the value from whenever this
    module first got imported instead.
    """
    if scope not in _VALID_SCOPES:
        raise BrupyUserError(f"Unknown scope '{scope}' (expected 'project' or 'user').")
    root = Path.cwd() if scope == "project" else Path.home()

    agents_target = root / ".agents" / "skills" / _SKILL_ID
    claude_dir = root / ".claude" / "skills"
    claude_link = claude_dir / _SKILL_ID

    if not force and agents_target.exists():
        raise BrupyUserError(
            f"'{agents_target}' already exists. Use --force to overwrite it."
        )
    if not force and (claude_link.exists() or claude_link.is_symlink()):
        raise BrupyUserError(
            f"'{claude_link}' already exists. Use --force to overwrite it."
        )

    if agents_target.exists():
        shutil.rmtree(agents_target)
    agents_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(AGENT_SKILL_DIR, agents_target)
    written = [agents_target.relative_to(root)]

    try:
        write_claude_skill_symlink(claude_dir, _SKILL_ID)
        written.append(claude_link.relative_to(root))
    except OSError:
        pass

    return root, written
