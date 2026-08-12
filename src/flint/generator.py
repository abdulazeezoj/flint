"""Renders a bundled template into a target project directory.

Templates are organized two levels deep (PRODUCT_ARCH.md §4):
``templates/<framework>/<template>/``, e.g. ``templates/fastapi/hello-world/``.
A framework (``fastapi``) groups one or more templates/variants
(``hello-world``, ``restapi``, ``ai``, ...); each variant is a complete,
independently renderable project.

Both file/directory *names* and file *contents* are rendered through
Jinja2, generation is all-or-nothing (rolled back on any failure), and
adding a new framework or template is purely a matter of adding a
directory + ``template.json`` — no changes here.
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
    "dockerignore.jinja": ".dockerignore",
}

_JINJA_SUFFIX = ".jinja"

# The base file set every template renders. An optional "docker" layer is
# added on top when Answers.docker is set and the template supports it.
_BASE_LAYER = "files"
_DOCKER_LAYER = "docker"

_env = Environment(keep_trailing_newline=True)


class Answers(BaseModel):
    """Everything the wizard collected, and everything a template needs."""

    project_name: str
    slug: str
    package_name: str
    framework: str
    template: str
    git_init: bool
    install: bool
    docker: bool


@dataclass(frozen=True)
class FrameworkMeta:
    id: str
    label: str
    description: str
    enabled: bool
    path: Path


@dataclass(frozen=True)
class TemplateMeta:
    id: str
    label: str
    description: str
    enabled: bool
    path: Path
    framework_id: str

    @property
    def full_id(self) -> str:
        return f"{self.framework_id}/{self.id}"

    @property
    def supports_docker(self) -> bool:
        return (self.path / _DOCKER_LAYER).is_dir()


def _load_meta_fields(meta_path: Path) -> dict:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "id": data["id"],
        "label": data["label"],
        "description": data["description"],
        "enabled": data.get("enabled", True),
    }


def list_frameworks() -> list[FrameworkMeta]:
    """Return all bundled frameworks, in a stable (sorted by id) order."""
    frameworks = []
    for framework_dir in sorted(TEMPLATES_DIR.iterdir()):
        meta_path = framework_dir / "template.json"
        if meta_path.is_file():
            frameworks.append(FrameworkMeta(path=framework_dir, **_load_meta_fields(meta_path)))
    return frameworks


def get_framework(framework_id: str) -> FrameworkMeta:
    framework_dir = TEMPLATES_DIR / framework_id
    meta_path = framework_dir / "template.json"
    if not meta_path.is_file():
        raise FlintUserError(f"Unknown framework '{framework_id}'.")
    return FrameworkMeta(path=framework_dir, **_load_meta_fields(meta_path))


def list_templates(framework_id: str) -> list[TemplateMeta]:
    """Return all template variants for a framework, in a stable order."""
    framework = get_framework(framework_id)
    templates = []
    for template_dir in sorted(framework.path.iterdir()):
        if not template_dir.is_dir():
            continue
        meta_path = template_dir / "template.json"
        if meta_path.is_file():
            templates.append(
                TemplateMeta(
                    path=template_dir,
                    framework_id=framework_id,
                    **_load_meta_fields(meta_path),
                )
            )
    return templates


def get_template(framework_id: str, template_id: str) -> TemplateMeta:
    for template in list_templates(framework_id):
        if template.id == template_id:
            return template
    raise FlintUserError(f"Unknown template '{template_id}' for framework '{framework_id}'.")


def render(
    framework_id: str,
    template_id: str,
    target_dir: Path,
    answers: Answers,
    force: bool = False,
) -> list[Path]:
    """Render ``<framework_id>/<template_id>`` into ``target_dir``.

    Returns the list of paths created, relative to ``target_dir``. Raises
    ``FlintUserError`` if either the framework/template is disabled or the
    target directory exists and is non-empty (unless ``force``), and rolls
    back everything written on any other failure so generation is
    all-or-nothing.
    """
    framework = get_framework(framework_id)
    if not framework.enabled:
        raise FlintUserError(f"Framework '{framework_id}' is not available yet.")

    template = get_template(framework_id, template_id)
    if not template.enabled:
        raise FlintUserError(f"Template '{template.full_id}' is not available yet.")

    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise FlintUserError(
            f"Directory '{target_dir}' already exists and is not empty. "
            "Use --force to generate into it anyway."
        )

    context = answers.model_dump()
    layers = [_BASE_LAYER]
    if answers.docker and template.supports_docker:
        layers.append(_DOCKER_LAYER)

    created_before = target_dir.exists()
    created: list[Path] = []
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for layer in layers:
            created.extend(_render_layer(template.path / layer, target_dir, context))
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see rollback below
        if not created_before:
            shutil.rmtree(target_dir, ignore_errors=True)
        if isinstance(exc, FlintError):
            raise
        raise FlintError(f"Failed to generate project: {exc}") from exc

    return sorted(created)


def _render_layer(layer_root: Path, target_dir: Path, context: dict) -> list[Path]:
    created = []
    for source_path in sorted(layer_root.rglob("*")):
        if source_path.is_dir():
            continue
        rel_source = source_path.relative_to(layer_root)
        rel_target = _render_relative_path(rel_source, context)
        dest_path = target_dir / rel_target
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(_render_content(source_path, context), encoding="utf-8")
        created.append(rel_target)
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
