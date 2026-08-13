"""Renders a bundled template into a target project directory.

Templates are organized two levels deep (PRODUCT_ARCH.md §4):
``templates/<framework>/<template>/``, e.g. ``templates/fastapi/hello-world/``.
A framework (``fastapi``) groups one or more templates/variants
(``hello-world``, ``rest-api``, ...); each variant is a complete,
independently renderable project.

Beyond the base file set, a template can declare:

- **options** — extra interactive prompts scoped to that template (e.g.
  rest-api's database/ORM/migrations/worker/redis choices, hello-world's
  optional pydantic-settings config). Each is `select` or `confirm`,
  can depend on an earlier option via `when`, and resolves to
  `skip_value` when its `when` isn't satisfied.
- **layers** — extra directories rendered *in addition to* the base
  `files/` layer, each gated by a `when` predicate evaluated against the
  fully resolved answers (fixed fields + options). This is how
  `--docker` adds a Dockerfile, and how e.g. rest-api's `worker-taskiq`
  layer adds worker code only when that worker was chosen. A later
  layer's file silently overwrites an earlier one at the same relative
  path — that's how e.g. a database layer swaps in a DB-backed
  `routes/items.py` over the base in-memory one.
- **skills** — references (by `id`, each with its own `when`) into a
  *shared* catalog at `src/flint/skills/<id>/`, decoupled from any one
  framework/template so e.g. the `pytest` or `redis` skill isn't
  duplicated across fastapi and flask. Every matched skill is rendered
  into `.agents/skills/<id>/` in the generated project — deeper,
  library-specific reference material (`SKILL.md`, `references/`,
  `guides/`) for exactly the stack that was chosen, alongside a
  generated `.agents/skills/README.md` index. See PRODUCT_ARCH.md §4.5.

Both file/directory *names* and file *contents* are rendered through
Jinja2, generation is all-or-nothing (rolled back on any failure), and
adding a new framework, template, option, layer, or skill is purely a
matter of editing `template.json`/adding files — no changes here.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment
from pydantic import BaseModel

from flint.errors import FlintError, FlintUserError

TEMPLATES_DIR = Path(__file__).parent / "templates"

# A shared catalog of "agent skills" — deeper, library-specific reference
# material (SKILL.md + references/ + guides/) that templates opt into by
# id, same `when`-gating as layers. Lives outside templates/ because a
# skill (e.g. "pytest", "redis") is typically useful to more than one
# framework/template and shouldn't be duplicated per template.
SKILLS_DIR = Path(__file__).parent / "skills"

# Files whose on-disk *source* name can't carry their real target name
# (e.g. a literal leading dot doesn't round-trip cleanly through every
# packaging/sdist tool). Keys/values are post-Jinja-render, pre-suffix-strip
# filenames.
_RENAME_MAP = {
    "gitignore.jinja": ".gitignore",
    "dockerignore.jinja": ".dockerignore",
    "env.jinja": ".env",
    "gitkeep.jinja": ".gitkeep",
}

_JINJA_SUFFIX = ".jinja"
_BASE_LAYER = "files"

# Wherever a template writes a `.env`, it also gets a `.env.example`
# alongside it with identical content — `.env` itself is gitignored (a
# developer's local overrides shouldn't get committed), `.env.example`
# is the checked-in reference of what vars exist. Templates only author
# one `env.jinja`; this mirrors it rather than requiring a second,
# easily-drifting source file.
_ENV_FILE = Path(".env")
_ENV_EXAMPLE_FILE = Path(".env.example")

_env = Environment(keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)


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
    options: dict[str, Any] = {}

    def context(self) -> dict[str, Any]:
        """Fixed fields + template-declared options, flattened into one
        namespace — used both as the Jinja render context and as the
        values `TemplateOption.when`/`TemplateLayer.when` evaluate against."""
        data = self.model_dump(exclude={"options"})
        data.update(self.options)
        return data


@dataclass(frozen=True)
class TemplateOption:
    """One extra interactive prompt a template declares in `template.json`."""

    key: str
    label: str
    type: str  # "select" | "confirm"
    default: Any
    choices: list[dict[str, str]] = field(default_factory=list)
    when: dict[str, list[Any]] = field(default_factory=dict)
    skip_value: Any = None

    @property
    def resolved_skip_value(self) -> Any:
        return self.default if self.skip_value is None else self.skip_value


@dataclass(frozen=True)
class TemplateLayer:
    """An extra directory rendered on top of `files/` when `when` matches."""

    dir: str
    when: dict[str, list[Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillRef:
    """A template's reference to a shared skill (`SKILLS_DIR / id`),
    included in the generated project's `.agents/skills/` when `when`
    matches — same predicate mechanism as `TemplateLayer`."""

    id: str
    when: dict[str, list[Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillMeta:
    """Metadata for one entry in the shared skills catalog, read from
    `SKILLS_DIR / id / skill.json` (mirrors `FrameworkMeta`/`TemplateMeta`
    — a maintainer-facing manifest, not itself rendered into a project)."""

    id: str
    label: str
    description: str
    path: Path


@dataclass(frozen=True)
class FrameworkMeta:
    id: str
    label: str
    description: str
    enabled: bool
    path: Path
    run_command: str = ""


@dataclass(frozen=True)
class TemplateMeta:
    id: str
    label: str
    description: str
    enabled: bool
    path: Path
    framework_id: str
    options: list[TemplateOption] = field(default_factory=list)
    layers: list[TemplateLayer] = field(default_factory=list)
    skills: list[SkillRef] = field(default_factory=list)

    @property
    def full_id(self) -> str:
        return f"{self.framework_id}/{self.id}"

    @property
    def supports_docker(self) -> bool:
        return any(layer.dir == "docker" for layer in self.layers)


def when_matches(when: dict[str, list[Any]], values: dict[str, Any]) -> bool:
    """True if every key in `when` maps to its currently resolved value.

    An empty/absent `when` always matches (no dependency declared).
    """
    return all(values.get(key) in allowed for key, allowed in when.items())


def _read_json(meta_path: Path) -> dict:
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _parse_option(data: dict) -> TemplateOption:
    return TemplateOption(
        key=data["key"],
        label=data["label"],
        type=data["type"],
        default=data.get("default"),
        choices=data.get("choices", []),
        when=data.get("when", {}),
        skip_value=data.get("skip_value"),
    )


def _parse_layer(data: dict) -> TemplateLayer:
    return TemplateLayer(dir=data["dir"], when=data.get("when", {}))


def _parse_skill_ref(data: dict) -> SkillRef:
    return SkillRef(id=data["id"], when=data.get("when", {}))


def get_skill(skill_id: str) -> SkillMeta:
    """Look up one entry in the shared skills catalog (`SKILLS_DIR`).

    Raises `FlintError` (not `FlintUserError`) if `skill_id` has no
    matching directory — an unknown skill id is a bundled-content bug
    (a template referencing a skill that doesn't exist), never something
    the CLI user typed.
    """
    skill_dir = SKILLS_DIR / skill_id
    meta_path = skill_dir / "skill.json"
    if not meta_path.is_file():
        raise FlintError(f"Unknown skill '{skill_id}' referenced by a template.")
    data = _read_json(meta_path)
    return SkillMeta(
        id=data["id"],
        label=data["label"],
        description=data["description"],
        path=skill_dir,
    )


def list_frameworks() -> list[FrameworkMeta]:
    """Return all bundled frameworks, in a stable (sorted by id) order."""
    frameworks = []
    for framework_dir in sorted(TEMPLATES_DIR.iterdir()):
        meta_path = framework_dir / "template.json"
        if meta_path.is_file():
            data = _read_json(meta_path)
            frameworks.append(
                FrameworkMeta(
                    id=data["id"],
                    label=data["label"],
                    description=data["description"],
                    enabled=data.get("enabled", True),
                    path=framework_dir,
                    run_command=data.get("run_command", ""),
                )
            )
    return frameworks


def get_framework(framework_id: str) -> FrameworkMeta:
    framework_dir = TEMPLATES_DIR / framework_id
    meta_path = framework_dir / "template.json"
    if not meta_path.is_file():
        raise FlintUserError(f"Unknown framework '{framework_id}'.")
    data = _read_json(meta_path)
    return FrameworkMeta(
        id=data["id"],
        label=data["label"],
        description=data["description"],
        enabled=data.get("enabled", True),
        path=framework_dir,
        run_command=data.get("run_command", ""),
    )


def list_templates(framework_id: str) -> list[TemplateMeta]:
    """Return all template variants for a framework, in a stable order."""
    framework = get_framework(framework_id)
    templates = []
    for template_dir in sorted(framework.path.iterdir()):
        if not template_dir.is_dir():
            continue
        meta_path = template_dir / "template.json"
        if meta_path.is_file():
            data = _read_json(meta_path)
            templates.append(
                TemplateMeta(
                    id=data["id"],
                    label=data["label"],
                    description=data["description"],
                    enabled=data.get("enabled", True),
                    path=template_dir,
                    framework_id=framework_id,
                    options=[_parse_option(o) for o in data.get("options", [])],
                    layers=[_parse_layer(l) for l in data.get("layers", [])],
                    skills=[_parse_skill_ref(s) for s in data.get("skills", [])],
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

    context = answers.context()
    layer_dirs = [_BASE_LAYER] + [
        layer.dir for layer in template.layers if when_matches(layer.when, context)
    ]
    matched_skills = [
        get_skill(ref.id) for ref in template.skills if when_matches(ref.when, context)
    ]

    created_before = target_dir.exists()
    created: list[Path] = []
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for layer_dir in layer_dirs:
            layer_path = template.path / layer_dir
            if not layer_path.is_dir():
                continue
            created.extend(_render_layer(layer_path, target_dir, context))
        for skill in matched_skills:
            created.extend(_render_skill(skill, target_dir, context))
        if matched_skills:
            created.append(_write_skills_index(target_dir, matched_skills))
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see rollback below
        if not created_before:
            shutil.rmtree(target_dir, ignore_errors=True)
        if isinstance(exc, FlintError):
            raise
        raise FlintError(f"Failed to generate project: {exc}") from exc

    return sorted(set(created))


def _render_layer(layer_root: Path, target_dir: Path, context: dict) -> list[Path]:
    created = []
    for source_path in sorted(layer_root.rglob("*")):
        if source_path.is_dir():
            continue
        rel_source = source_path.relative_to(layer_root)
        rel_target = _render_relative_path(rel_source, context)
        dest_path = target_dir / rel_target
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = _render_content(source_path, context)
        dest_path.write_text(rendered, encoding="utf-8")
        created.append(rel_target)

        if rel_target == _ENV_FILE:
            example_target = rel_target.with_name(_ENV_EXAMPLE_FILE.name)
            (target_dir / example_target).write_text(rendered, encoding="utf-8")
            created.append(example_target)
    return created


_SKILL_CONTENT_DIR = "content"
_SKILLS_INDEX_PATH = Path(".agents", "skills", "README.md")


def _render_skill(skill: SkillMeta, target_dir: Path, context: dict) -> list[Path]:
    """Render one matched skill's `content/` into `.agents/skills/<id>/`.

    `skill.path` is the skill's catalog root (sibling to `skill.json`,
    the maintainer-facing manifest `get_skill` already read) — content
    lives one level down in `content/` precisely so `skill.json` itself
    never gets swept up by `_render_layer`'s `rglob`, the same way a
    template's own `template.json` is never rendered because it sits
    beside `files/`, not inside it.
    """
    content_root = skill.path / _SKILL_CONTENT_DIR
    skill_target = Path(".agents", "skills", skill.id)
    rendered = _render_layer(content_root, target_dir / skill_target, context)
    return [skill_target / rel for rel in rendered]


def _write_skills_index(target_dir: Path, skills: list[SkillMeta]) -> Path:
    """Write `.agents/skills/README.md`, a generated table of contents
    over exactly the skills this project got — so an agent working in
    the project can discover them without listing the directory."""
    lines = [
        "# Agent Skills",
        "",
        "Deeper, library-specific reference material for exactly the stack",
        "this project uses — generated by flint to match the choices made",
        "when it was scaffolded. Each skill's `SKILL.md` explains what it",
        "covers and when to reach for it; `references/` and `guides/` go",
        "deeper on specific APIs and tasks.",
        "",
        "| Skill | What it covers |",
        "| --- | --- |",
    ]
    for skill in sorted(skills, key=lambda s: s.id):
        lines.append(f"| [{skill.label}](./{skill.id}/SKILL.md) | {skill.description} |")
    dest = target_dir / _SKILLS_INDEX_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _SKILLS_INDEX_PATH


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
