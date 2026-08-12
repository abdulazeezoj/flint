"""Renders a bundled template directory into a target project directory.

See PRODUCT_ARCH.md §4 for the design this implements: both file/directory
*names* and file *contents* are rendered through Jinja2, generation is
all-or-nothing (rolled back on any failure), and adding a new template is
purely a matter of adding a directory + ``template.json`` — no changes
here.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment
from pydantic import BaseModel

from flint.errors import FlintError, FlintUserError

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Files whose on-disk *source* name can't carry their real target name
# (e.g. a literal leading dot doesn't round-trip cleanly through every
# packaging/sdist tool). Keys/values are post-Jinja-render, pre-suffix-strip
# filenames.
_RENAME_MAP = {
    "gitignore.jinja": ".gitignore",
}

_JINJA_SUFFIX = ".jinja"

_env = Environment(keep_trailing_newline=True)


class Answers(BaseModel):
    """Everything the wizard collected, and everything a template needs."""

    project_name: str
    slug: str
    package_name: str
    framework: str
    git_init: bool
    install: bool


@dataclass(frozen=True)
class TemplateMeta:
    id: str
    label: str
    description: str
    enabled: bool
    path: Path


def list_templates() -> list[TemplateMeta]:
    """Return all bundled templates, in a stable (sorted by id) order."""
    templates = []
    for template_dir in sorted(TEMPLATES_DIR.iterdir()):
        meta_path = template_dir / "template.json"
        if meta_path.is_file():
            templates.append(_load_meta(template_dir, meta_path))
    return templates


def get_template(template_id: str) -> TemplateMeta:
    template_dir = TEMPLATES_DIR / template_id
    meta_path = template_dir / "template.json"
    if not meta_path.is_file():
        raise FlintUserError(f"Unknown template '{template_id}'.")
    return _load_meta(template_dir, meta_path)


def _load_meta(template_dir: Path, meta_path: Path) -> TemplateMeta:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return TemplateMeta(
        id=data["id"],
        label=data["label"],
        description=data["description"],
        enabled=data.get("enabled", True),
        path=template_dir,
    )


def render(template_id: str, target_dir: Path, answers: Answers, force: bool = False) -> list[Path]:
    """Render ``template_id`` into ``target_dir``.

    Returns the list of paths created, relative to ``target_dir``. Raises
    ``FlintUserError`` if the target directory exists and is non-empty
    (unless ``force``), and rolls back everything written on any other
    failure so generation is all-or-nothing.
    """
    template = get_template(template_id)
    if not template.enabled:
        raise FlintUserError(f"Template '{template_id}' is not available yet.")

    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise FlintUserError(
            f"Directory '{target_dir}' already exists and is not empty. "
            "Use --force to generate into it anyway."
        )

    files_root = template.path / "files"
    context = answers.model_dump()

    created_before = target_dir.exists()
    created: list[Path] = []
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_path in sorted(files_root.rglob("*")):
            if source_path.is_dir():
                continue
            rel_source = source_path.relative_to(files_root)
            rel_target = _render_relative_path(rel_source, context)
            dest_path = target_dir / rel_target
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(_render_content(source_path, context), encoding="utf-8")
            created.append(rel_target)
    except FlintError:
        raise
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see rollback below
        if not created_before:
            shutil.rmtree(target_dir, ignore_errors=True)
        raise FlintError(f"Failed to generate project: {exc}") from exc

    return created


def _render_relative_path(rel_source: Path, context: dict) -> Path:
    rendered_parts = [_env.from_string(part).render(**context) for part in rel_source.parts]
    *dir_parts, filename = rendered_parts
    filename = _RENAME_MAP.get(filename, filename)
    if filename.endswith(_JINJA_SUFFIX):
        filename = filename[: -len(_JINJA_SUFFIX)]
    return Path(*dir_parts, filename)


def _render_content(source_path: Path, context: dict) -> str:
    source_text = source_path.read_text(encoding="utf-8")
    if source_path.suffix != _JINJA_SUFFIX:
        return source_text
    return _env.from_string(source_text).render(**context)
