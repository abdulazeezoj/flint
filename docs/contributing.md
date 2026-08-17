# Contributing

This page is for working on Brupy itself — the CLI, its bundled
templates, and its skills catalog — not for using Brupy to scaffold a
project. If you just want to generate a project, see
[Getting Started](getting-started.md) instead.

Brupy's own code is intentionally thin: `cli.py` parses flags,
`prompts.py` asks questions, `generator.py` renders Jinja2 templates
onto disk. Almost everything a contributor does day-to-day —
adding a template, adding a skill, tweaking generated output — is a
**content change under `src/brupy/templates/` or `src/brupy/skills/`**,
not a code change — the distinction that keeps most contributions
low-risk.

## Local setup

```bash
git clone https://github.com/abdulazeezoj/brupy
cd brupy
uv sync
```

Run the test suite:

```bash
uv run pytest
```

This also runs coverage, and the suite **fails under 100% branch
coverage** (`--cov=brupy --cov-report=term-missing --cov-fail-under=100`,
with `[tool.coverage.run] branch = true` in `pyproject.toml`) — every
line *and* branch in `src/brupy/` has to be exercised, not just every
function.

!!! tip "Iterating locally"
    Re-running the full coverage gate on every save is slow. Use
    `uv run pytest --no-cov` while you're iterating on a single test or
    template, then run the plain `uv run pytest` once before you open a
    PR.

Confirm the CLI itself works against your checkout:

```bash
uv run brupy --help
```

## Working on the docs site

The docs live in `docs/` and build with MkDocs Material, using a
dependency group kept separate from the dev one — install it before
you serve or build the site:

```bash
uv sync --group docs
```

Serve them locally with live reload:

```bash
uv run mkdocs serve
```

Before opening a docs PR, run the same strict build CI/CD will run —
it turns warnings (broken internal links, missing nav entries) into
hard failures:

```bash
uv run mkdocs build --strict
```

`docs/_product/` (the `PRODUCT_SPEC.md` / `PRODUCT_FLOW.md` /
`PRODUCT_ARCH.md` files this site's own architecture pages are written
from) is deliberately excluded from the built site via `mkdocs.yml`'s
`exclude_docs` — it's internal design material, not user-facing
documentation, so don't link to it from a page in `docs/`.

## Repository layout

The parts of the tree you'll actually touch:

```text
brupy/
├── src/brupy/
│   ├── cli.py               # Typer app — `new` command, flags incl. --option
│   ├── prompts.py            # questionary wizard steps + option resolution
│   ├── naming.py               # project name -> slug/package_name validation
│   ├── generator.py             # template renderer: options, layers, Jinja2
│   ├── postgen.py                 # git init, uv sync, summary printing
│   ├── prefs.py                     # ~/.brupy/last.json — best-effort read/write
│   ├── errors.py                     # BrupyError and friends -> exit codes
│   ├── templates/
│   │   ├── fastapi/
│   │   │   ├── template.json          # framework metadata
│   │   │   ├── hello-world/
│   │   │   │   ├── template.json       # options, layers, skills
│   │   │   │   ├── README.md            # maintainer docs — not rendered
│   │   │   │   ├── files/                 # always rendered
│   │   │   │   ├── docker/                 # rendered iff --docker
│   │   │   │   └── config/                  # rendered iff config option is true
│   │   │   └── rest-api/                     # richer template — more options/layers
│   │   └── flask/                              # same shape, one level up
│   └── skills/                                    # shared .agents/skills/ catalog (§ below)
│       ├── fastapi/
│       │   ├── skill.json                          # {id, label, description} — not rendered
│       │   └── content/
│       │       ├── SKILL.md.jinja
│       │       ├── references/*.md.jinja
│       │       └── guides/*.md.jinja
│       └── pydantic-settings/ sqlmodel/ sqlalchemy/ ...   # same shape
├── tests/
├── docs/                     # this site (+ docs/_product/, excluded from the build)
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

A **framework** directory (`templates/fastapi/`, `templates/flask/`)
has its own `template.json` and one subdirectory per **template**
variant (`hello-world/`, `rest-api/`), each with its own `template.json`.
A future framework can be stubbed the same way FastAPI/Flask were
before they had real content: just a framework-level `template.json`
with `"enabled": false` and no template subdirectories, so the CLI/wizard
lists it as "coming soon" with zero code changes.

## Adding a framework or template

This is a **content-only change** — no edits to `generator.py` or any
other Python module. The generator discovers frameworks, templates,
their options, and their layers entirely by reading `template.json`
files at import time.

The minimal shape is `templates/<framework>/<new-template>/` with a
`template.json` and a `files/` directory (always rendered). See
[`src/brupy/templates/fastapi/hello-world/README.md`](https://github.com/abdulazeezoj/brupy/blob/main/src/brupy/templates/fastapi/hello-world/README.md)
for that minimal layout written out in full, and
[`src/brupy/templates/fastapi/rest-api/template.json`](https://github.com/abdulazeezoj/brupy/blob/main/src/brupy/templates/fastapi/rest-api/template.json)
for the richest real example — six options with `when`/`skip_value`
chains, eight gated layers, and a `skills` list, all in one file.

### The `template.json` schema

A **framework**-level `template.json` (sits beside the template
subdirectories):

```json
{
  "id": "flask",
  "label": "Flask",
  "description": "Flask — a lightweight WSGI web framework.",
  "enabled": true,
  "run_command": "uv run flask --app src/{package_name}/main.py run"
}
```

`run_command` is what lets the generated project's "Next steps" show
the right dev-server command per framework (`str.format`-templated with
`package_name`, resolved after generation — not Jinja2).

A **template**-level `template.json` (sits beside `files/`):

```json
{
  "id": "rest-api",
  "label": "REST API",
  "description": "...",
  "enabled": true,
  "options": [
    {
      "key": "database",
      "label": "Database",
      "type": "select",
      "default": "sqlite",
      "choices": [
        { "value": "none", "label": "None (in-memory store)" },
        { "value": "sqlite", "label": "SQLite" },
        { "value": "postgres", "label": "PostgreSQL" }
      ]
    },
    {
      "key": "orm",
      "label": "ORM",
      "type": "select",
      "default": "sqlmodel",
      "choices": [ /* ... */ ],
      "when": { "database": ["sqlite", "postgres"] },
      "skip_value": "none"
    }
  ],
  "layers": [
    { "dir": "docker", "when": { "docker": [true] } },
    { "dir": "db-sqlmodel", "when": { "orm": ["sqlmodel"] } }
  ],
  "skills": [
    { "id": "fastapi" },
    { "id": "sqlmodel", "when": { "orm": ["sqlmodel"] } }
  ]
}
```

- **`options`** — extra interactive prompts the template declares,
  resolved in the order listed. Each is `type: "select"` (needs a
  `choices` list of `{value, label}`) or `type: "confirm"` (a y/n).
  `when` makes an option depend on an **earlier** option's already-
  resolved value — declaration order matters. When `when` is present
  and doesn't match, the option is never asked (interactive or not) and
  instead silently resolves to `skip_value` (or `default`, if
  `skip_value` is omitted).
- **`layers`** — extra directories rendered *in addition to* the
  always-on `files/` layer, gated by the same `when` predicate,
  evaluated against the fully resolved answers. **A later layer's file
  silently overwrites an earlier one at the same relative path** — this
  is the mechanism `rest-api` uses to swap in a DB-backed
  `routes/items.py` over the plain in-memory one from `files/`, rather
  than sprinkling `{% if %}` through shared code.
- **`skills`** — see [Adding a skill](#adding-a-skill) below.

Jinja2 processes both **file/directory names** and **file contents**
inside any layer:

- A path segment named literally `{{ "{{package_name}}" }}` becomes e.g.
  `my_api`.
- `*.jinja` extensions are stripped after rendering (`main.py.jinja` →
  `main.py`); files without `.jinja` are copied verbatim — used for
  things like `alembic/script.py.mako`, which has its own `${...}`
  syntax and must **not** get a `.jinja` suffix or Jinja will try (and
  fail) to parse it.
- A handful of filenames are explicitly renamed after rendering, since
  dotfiles don't round-trip cleanly as literal source filenames in
  every packaging tool: `gitignore.jinja` → `.gitignore`,
  `dockerignore.jinja` → `.dockerignore`, `env.jinja` → `.env`,
  `gitkeep.jinja` → `.gitkeep`.

!!! tip "Layer vs. inline `{% if %}`"
    Prefer a **layer** when a whole file either exists for a given
    combination of choices or it doesn't — keeps generated *code*
    readable (one clean `routes/items.py`, not four nested `{% if %}`
    blocks). Reach for an inline `{% if %}` only for "gathering" files
    that inherently need to mention several orthogonal choices in one
    place — `pyproject.toml`'s dependency list, `README.md`/`AGENTS.md`,
    `.env`/`core/config.py`.

!!! warning "Jinja whitespace gotcha"
    `generator.py`'s Jinja environment sets `trim_blocks=True,
    lstrip_blocks=True`, so ordinary `{% if %}`/`{% endif %}` blocks on
    their own line behave like a "normal" templating language — don't add
    manual `-` trimming (`{%- if -%}`). After adding a new conditional
    file, actually check the rendered output once (or run the test
    suite, which parses every generated `.py` file with `ast.parse()`
    and every `pyproject.toml` with `tomllib.loads()`) rather than
    trusting it by eye.

Once your template directory and `template.json` exist, no other file
in the codebase needs to change — the CLI and generator discover new
frameworks/templates by reading `template.json`, not by any registry.
Add real coverage to `tests/test_generator.py` (or a new
`tests/test_<framework>_<template>.py`, following the pattern of
`test_flask_hello_world.py`) that renders representative option
combinations.

## Adding a skill

A skill is reference material *about a library* (`.agents/skills/<id>/`
in a generated project), not project content — that's why it lives in
its own flat catalog at `src/brupy/skills/<id>/`, outside `templates/`
entirely, and why several templates can reference the same skill by
`id` instead of each carrying their own copy.

Use `src/brupy/skills/fastapi/` as the reference shape:

```text
skill.json              # {id, label, description} — maintainer metadata, not rendered
content/
  SKILL.md.jinja         # overview, when to use, quick reference, links
  references/*.md.jinja  # deep-dive API/behavior docs
  guides/*.md.jinja      # task-oriented how-tos
```

`skill.json` sits beside `content/`, not inside it, for the same
reason a template's own `template.json` sits beside `files/` — the
renderer walks everything under the directory it's given, so metadata
that shouldn't ship in the generated project has to live outside it.

The same Jinja2 machinery that renders template layers renders
`content/` too, just pointed at `.agents/skills/<id>/` in the generated
project instead of the project root — so a skill's code examples get
real `{{ package_name }}` substitution and can branch on resolved
options with `{% if %}` (the shared `sqlalchemy` skill, for instance,
branches on `framework` to read async-first for FastAPI and sync-first
for Flask, since it's genuinely one library used two different ways).

To make an existing template pull in your new skill, add it to that
template's `template.json`:

```json
"skills": [
  { "id": "fastapi" },
  { "id": "your-skill", "when": { "some_option": ["some_value"] } }
]
```

Same `id`/`when` shape as a layer, evaluated with the same predicate —
a skill with no `when` is always included; one with a `when` is
included only when it matches against the fully resolved answers.
After rendering every matched skill, Brupy also (re)writes a generated
`.agents/skills/README.md` index, sourced from each included skill's
`skill.json` — you don't need to maintain that index by hand.

See [Agent Skills](agent-skills.md) for what this looks like from the
generated-project side.

## Testing philosophy

A green `pytest` run and a generated project that actually boots are
two different claims, and Brupy's test suite is built in layers
precisely because no single layer can make both of them at once.

- **All-or-nothing generation.** `generator.render()` writes a layer at
  a time; if anything raises partway through, everything written so far
  under the target directory is removed before the exception
  propagates — unless the target directory already existed before the
  call (e.g. a `--force` run into a directory you made), in which case
  Brupy never deletes something it didn't create itself. A `0` exit
  code always means a complete, runnable project landed on disk; a
  failed run never leaves a half-generated one behind.
- **100% branch coverage, gated in CI, not just aspirational.**
  `uv run pytest` fails outright if any line or branch in `src/brupy/`
  goes unexercised. This is what makes "content-only" template changes
  safe to merge quickly — the option/layer resolution logic itself is
  fully covered, so a new `template.json` is mostly testing new *data*,
  not new code paths.
- **Rendered output is checked, not just "did it not crash."** Template
  tests render real option combinations into a `tmp_path`, assert the
  exact file set, then run every generated `.py` file through
  `ast.parse()` and every `pyproject.toml` through `tomllib.loads()` —
  catches template bugs (like the whitespace gotcha above) that a
  "render succeeded" check alone would miss.
- **Unit tests are not the whole story — live verification is manual,
  and deliberate.** Before any template change ships, someone actually
  runs the generated output through `uv sync && uv run pytest`, runs
  real Alembic/Flask-Migrate migrations against real SQLite *and* real
  PostgreSQL, boots the generated app plus a real Taskiq/Celery worker
  against real Redis and executes an actual task, and does a
  `docker build`/`docker run` plus a live request. This step has caught
  real bugs that `ast.parse()` and a plain `uv sync` never would — a
  missing top-level `__init__.py` that broke `fastapi dev` while `pytest`
  stayed green, an Alembic `prepend_sys_path` misconfigured for a
  `src/`-layout project, worker CLIs that start cleanly but never
  discover a single task, and a module-level `Flask(__name__)` that
  opened a real database connection the instant a test file merely
  *imported* it. None of those are the kind of bug a coverage number
  will ever tell you about — if you're changing generated code (not
  just Brupy's own logic), budget time to actually run what you
  generated.

## CI/CD

`.github/workflows/ci.yml` runs on every push to `main` and every pull
request: `uv sync --locked` (fails if `uv.lock` has drifted from
`pyproject.toml`), the full `uv run pytest` gate described above, and a
smoke check that the installed console script runs
(`uv run brupy --version`). It runs against a single Python version —
3.11, the floor set by `requires-python` — since Brupy's own code has
no version-specific branches.

`.github/workflows/cd.yml` fires only on pushing a `v*` tag. It has two
jobs:

1. **`test`** — the identical gate CI runs. A tag with a red test suite
   never reaches the next job.
2. **`publish`** — verifies the pushed tag's version matches
   `pyproject.toml`'s `version` (refuses to publish on a mismatch, so a
   manually mistagged commit can't ship under the wrong version), runs
   `uv build`, then publishes via `pypa/gh-action-pypi-publish` using
   PyPI's **Trusted Publishing** (OIDC) — no long-lived API token
   stored as a GitHub secret. The job's `id-token: write` permission and
   its `pypi` environment are what PyPI's registered trusted-publisher
   config keys off of (repo, workflow filename, and environment name all
   have to match).

## Releasing

Cutting a release is three manual steps ending in a `git push`;
everything after that — testing, verifying, publishing — is `cd.yml`'s
job, not yours.

1. Bump `__version__` in `src/brupy/__init__.py` **and** `version` in
   `pyproject.toml` — these are kept in sync manually, there's no
   version-sync tooling yet.
2. Add a `CHANGELOG.md` entry (newest first, linking the version to the
   behavior change).
3. Commit, then tag and push:

   ```bash
   git tag v0.11.0
   git push origin v0.11.0
   ```

Pushing the tag is what triggers `cd.yml` — it re-runs the test suite,
checks the tag matches `pyproject.toml`, and publishes to PyPI. There's
no separate "click publish" step; a green `cd.yml` run *is* the
release.

## Versioning scheme

The three numbers in `v{release}.{feature}.{fixes}` each answer a
different question about what changed:

- **`release`** — the major epoch. Starts at `0` (pre-1.0, still finding
  product shape); bumps when the product's scope or promise materially
  changes.
- **`feature`** — bumps when a release adds new user-facing capability —
  a new framework, a new template, a new option, a new skill.
- **`fixes`** — bumps for patches and bugfixes that add no new
  capability.

A new template or a new skill is a `feature` bump; a bug in an existing
template's generated output is a `fixes` bump.
