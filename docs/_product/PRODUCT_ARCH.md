# Flint — Architecture

**Status:** Draft for v0
**Owner:** Engineering
**Last updated:** 2026-08-15 (v0.17.1: repo layout tree updated for `.agents/skills/flint/` + `.claude/skills/flint` symlink — see §3)

Implements `PRODUCT_SPEC.md` / `PRODUCT_FLOW.md`. This is the technical
design for the `flint` CLI itself (not the projects it generates).

## 1. Tech stack

| Concern | Choice | Why |
|---|---|---|
| CLI framework | [Typer](https://typer.tiangolo.com/) | Type-hint-driven, generates `--help`, minimal boilerplate, built on Click (battle-tested arg parsing). |
| Interactive prompts | [questionary](https://github.com/tmbo/questionary) | Arrow-key select lists and confirm prompts that read like `create-next-app`; degrades cleanly, easy to script around in tests. |
| Terminal output | [rich](https://github.com/Textualize/rich) | Colored summaries, spinners for `uv sync` / `git init`, tables — Typer already depends on it. |
| Templating | [Jinja2](https://jinja.palletsprojects.com/) | Renders both file contents and file/directory *names* (`{{package_name}}`), industry-standard, no need for a full scaffolding framework (cookiecutter/copier) when Flint owns its own bundled templates. |
| Packaging / env | [uv](https://docs.astral.sh/uv/) | Both: (a) how Flint itself is built/packaged/tested, and (b) the package manager wired into every generated project. |
| Testing | pytest + Typer's `CliRunner` | Standard, integrates with `uv run pytest`. |

No cookiecutter/copier dependency: templates ship bundled in the package.
Pulling in a full templating framework for a handful of templates is
unnecessary weight; the template *system* (§4) is still designed so that
swapping in cookiecutter/copier — or a remote template registry — later
is a contained change, not a rewrite.

## 2. Distribution

- PyPI distribution name: `flint-kit` — plain `flint` is an unrelated,
  already-published package, so `pyproject.toml`'s `[project] name` and
  the console script diverge on purpose (see PRODUCT_SPEC §10/§11 for
  why). `[tool.uv.build-backend] module-name` and every `[project.scripts]`
  entry stay `flint`; only the PyPI-facing string carries the suffix.
- Console script entry point: `flint`.
- Primary usage is via `uvx --from flint-kit flint` (ephemeral run, no install) or
  `uv tool install flint-kit` (persistent `flint` on PATH) — mirrors how
  `npx create-next-app` is normally invoked.
- Build backend: `hatchling` via `uv`'s default `uv init --package`
  project shape (src layout).

## 3. Repository layout

```
flint/
├── .agents/
│   └── skills/
│       └── flint/                  # portable agent skill teaching an agent how to *use*
│           │                       # the flint CLI itself — unrelated to SKILLS_DIR (§4.5),
│           │                       # which flint bundles *into generated projects*
│           ├── SKILL.md
│           └── references/
│               ├── cli-reference.md
│               └── templates.md
├── .claude/
│   └── skills/
│       └── flint -> ../../.agents/skills/flint   # symlink, for Claude Code's own
│                                                   # discovery path (repo-relative)
├── .github/
│   └── workflows/
│       ├── ci.yml                  # tests, every push/PR to main
│       ├── cd.yml                  # PyPI publish, on a v* tag push
│       └── docs.yml                # docs site build + GitHub Pages deploy — see §8
├── mkdocs.yml                      # docs site config (Material theme) — see §4.6
├── docs/
│   ├── _product/                   # THIS document set — internal, excluded from the
│   │   │                           # built docs site (mkdocs.yml's exclude_docs)
│   │   ├── PRODUCT_SPEC.md
│   │   ├── PRODUCT_FLOW.md
│   │   └── PRODUCT_ARCH.md
│   ├── index.md                    # docs site home page
│   ├── getting-started.md
│   ├── cli-reference.md
│   ├── agent-skills.md
│   ├── preferences.md
│   ├── contributing.md
│   └── project-templates/          # NOT docs/templates/ — MkDocs hardcodes a default
│       │                           # exclusion for a root-level templates/ dir (reserved
│       │                           # for theme customization), so this had to be renamed
│       ├── index.md
│       ├── fastapi-hello-world.md
│       ├── fastapi-rest-api.md
│       ├── fastapi-full-stack.md
│       ├── flask-hello-world.md
│       ├── flask-rest-api.md
│       └── flask-full-stack.md
├── src/
│   └── flint/
│       ├── __init__.py          # __version__
│       ├── __main__.py          # `python -m flint`
│       ├── cli.py               # Typer app, `new` command, flags incl. --option
│       ├── prompts.py           # questionary wizard steps + option resolution
│       ├── naming.py            # project name -> slug/package_name validation
│       ├── generator.py         # template renderer: options, layers, Jinja2
│       ├── postgen.py           # git init, uv sync, summary printing
│       ├── prefs.py             # ~/.flint/last.json — best-effort read/write
│       ├── errors.py            # FlintError and friends -> exit codes
│       └── templates/
│           ├── fastapi/
│           │   ├── template.json                  # framework metadata
│           │   ├── hello-world/
│           │   │   ├── template.json               # options: [config]; layers: [docker, config]
│           │   │   ├── README.md                   # maintainer docs (not rendered)
│           │   │   ├── files/                      # always rendered
│           │   │   ├── docker/                     # rendered iff --docker
│           │   │   └── config/                     # rendered iff config option is true
│           │   └── rest-api/
│           │       ├── template.json               # options: [database, orm, migrations, worker, broker, redis]
│           │       ├── files/                       # always rendered — main.py, core/config.py, schemas.py, routes/items.py (in-memory), env.jinja (-> .env + .env.example)
│           │       ├── docker/                       # rendered iff --docker
│           │       ├── db-sqlmodel/                   # rendered iff orm == sqlmodel; overrides routes/items.py, adds core/db.py + models.py
│           │       ├── db-sqlalchemy/                 # rendered iff orm == sqlalchemy; same shape, SQLAlchemy Core/ORM
│           │       ├── migrations-sqlmodel/            # rendered iff migrations && orm == sqlmodel
│           │       ├── migrations-sqlalchemy/          # rendered iff migrations && orm == sqlalchemy
│           │       ├── worker-taskiq/                   # rendered iff worker == taskiq; worker.py (broker-aware) + tasks/example.py
│           │       ├── worker-celery/                   # rendered iff worker == celery; same shape, Celery, same broker-awareness
│           │       └── redis/                            # rendered iff redis is true (requested, or implied when broker == "redis"); core/redis.py
│           └── flask/
│               ├── template.json                  # framework metadata
│               ├── hello-world/                    # same shape as fastapi/hello-world, on a WSGI Flask(__name__) app
│               └── rest-api/                       # sync counterpart to fastapi/rest-api — application-factory (create_app()), Celery-only (no Taskiq: async-first, doesn't fit WSGI)
│                   ├── template.json               # options: [database, orm, migrations, worker, broker, redis]
│                   ├── files/                       # main.py (create_app factory), core/config.py, schemas.py, routes/items.py (in-memory), env.jinja (-> .env + .env.example)
│                   ├── docker/                       # rendered iff --docker
│                   ├── db-flask-sqlalchemy/           # rendered iff orm == flask-sqlalchemy; overrides routes/items.py, adds core/db.py + models.py
│                   ├── db-sqlalchemy/                 # rendered iff orm == sqlalchemy; same shape, manual SQLAlchemy Core/ORM
│                   ├── migrations-flask-sqlalchemy/    # rendered iff migrations && orm == flask-sqlalchemy; Flask-Migrate (needs a Flask-SQLAlchemy db object)
│                   ├── migrations-sqlalchemy/          # rendered iff migrations && orm == sqlalchemy; bare Alembic
│                   ├── worker-celery/                   # rendered iff worker == celery; worker.py + tasks/example.py
│                   └── redis/                            # rendered iff redis is true; core/redis.py
│       └── skills/                                 # shared "agent skills" catalog — see §4.5
│           ├── fastapi/
│           │   ├── skill.json                      # {id, label, description} — not rendered
│           │   └── content/                         # rendered into .agents/skills/fastapi/
│           │       ├── SKILL.md.jinja
│           │       ├── references/*.md.jinja
│           │       └── guides/*.md.jinja
│           ├── flask/ pydantic-settings/ sqlmodel/ sqlalchemy/
│           │   flask-sqlalchemy/ alembic/ flask-migrate/ taskiq/
│           │   celery/ redis/ pytest/                # same shape as fastapi/ above
├── tests/
│   ├── conftest.py               # autouse fixture: isolates prefs.PREFS_DIR/FILE per test
│   ├── test_naming.py
│   ├── test_generator.py
│   ├── test_flask_hello_world.py
│   ├── test_flask_rest_api.py
│   ├── test_flask_full_stack.py
│   ├── test_prompts.py
│   ├── test_cli.py
│   ├── test_postgen.py
│   ├── test_prefs.py
│   └── test_main.py
├── pyproject.toml
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## 4. Template system design

Templates are organized two levels deep: `templates/<framework>/<template>/`
(PRODUCT_SPEC §3 defines the framework/template/option distinction). A
**framework** directory (`templates/fastapi/`, `templates/flask/`) has
its own `template.json` and one subdirectory per **template** variant
(`hello-world/`, `rest-api/`), each with its own `template.json`. Both
shipped frameworks are enabled as of v0.8. Any future framework ships
the same way FastAPI/Flask did before their content existed: a stub —
just a framework-level `template.json` with `"enabled": false`, no
template subdirectories — that exists purely so the wizard/CLI can list
it as "coming soon" (PRODUCT_FLOW §2 step 3) without any code changes,
until it's filled in and flipped to `"enabled": true`.

### Framework `template.json` schema

```json
{
  "id": "flask",
  "label": "Flask",
  "description": "Flask — a lightweight WSGI web framework.",
  "enabled": true,
  "run_command": "uv run flask --app src/{package_name}/main.py run"
}
```

- **`run_command`** — the dev-server command shown on the generated
  project's "Next steps" line (PRODUCT_FLOW §5 step 11), templated with
  plain `str.format(package_name=...)` (not Jinja — it's resolved in
  `cli.py` after generation, not during rendering). This is what lets
  `postgen.print_summary` show the right command per framework instead
  of assuming FastAPI's `fastapi dev`; `FrameworkMeta.run_command`
  defaults to `""` for forward-compatibility with a disabled stub that
  hasn't declared one yet.

### Template `template.json` schema

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
  ]
}
```

- **`options`** (optional, template-scoped) — extra interactive prompts
  the template declares, resolved by `prompts.prompt_template_options`
  (§6) in the order listed. Each is `type: "select"` (needs `choices`,
  a list of `{value, label}`) or `type: "confirm"` (a y/n). `when` makes
  an option depend on an **earlier** option's resolved value — declaration
  order matters, since a `when` can only see already-resolved keys.
  When `when` is present and doesn't match, the option is never asked
  (interactive or not) and instead resolves to `skip_value` (falling
  back to `default` if `skip_value` is omitted). This is how rest-api's
  `orm`/`migrations` collapse to `"none"`/`false` when no database was
  chosen, and how `redis` resolves to `true` — implied, not asked — the
  moment `broker` resolves to `"redis"` (its `when` is `{"broker":
  ["rabbitmq", "none"]}`; `broker` itself resolving to `"redis"` means
  that `when` doesn't match, triggering `skip_value: true`). §4.1 works
  through this exact chain in full, including why it's gated on `broker`
  rather than `worker`. `generator.when_matches(when, values)` implements
  the predicate itself,
  shared between option resolution and layer gating below — an empty/
  absent `when` always matches.
- **`layers`** (optional) — extra directories rendered *in addition to*
  the always-on `files/` layer, each gated by the same `when` predicate,
  evaluated against the *fully resolved* answers (fixed fields like
  `docker`/`git_init` merged with the template's own resolved options —
  see `Answers.context()`). This is how `--docker` adds a Dockerfile
  (`{"dir": "docker", "when": {"docker": [true]}}` — no code path is
  hardcoded to "docker" anymore, it's just data) and how e.g. rest-api's
  `worker-taskiq` layer adds worker code only when that worker was
  chosen. **A later layer's file silently overwrites an earlier one at
  the same relative path** — that's the mechanism rest-api uses to swap
  in a DB-backed `routes/items.py`/`main.py` over the base in-memory
  ones, rather than sprinkling `{% if %}` through shared code files (see
  §4.2). `TemplateMeta.supports_docker` is derived, not stored — `any(
  layer.dir == "docker" for layer in template.layers)`.
- `README.md` (optional) — maintainer-facing docs for the template
  itself; lives at the template root (sibling to `files/`), so it is
  **not** picked up by the renderer (only declared layer directories are
  rendered) and never ships in a generated project.

Within any layer, both **file/directory names** and **file contents**
are run through Jinja2 (`trim_blocks=True, lstrip_blocks=True` — see the
whitespace-control note in §4.3):
- A path segment literally named `{{package_name}}` becomes e.g.
  `my_api`.
- `*.jinja` file extensions are stripped after rendering
  (`main.py.jinja` → `main.py`); files without `.jinja` are copied
  verbatim — e.g. `alembic/script.py.mako`, which uses Mako's own
  `${...}` syntax and must **not** get a `.jinja` suffix or Jinja would
  try (and fail) to parse it.
- `gitignore.jinja` renders to `.gitignore`, `dockerignore.jinja` to
  `.dockerignore`, `env.jinja` to `.env`, `gitkeep.jinja` to `.gitkeep`
  — an explicit rename table in `generator.py` (`_RENAME_MAP`)
  sidesteps packaging tools that mishandle literal leading-dot filenames
  in source control / sdists.

Render context (the "answers" passed to every template) — `Answers.
context()` flattens the fixed fields and the template's resolved
`options` dict into one namespace, so templates reference e.g.
`{{ database }}` directly rather than `{{ options.database }}`:

```python
class Answers(BaseModel):
    project_name: str      # raw user input, "My Api"
    slug: str               # "my-api" — directory / distribution name
    package_name: str       # "my_api" — importable package name
    framework: str          # "fastapi"
    template: str            # "rest-api"
    git_init: bool
    install: bool
    docker: bool
    options: dict[str, Any]  # e.g. {"database": "sqlite", "orm": "sqlmodel", ...}
```

`generator.render(framework_id, template_id, target_dir, answers, force=False)`:
1. Resolve the framework, then the template within it; verify both
   `enabled`.
2. Refuse if `target_dir` exists and is non-empty, unless `force=True`.
3. Build the layer list: `["files"]` + every declared layer whose `when`
   matches `answers.context()`.
4. For each layer (in order), walk its directory (`rglob`, deterministic
   sorted order); for each file, render the *path itself* through
   Jinja2, render *contents* through Jinja2, write to `target_dir` —
   later layers overwrite earlier layers' files at the same path.
5. On any exception: remove everything written so far under `target_dir`
   before re-raising, unless `target_dir` already existed before this
   call (e.g. a `--force` run into a directory the user made) — never
   delete something Flint didn't create. All-or-nothing generation, per
   PRODUCT_FLOW §5.
6. Return the deduplicated, sorted list of created paths (used for the
   CLI summary; `postgen.print_summary` checks for `Path("Dockerfile")`
   in it to decide whether to print Docker next-steps).

This keeps "add a new template" to: add a directory + `template.json`
(+ optional layer directories), no changes to `generator.py`. Adding a
new *framework* is the same, one level up — Flask shipped this way in
v0.8: fill in `hello-world/`/`rest-api/` content, set a `run_command`,
flip `enabled: false` → `true`, no architecture change.

### 4.1 A worked example: rest-api's `broker`/`redis` options

Four moving pieces, all data-driven, and a chain that's worth tracing in
full since it's the least obvious `when`/`skip_value` interaction in the
codebase:

1. `template.json`'s `broker` option: `"when": {"worker": ["taskiq",
   "celery"]}, "skip_value": "none"`. Read as: *ask which broker only if
   a worker was chosen; with no worker there's nothing to broker,
   resolve to `"none"` without asking.*
2. `template.json`'s `redis` option: `"when": {"broker": ["rabbitmq",
   "none"]}, "skip_value": true`. Read as: *ask about Redis (for
   caching) whenever the broker is **not** `"redis"` — i.e. either no
   worker was chosen (`broker` resolved to `"none"`) or RabbitMQ was
   picked. The moment `broker` resolves to `"redis"`, a Redis instance
   is already needed for the worker, so the caching question is skipped
   and implied `true`.* This is deliberately **not** `"when": {"worker":
   ["none"]}` (the v0.3–v0.6 shape) — that older rule conflated "a
   worker was chosen" with "the worker uses Redis," which broke the
   moment RabbitMQ became a second broker choice: picking RabbitMQ would
   have silently implied Redis too, for no reason. Gating on `broker`
   instead of `worker` is what lets `redis` mean exactly one thing:
   *is there a Redis instance this app can reach*, however that came to
   be true.
3. `template.json`'s `redis` **layer**: `{"dir": "redis", "when":
   {"redis": [true]}}` — unchanged by the above. Once the `redis` option
   resolves (asked or implied), the layer gate just checks the final
   value; it doesn't care *why* `redis` ended up `true`.
4. `redis/src/{{package_name}}/core/redis.py.jinja` — the one new file
   that layer adds (an async Redis client). It doesn't touch `main.py`,
   deliberately, so it can't conflict with the `worker-*` layers, which
   *do* override `main.py` (to add lifespan wiring and a demo
   task-enqueue endpoint). There's no equivalent `broker-rabbitmq/`
   layer/client — RabbitMQ has no app-level use the way Redis does for
   caching, it's purely internal to `worker.py` (`taskiq-aio-pika` /
   Celery's built-in AMQP transport), so the RabbitMQ-specific content
   is just a few `{% if broker == "rabbitmq" %}` branches inside
   `worker.py.jinja`/`config.py.jinja`/`env.jinja`/`pyproject.toml.jinja`
   — not enough surface to justify a layer.

One consequence worth naming: because `redis` and `broker` are
independent options, an explicit `-o broker=redis -o redis=false` is a
legal (if self-contradictory) combination — explicit `--option` values
always win over `when`/`skip_value` resolution, per option, with no
cross-option consistency check. Any future layer/content that assumes
"broker == redis implies a Redis instance exists" needs to check the
resolved `redis` value directly rather than inferring it from `broker`.

### 4.2 When to use a layer vs. an inline `{% if %}`

Two mechanisms exist for conditional content; picking the wrong one for
a given file makes templates harder to maintain:

- **Layers** (preferred for code): a whole file either exists for a
  given combination of choices or it doesn't. `db-sqlmodel/` and
  `db-sqlalchemy/` each ship their own complete `routes/items.py` and
  `core/db.py` — no shared file has ORM-specific branches in it. Keeps
  generated *code* readable (a developer opens `routes/items.py` and
  sees one clean implementation, not four nested `{% if %}` blocks).
- **Inline `{% if %}`** (acceptable for "gathering" files): some files
  inherently need to mention *multiple* orthogonal choices in one place
  — `pyproject.toml` (the dependency list touches orm/database/
  migrations/worker/redis all at once), `README.md`/`AGENTS.md` (one
  coherent narrative document), `.env`/`core/config.py` (all configured
  values in one place). Decomposing these into layers would need a
  "merge multiple layers' contributions into one file" mechanism Flint
  doesn't have (and isn't worth building for a handful of files) — a
  short, well-organized conditional block is the pragmatic choice here.
  `main.py` is a deliberate, documented exception: worker/database both
  need to touch its startup wiring, so it stays inline-conditional
  rather than needing a `db+worker`-combinatorial set of layer overrides.

### 4.3 Whitespace control gotcha (Jinja `trim_blocks`/`lstrip_blocks`)

`generator._env` sets `trim_blocks=True, lstrip_blocks=True`. Without
these, every `{% if %}`/`{% endif %}` on its own line leaves a stray
blank line in the rendered output unless every tag is manually
suffixed/prefixed with `-` (`{%- if ... -%}`) — tedious and easy to get
wrong (an early version of `main.py.jinja` had a missing blank line
between import groups and PEP8-violating single blank lines before
`def`s from exactly this). With `trim_blocks`/`lstrip_blocks` on,
ordinary `{% if %}` blocks behave like a "normal" templating language —
write templates with **no** manual `-` trimming and check the rendered
output once per new conditional file (`ast.parse()` for `.py`, `tomllib.
loads()` for `.toml` — see `test_generator.py`'s `_assert_all_python_
files_parse`/`_assert_valid_toml` helpers) rather than trusting it by
eye.

### 4.4 The generated *project's* layout is opinionated too — Next.js-style

Everything above is about how flint's *own* code decides what to
render. This section is about the shape of what gets rendered — the
layout a developer (or a coding agent extending the scaffold) actually
sees inside `rest-api`'s `src/{{package_name}}/`.

The model is Next.js's own rule, taken literally rather than loosely:
**only routing is magic and strictly located; everything else is
convention, not enforcement.** Next doesn't mandate `lib/`/`components/`
— people converge on those because *routing* has one unambiguous home
(`app/`/`pages/`) and nothing else competes for that kind of certainty.
Applied here:

- **Strictly opinionated** (flint always uses this exact name/location,
  and every generated project agrees):
  - `main.py` — the FastAPI entrypoint. Never renamed, never moved.
  - `worker.py` — the worker entrypoint (present only when a worker is
    chosen). Same rule.
  - `routes/` — one module per HTTP resource. This is the "app/" of
    this layout: the one place with real, load-bearing significance
    (routers get individually imported and mounted in `main.py`).
  - `tasks/` — one module per background job, mirroring `routes/`.
  - `core/` — shared infrastructure every route/task might reasonably
    depend on: `config.py` (always), `db.py` (async engine/session, iff
    a database is chosen), `redis.py` (iff redis resolves true). A
    hypothetical future `schedules.py` (periodic job registration) would
    live here too — the folder's job is "cross-cutting plumbing," not
    "everything that isn't a route."
- **A default, not a rule** — flint picks *something* reasonable so the
  project isn't missing a home for these, but doesn't treat it as fixed
  the way the above is: `schemas.py` (Pydantic contracts) and
  `models.py` (ORM models, iff a database is chosen) stay single
  top-level files for now, because rest-api only ships one resource.
  Both are natural candidates to become `schemas/`/`models/` folders —
  mirroring `routes/`/`tasks/` — the moment a generated project grows a
  second resource, but flint doesn't make that call for the user.

Why `models.py` (and `db.py`'s session/engine setup) is **not** under
`core/`, despite both starting life under `db/` before this design: the
prior FastAPI-scaffolding research (`PRODUCT_ARCH.md`'s v0.2 research
pass, and independently `zhanymkanov/fastapi-best-practices`) draws the
same line — `core/` is config + cross-cutting infrastructure,
`models/`/`schemas/` are domain content that scale with resource count.
Putting `Item` inside `core/` would mean every future resource's model
also lands in the one folder meant to stay small and stable — exactly
the ambiguity this layout exists to avoid.

`hello-world`'s optional `config` option follows the same convention for
consistency (`core/config.py`, not top-level `config.py`) even though a
one-endpoint template doesn't need the rest of the `core/`/`routes/`/
`tasks/` structure — a developer who's used one flint template shouldn't
have to relearn where config lives in another.

### 4.5 `.agents/skills/` — a shared, opt-in skills catalog

Every generated project ships `AGENTS.md` (always-on, lightweight —
run/test commands, layout, conventions). As of v0.9, richer,
library-specific reference material is available too: `.agents/skills/
<id>/` — a `SKILL.md`, `references/*.md`, and `guides/*.md` per
library, copied in *only* for the libraries a given project actually
ended up using. AGENTS.md's own "Agent skills" section points at
whichever of these actually apply.

**Why a separate catalog, not more template layers.** A layer
(`db-sqlmodel`, `worker-taskiq`, ...) is *project content* — it's
rendered as part of the app itself and is naturally scoped to one
template. A skill is *reference material about a library*, and several
libraries (`pytest`, `redis`, `sqlalchemy`, `pydantic-settings`,
`alembic`, `celery`) are used identically-in-spirit by more than one
template. Modeling skills as template-scoped layers would mean either
duplicating that content across `fastapi/rest-api` and `flask/rest-api`
(drifts the moment one copy gets a fix the other doesn't), or
cross-linking between layer trees (fragile, nothing else in the
template system does this). Instead, the catalog lives once, flat, at
`src/flint/skills/<id>/` — outside `templates/` entirely — and each
template's `template.json` references catalog entries by `id`.

**Schema**, `skills` inside a template's `template.json`:

```json
"skills": [
  { "id": "fastapi" },
  { "id": "pydantic-settings" },
  { "id": "sqlmodel", "when": { "orm": ["sqlmodel"] } },
  { "id": "alembic", "when": { "migrations": [true] } }
]
```

Same `id`/`when` shape as a `TemplateLayer`, evaluated with the exact
same `when_matches(when, context)` predicate against the fully resolved
answers — a skill with an empty/absent `when` is always included; one
with a `when` is included only when it matches, exactly like a layer.

**Catalog entry shape**, `src/flint/skills/<id>/`:

```
skill.json              # {id, label, description} — maintainer metadata,
                         # never itself rendered (mirrors template.json
                         # sitting beside files/, not inside it)
content/
  SKILL.md.jinja         # overview, when to use, quick reference, links
  references/*.md.jinja  # deep-dive API/behavior docs
  guides/*.md.jinja      # task-oriented how-tos
```

`content/` exists specifically so `_render_layer`'s `rglob` (which walks
everything under the directory it's given) never sees `skill.json` —
the same reason a template's own `template.json` sits beside `files/`
rather than inside it. Every matched skill's `content/` is rendered
into `.agents/skills/<id>/` in the generated project via the *same*
`_render_layer` helper templates already use, just pointed at a
different source root and a `.agents/skills/<id>/` destination instead
of the project root — no new rendering logic, no new Jinja semantics.
Because it's the same renderer, skill content gets the same
`{{ package_name }}` substitution and `{% if %}` conditionals real
template files do — a skill's code examples show the actual import
paths a given generated project will have, and can branch on resolved
options the same way `README.md.jinja` does (e.g. the shared
`sqlalchemy` skill branches on `framework` to read async-first for a
FastAPI project and sync-first for a Flask one, since it's genuinely
one library used two different ways here).

After rendering every matched skill, `render()` also writes a generated
`.agents/skills/README.md` — a table of exactly the skills present with
their one-line descriptions, sourced from each `skill.json`. Not
authored content, just an index over what actually got included, since
`git status`/directory-listing is a worse way to discover "what skills
does this project have."

**Bootstrapping**: the `fastapi` skill was hand-built first and used to
validate the whole mechanism end-to-end (rendering, substitution,
when-gating, the generated index) before the remaining ten
(`flask`, `pydantic-settings`, `sqlmodel`, `sqlalchemy`,
`flask-sqlalchemy`, `alembic`, `flask-migrate`, `taskiq`, `celery`,
`redis`, `pytest`) were authored — each grounded directly in the real
template source it documents, and each folding in the real gotchas
already recorded in §7.1 below wherever relevant (task-discovery for
taskiq/celery, `create_all()`-vs-migrations for alembic/flask-migrate/
flask-sqlalchemy/sqlalchemy, the app-factory-avoids-import-time-DB-
connection bug for flask).

### 4.6 The docs site (`mkdocs.yml`) vs. this document set

Two audiences, two places, deliberately not merged:

- **This document set** (`docs/_product/PRODUCT_SPEC.md`/`PRODUCT_FLOW.md`/
  `PRODUCT_ARCH.md`) is for whoever is *building* flint — spec-numbered
  requirements, worked examples of the `when`/`skip_value` mechanism,
  incident write-ups. It guides development direction and is the
  source of truth this whole file is part of.
- **The docs site** (`docs/*.md` outside `_product/`, built by
  `mkdocs.yml` with the Material theme, published to GitHub Pages) is
  for whoever is *using* flint — install instructions, a CLI reference,
  one page per template, `.agents/skills/` explained, remembered
  preferences, a contributing guide. Guide/reference tone, not spec
  tone; content is substantially *derived from* this document set and
  the per-template maintainer `README.md`s, rewritten for that
  audience rather than duplicating spec language.

**Why one `docs/` directory holds both, with one excluded**: keeping
the internal docs physically inside the same tree they describe (not a
separate repo/branch) is worth more than a clean top-level split — a
PR touching `generator.py`'s skills mechanism naturally sits next to
the `PRODUCT_ARCH.md` §4.5 update it needs. `mkdocs.yml`'s
`exclude_docs: |\n  _product/\n` (MkDocs ≥1.5) fully excludes that
subtree from the *built* site — not merely unlisted from nav, actually
absent from the output, unreachable by direct URL — while leaving it
exactly where a contributor browsing the repo would expect to find it.

**Why `docs/project-templates/`, not `docs/templates/`**: MkDocs
hardcodes a default exclusion pattern, `/templates/` at the docs root
(`mkdocs/structure/files.py`'s `_default_exclude`), reserved for theme
customization overrides — a name collision, not a design choice. Found
by the exact failure mode `exclude_docs` itself produces (files
silently absent from the build, `--strict` only warns that `nav`
references a now-excluded page) — worth remembering if a future docs
reorg reintroduces a `templates/` directory anywhere under `docs/`.

**Build/deploy**: `uv sync --group docs` installs `mkdocs`/
`mkdocs-material` (a separate dependency group from `dev` — CI/CD's
`ci.yml`/`cd.yml` never need to install them). `uv run mkdocs build
--strict` is the same command run locally, in `docs.yml`'s CI check,
and is what fails the build on any broken internal link, missing nav
target, or other structural issue (this is `--strict`'s job — content
*quality* is still a human/review concern, `--strict` only catches
structural breakage). See §8 for the deploy workflow itself.

**Gotcha: Material's grid-cards recipe needs two extensions, and
`--strict` won't catch a missing one.** `docs/index.md`'s "Where to go
next" section uses `<div class="grid cards" markdown>` — Material's
documented way to lay out linked cards. That recipe only renders if
`markdown_extensions` includes both `attr_list` (lets the `markdown`
attribute opt a raw HTML block into markdown processing) and
`md_in_html` (the extension that actually processes markdown nested
inside raw HTML — without it, Python-Markdown leaves the block's
contents untouched). Missing either one isn't a build error: the page
still builds and passes `--strict`, it just renders the card block as a
literal run of `**[text](link.md)**` markdown syntax instead of cards —
only caught by actually looking at the rendered page (found via a
Playwright screenshot pass, not the build log). Worth remembering for
any future page that reaches for a Material "recipe" requiring raw HTML
with nested markdown.

### 4.7 Two Jinja2 environments in one project — `full-stack`'s `.jinja`-suffix rule

`fastapi/full-stack` and `flask/full-stack` (v0.16.0) are the first
templates whose generated project *itself* renders Jinja2 at runtime —
`templates/base.html`, `templates/index.html`, and
`templates/partials/*.html` are FastAPI/Flask templates, rendered by
the generated app's own `Jinja2Templates`/`render_template()` on every
request. This collides with flint's existing rule that any `.jinja`-
suffixed file gets rendered through **flint's own** `generator._env` at
*generation* time (§4, top of this section) — a rule every other
template in the codebase relies on unconditionally.

If `index.html.jinja` existed, flint's generator would render it once,
at `flint new` time, using flint's context (`project_name`,
`package_name`, the resolved options — no `todos`, no `todo`). Its
`{% for todo in todos %}` would evaluate against an **undefined**
`todos` (Jinja's default `Undefined` renders as empty in output, no
error raised) and produce an empty loop body; `{{ todo.title }}` inside
a `{% include %}`'d partial would do the same. The generated project
would ship with a permanently empty-looking Todo list template, no
error at generation time, no error at `uv run pytest` time (nothing
asserts the *runtime* Jinja tags survived) — only a broken page in a
browser would reveal it. This was caught before it shipped, not after:
an initial draft of `base.html` used `.jinja` and a scripted check
(`grep` for `{{`/`{%` across every rendered file, run against several
option combos) flagged it immediately, well before any live-server
check.

**The fix**: `templates/*.html` and `static/css/style.css` carry **no**
`.jinja` suffix. `generator._render_content` copies a non-`.jinja` file
byte-for-byte (see the top of §4) — so these files pass through flint's
generator completely untouched, `{% for %}`/`{{ }}` and all, and are
only ever evaluated by the *generated app's* Jinja2 environment, once
the project is actually running. The one flint-resolved value these
templates need — `app_name` (ultimately `{{ project_name }}`, resolved
by flint into `core/config.py`'s `Settings` at generation time) — is
threaded through at *request* time instead, passed explicitly into the
render call from the route handler:

```python
return templates.TemplateResponse(
    request, "index.html", {"app_name": settings.app_name, "todos": todos}
)
```

This is a general rule going forward, not a one-off fix: **any file a
generated project renders with its own templating engine at runtime
must never carry flint's `.jinja` suffix**, regardless of framework.
`test_generator.py`'s `test_full_stack_no_leftover_jinja_in_runtime_templates`
(and its `test_flask_full_stack.py` equivalent) encode this as a
regression test — it asserts runtime Jinja syntax *does* survive inside
`templates/`, and that no `{{`/`{%` survives anywhere else in a
rendered project.

### 4.8 `full-stack`'s `css` option: a build-time/runtime split, not a template split

v0.17 added `css` (`vanilla` | `tailwind`) to both `full-stack`
templates. The interesting design decision wasn't the option itself —
it's a plain `select` like any other — but **where `static/css/style.css`
lives and what "shipping" it means**, which differs fundamentally
between the two values:

- **`css=vanilla`**: `style.css` is hand-written source, checked in,
  rendered by flint like any other file. What you see generated is
  exactly what serves in production.
- **`css=tailwind`**: `style.css` is a **build artifact**. The checked-in
  source is `static/css/input.css` (a few lines: `@import "tailwindcss"`
  plus an `@theme` block for custom design tokens — Tailwind v4's
  CSS-first config, no `tailwind.config.js`). `style.css` is produced by
  actually *running* the [Tailwind standalone CLI](https://tailwindcss.com/blog/standalone-cli)
  against `input.css` — flint never writes it, and it's `.gitignore`d in
  the generated project. This mirrors a pattern already established for
  `migrations=true` (schema comes from running a migration, not from
  `flint new`) and the worker option (a worker process flint doesn't
  start) — a real "one command you must run before this works" step,
  not something to fake at generation time.

**Why the standalone CLI, not a Node.js build pipeline**: every other
tool this project depends on installs through `uv`. A `package.json` +
`npm install` + Tailwind's PostCSS plugin would introduce Node.js as a
second toolchain into an otherwise Python-only generated project — a
real cost for a CSS framework. Tailwind v4's standalone CLI removes
that tradeoff entirely: it's a self-contained platform binary with no
Node runtime dependency. [`pytailwindcss`](https://pypi.org/project/pytailwindcss/)
wraps it as an ordinary `pyproject.toml` dependency — `uv sync` installs
the wrapper, and the wrapper downloads/caches the actual binary the
first time `uv run tailwindcss ...` executes. The design (source CSS in,
built CSS out, binary managed transparently, `init`/`watch`/`build`-
shaped commands) is modeled directly on
[`litestar-tailwind-cli`](https://github.com/Tobi-De/litestar-tailwind-cli),
the reference implementation of this pattern for a Python web framework
— flint doesn't reimplement binary-downloading logic itself, just
depends on the already-published wrapper.

**Layer structure**: `static/css/style.css` moved *out* of the base
`files/` layer entirely and into two new peer layers, `css-vanilla/`
(the pre-existing hand-written CSS, relocated unchanged) and
`css-tailwind/` (`input.css` + Tailwind-utility-class rewrites of
`templates/index.html` and `templates/partials/{todo_item,empty_state}.html`),
gated the same `when`-mechanism as `db-*`/`worker-*`. This is the
"layer, not inline `{% if %}`" choice from §4.2 applied to CSS: the two
variants' `templates/index.html` are genuinely different files (custom
class names vs. Tailwind utility classes), not one file with a
conditional class-name mapping, and forcing that into `{% if %}`
branches would make an already-verbose runtime-Jinja template (§4.7)
far harder to read. One consequence worth flagging for future template
authors: because neither `css-vanilla` nor `css-tailwind` has a
fallback, **`render()` called with `css` absent from `options` ships no
`static/css/style.css` and no `static/css/input.css` at all** — neither
layer's `when` matches a missing key. This is consistent with every
other option (`render()` never applies `template.json`'s declared
defaults; that's `prompts.py`'s job — see §4), but it was a real gap
caught during this release: `test_generator.py`'s
`make_full_stack_answers()` helper predates the `css` option and didn't
set it, so several existing tests silently stopped generating any CSS
file the moment the layers were split. Fixed by adding `css="vanilla"`
to the helper's defaults, matching how every other option already has
an explicit default there.

**A real bug this caught**: `tests/test_main.py.jinja` — shared by
`files/`, so shared by every `css` variant — had
`assert 'class="todo-item done"' in toggle_response.text` to check that
toggling a todo marks it done. That string is `css-vanilla`-only markup;
it doesn't exist in `css-tailwind`'s rewritten `todo_item.html`. Every
static check (`ast.parse()`, `tomllib.loads()`, the leftover-Jinja
sweep) passed regardless, because the test file itself is syntactically
fine — the failure only appeared when a generated `css=tailwind`
project's `uv run pytest` actually ran the assertion against real
Tailwind markup. Fixed by asserting the checkbox's `checked` attribute
instead, which is identical markup in both variants — the general
lesson (documented in both `full-stack` maintainer `README.md`s as a
standing rule) is that a test file shared across variants of a template
option must never assert against variant-specific presentation, only
behavior.

## 5. Remembered preferences (`prefs.py`)

`~/.flint/last.json` (PRODUCT_FLOW.md §6) is deliberately the simplest
thing that could work: one flat JSON file, no schema/migration
machinery, best-effort I/O.

```python
PREFS_DIR = Path.home() / ".flint"
PREFS_FILE = PREFS_DIR / "last.json"
```

Shape:

```json
{
  "last_framework": "fastapi",
  "last_templates": { "fastapi": "rest-api" },
  "templates": {
    "fastapi/rest-api": {
      "options": { "database": "postgres", "orm": "sqlmodel", "...": "..." },
      "docker": true,
      "git_init": false,
      "install": true
    }
  }
}
```

- `last_framework` — the single most-recently-used framework.
- `last_templates` — one entry per framework, so switching frameworks
  and switching back doesn't lose what was last picked in each.
- `templates` — keyed by `full_id` (`<framework>/<template>`, matching
  `TemplateMeta.full_id`), holding everything specific to that exact
  template: its resolved options plus `docker`/`git_init`/`install`.
  Two different templates never share a bucket, so rest-api's remembered
  `database` choice can't leak into hello-world's option set (which
  doesn't even have a `database` key).

`prefs.py`'s public surface is five pure-ish functions, all defensive by
construction rather than by caller-side checking:

- `load_prefs() -> dict` / `save_prefs(prefs: dict) -> None` — the only
  two functions that touch disk. `load_prefs` returns `{}` on *any*
  failure (missing file, unreadable, invalid JSON, valid JSON that isn't
  an object); `save_prefs` swallows any `OSError` (read-only home
  directory, out of disk, etc.). Neither ever raises — a broken prefs
  file must never be the reason `flint new` fails.
- `get_last_framework(prefs)`, `get_last_template(prefs, framework_id)`,
  `get_template_prefs(prefs, full_id)` — read accessors that double as
  sanitizers: each validates the type of what it reads (e.g. a
  hand-edited `"last_framework": 123` is treated as absent, not passed
  through and crashing something downstream) so every *caller* gets
  back either a well-typed value or `None`/`{}`, never has to
  type-check itself. `get_template_prefs` in particular always returns
  the full `{options, docker, git_init, install}` shape with `None`/`{}`
  for anything missing or malformed — `cli.py` never branches on
  whether a key exists.
- `record_run(prefs, *, framework_id, template_id, full_id, options,
  docker, git_init, install) -> dict` — pure function, returns an
  *updated copy* (doesn't mutate its input) with `last_framework`/
  `last_templates[framework_id]`/`templates[full_id]` all set; every
  other framework/template's remembered data passes through untouched.

**Staleness, not validation, is the operative concept.** There's no
"is this remembered value still valid" check inside `prefs.py` itself —
that's the caller's job, and it's the same job the caller already does
for the template's own `default`:

- `prompts._select_enabled(..., default_id)` — a remembered framework/
  template id is used only if it's still present *and* `enabled`;
  otherwise it falls back to the first enabled entry, exactly as if
  nothing had been remembered.
- `prompts.prompt_template_options(..., last)` — for a `select` option,
  a remembered value is used only if it's still among `option.choices`;
  for a `confirm` option, only if it's actually a `bool`. Otherwise, the
  template's own `option.default` is used, same as no `last` at all.
- `prompts.prompt_docker/prompt_git_init/prompt_install(..., remembered)`
  — `None` (never recorded, or the whole `templates` entry is missing)
  falls back to the existing hardcoded default (`False`/`True`/`True`
  respectively); any actual `bool` is used as-is.

This means a template's schema can change across Flint versions — an
option removed, a select's choices narrowed — and an old `last.json`
entry just silently stops applying to the parts that no longer make
sense, without any version field or migration step.

**Wiring, in `cli.py._run_new`:** `stored_prefs = prefs.load_prefs()` if
`remember` (the `--remember/--no-remember` flag, default `True`) else
`{}` — reusing the same "nothing remembered" path either way, so
`remember=False` needs no separate code path through `prompts.py`.
Every prompt call receives its slice of `stored_prefs` up front, resolved
*before* prompting (so both the interactive default and the
non-interactive fallback come from one lookup, per PRODUCT_FLOW.md §6).
After `generator.render` succeeds, `prefs.record_run(...)` builds the
updated dict and `prefs.save_prefs(...)` writes it — deliberately placed
after rendering (so a failed/rolled-back generation never gets
remembered) but before the git-init/install steps (whose success/failure
doesn't change what was actually *requested*, which is what's worth
remembering).

## 6. CLI flow → code mapping

| PRODUCT_FLOW step | Module |
|---|---|
| Entry points, flag parsing | `cli.py` (Typer app; `new` command; bare `flint` invokes `new` via Typer's default-command pattern) |
| Interactive prompts | `prompts.py` — one function per step, each accepting a pre-supplied flag value and skipping its own prompt if set or if `--yes`/non-TTY. `prompt_framework`/`prompt_template` share a `_select_enabled` helper. |
| Template option resolution | `prompts.prompt_template_options(template, provided, interactive, last)` — walks `template.options` in order, honoring an explicit `--option`/`-o key=value` override first (validated against the option's `type`/`choices`), else `when`-gating (§4), else a remembered value (§5) if still valid, else prompting or defaulting. `cli.py` parses the repeatable `--option` flag into a `dict[str, str]` via `prompts.parse_option_flags` and rejects unknown keys before resolution. |
| Remembered preferences | `prefs.py` (§5) — `cli.py` loads once per run and passes slices into each `prompts.*` call; records once, after a successful render. |
| Name validation | `naming.py` — pure functions, no I/O, exhaustively unit tested |
| Directory existence check | `cli.py` checks first — non-empty + no `--force` is a hard error in non-interactive mode, or (since v0.10) an interactive confirmation prompt (`prompts.prompt_force_overwrite`) that promotes `force` to `True` on "yes"; `generator.render()` re-checks the same condition regardless of caller, as a final safety net |
| File generation | `generator.py` |
| git init / uv sync | `postgen.py` — each step wrapped so a missing `git`/`uv` binary warns and continues rather than raising |
| Summary / next steps | `postgen.py` (`print_summary`), using `rich`; prints a leading `Options: k=v, ...` line when the template declared any |
| Exit codes | `errors.py` defines `FlintUserError` (→1) and lets anything else bubble to Typer's default handler (→2); the top-level command wraps generation in a `try/except FlintUserError` |

TTY detection for non-interactive mode: `sys.stdin.isatty()`, overridable
by explicit `--yes`.

`--docker` support-check ordering: `cli.py` picks the template and
resolves its options first, then calls `prompts.prompt_docker`, then —
if docker was requested but `chosen_template.supports_docker` is false —
downgrades to `docker=False` with a warning *before* calling
`generator.render`, so the render context (`Answers.docker`) always
matches what was actually generated.

`flint list-templates` (since v0.10) is a separate, standalone `@app.
command`, deliberately outside `_run_new`'s flow entirely — it's pure
introspection (`generator.list_frameworks()` × `generator.
list_templates()`, rendered as a `rich.table.Table`), generates
nothing, touches no filesystem beyond reading bundled `template.json`
files, and needs none of `_run_new`'s state (`Answers`, `prefs`,
`postgen`). Disabled frameworks/templates are listed too, annotated
"(coming soon)" — same convention `prompts._select_enabled` uses in the
wizard — so the command stays a complete, accurate picture of the
roadmap rather than just what's usable today.

## 7. Testing strategy

`pytest` runs with `--cov=flint --cov-report=term-missing
--cov-fail-under=100` by default (`[tool.pytest.ini_options]` in
`pyproject.toml`), with branch coverage on
(`[tool.coverage.run] branch = true`) — the suite fails the moment any
line *or* branch in `src/flint/` goes uncovered, not just when a whole
function is untested. `uv run pytest` is enough to check both tests and
coverage locally; use `uv run pytest --no-cov` while iterating to skip
the gate temporarily.

- `test_naming.py` — table-driven tests of the slugify/package-name
  rules, plus the defensive non-identifier guard (forced via
  monkeypatching, since real input can't reach it).
- `test_generator.py` — the bulk of the suite. Covers: `when_matches`
  directly (empty/single/multi-key/missing-key cases); `hello-world`
  render with/without `docker`/`config`; the non-empty-directory guard,
  disabled-framework/-template rejection (synthesized via a
  `TEMPLATES_DIR` monkeypatch, since both real templates are enabled
  now), rollback-on-failure (including that a `FlintError` mid-render
  still rolls back, and that a pre-existing `--force` directory is never
  deleted); the verbatim-copy path for non-`.jinja` files;
  `list_frameworks`/`list_templates` skipping entries without
  `template.json`; a declared layer with a missing directory being
  skipped rather than failing. A dedicated block of `rest-api`-specific
  tests renders real combinations (in-memory, SQLite+SQLModel+migrations,
  Postgres+SQLAlchemy, Taskiq, Celery, Redis, Taskiq/Celery+RabbitMQ, the
  `redis`/`broker` decoupling, "all features combined") and asserts the
  right files exist/don't, then runs every `.py` file through
  `ast.parse()` and `pyproject.toml` through `tomllib.loads()` — catches
  template bugs (like the whitespace ones in §4.3) that only a
  rendered-output check would catch, without needing a live `uv sync`
  for every combination.
- `test_prompts.py` — monkeypatches `questionary`'s `.ask()` calls (it
  drives a real TTY via `prompt_toolkit`, which can't be exercised
  through Typer's `CliRunner`) to cover the interactive branches for
  every prompt function, plus `parse_option_flags` and
  `prompt_template_options` against both a synthetic template (a
  `database`/`orm`/`migrations` option chain mirroring rest-api's shape,
  for isolated `when`/`skip_value` testing) and the real `rest-api`
  template (confirming its actual declared defaults, that `worker`
  implies a `broker`, and that `broker` decouples `redis` per §4.1).
- `test_cli.py` — Typer's `CliRunner`, covering: full non-interactive
  happy path (with and without `--docker`), `--option` end-to-end for
  rest-api (and its "Options: ..." summary line), unknown/invalid
  `--option` values, a malformed `--option` (no `=`), `--version`,
  `--help`, existing-directory error, invalid name, unknown/disabled
  framework/template, `--docker` requested against a template that
  doesn't support it, a `typer.Exit` raised mid-flow passing
  through unchanged, and an unexpected exception mapping to exit code 2.
  The fully-interactive path (including the "Using uv..." message) is
  exercised by calling `cli._run_new` directly with `sys.stdin` patched
  and `questionary` stubbed, rather than through `CliRunner` — Click's
  `CliRunner.invoke()` swaps `sys.stdin` out for its own stream for the
  duration of the call, which would clobber an `isatty()` patch made
  beforehand.
- `test_postgen.py` — `git_init`/`install_dependencies` directly, with
  `subprocess.run` monkeypatched: binary-not-found, success, and
  `CalledProcessError` for each; `print_summary`'s options-line
  presence/absence.
- `test_prefs.py` — `load_prefs`/`save_prefs` round-tripping, a missing/
  corrupt/non-object prefs file resolving to `{}`, an unwritable
  `PREFS_DIR` not raising, every accessor's type-guarding (wrong type at
  each level of the JSON → `None`/`{}`, not a crash), and `record_run`
  both merging correctly and not mutating its input. `conftest.py`'s
  `isolated_prefs_dir` autouse fixture monkeypatches `prefs.PREFS_DIR`/
  `prefs.PREFS_FILE` to a per-test `tmp_path` subdirectory — this is what
  keeps every test in the suite (not just `test_prefs.py`) from ever
  touching the real `~/.flint`, and from leaking remembered state between
  tests. `test_cli.py` layers end-to-end coverage on top: a full
  remember → next-run-uses-it round trip through `CliRunner`,
  `--no-remember` skipping both the read and the write, an explicit flag
  still winning over a remembered value, and a stale remembered option
  value falling back to the template's own default.
- `test_main.py` — covers the `python -m flint` / `python -m flint.cli`
  entry-point guards via `runpy.run_module(..., run_name="__main__")`,
  plus a plain `import flint.__main__` to cover the guard's not-taken
  branch.
- `test_flask_hello_world.py` / `test_flask_rest_api.py` /
  `test_flask_full_stack.py` — Flask's mirror of the FastAPI
  hello-world/rest-api/full-stack coverage above (rendered
  combinations, `ast.parse()`/`tomllib.loads()` checks, plus a check
  that `templates/`/`static/` content survives flint's generator with
  its runtime Jinja2 syntax intact — see §4.7). Kept as standalone
  files rather than folded into `test_generator.py`, since they exist
  purely to cover a second framework's content, not the generator
  engine itself. `full-stack`'s FastAPI-side tests, by contrast, live
  inline in `test_generator.py` (mirroring `rest-api`'s own placement)
  since FastAPI is the enabled-by-default framework and needs no
  monkeypatch fixture.
- **Live end-to-end verification (manual, done before every template
  change ships — not part of the automated suite or the coverage
  gate)**: actually run generated output through `uv sync && uv run
  pytest` for representative combinations; run real Alembic/Flask-Migrate
  migrations against real SQLite *and* real PostgreSQL; boot the
  generated app plus a real Taskiq/Celery worker against real Redis and
  enqueue/execute an actual task end-to-end; `docker build`/`docker run`
  + a live request. This is what caught the bugs in §7.1 below —
  `ast.parse()` and `uv sync` alone did not.

### 7.1 Bugs this level of verification caught (and why lighter checks missed them)

Worth recording — each was invisible to `uv sync && pytest`, only
surfaced by actually running the generated tooling:

- **Missing top-level `__init__.py`** in rest-api's `files/` layer (only
  `core/__init__.py` and `routes/__init__.py` existed). Plain Python
  imports still worked via PEP 420 namespace packages, and so did
  pytest (its own `pythonpath` config), which is exactly why `uv sync &&
  pytest` stayed green — but `fastapi_cli`'s own directory-walk logic
  (used by `fastapi dev`/`fastapi run`) requires `__init__.py` to
  correctly find the `src/` root, and silently computed the *wrong*
  root without it, breaking `fastapi dev`.
- **Alembic's `prepend_sys_path`** defaulted to `.` (the project root);
  needed to be `src` for a `src/`-layout project, or `alembic revision
  --autogenerate` can't import the app's models at all.
  `uv sync && pytest` never touches Alembic, so this was invisible until
  actually running `alembic revision`.
- **Taskiq/Celery task discovery**: pointing either worker CLI at
  `worker.py` (which defines the broker/app) doesn't automatically
  import the task modules under `tasks/` (which register the actual
  tasks) — the worker starts cleanly and reports zero known tasks.
  Fixed by importing each `tasks/*.py` module at the *bottom* of
  `worker.py` (after the broker/app object exists, to sidestep the
  circular import — a task module needs to import `broker`/`celery_app`
  from `worker.py`). A bare `from ... import tasks` (the package) isn't
  enough either — importing a package doesn't auto-import its
  submodules, so each new file under `tasks/` needs its own explicit
  import line. Only a real worker process boot ("`[tasks]` empty" /
  "task not found") surfaces this — the code imports and type-checks
  fine either way.
- **`aiosqlite` only in prod deps for `database == "sqlite"`**: but
  rest-api's tests *always* use an isolated SQLite database for
  isolation (FR10), regardless of which database was configured for
  production — so `database == "postgres"` generated a project whose
  own test suite couldn't run (`ModuleNotFoundError: aiosqlite`) unless
  `aiosqlite` was *also* an unconditional dev-dependency. Caught only by
  actually running `pytest` inside a `database=postgres` project — a
  postgres-flavored `ast.parse()`/`tomllib` check has no way to know the
  test suite needs a package the production code doesn't.
- **Flask's module-level `app = Flask(__name__)` opens a DB connection at
  import time**: FastAPI's rest-api never had this problem (it builds
  the app once, inside `main.py`, with `init_db()` only called from an
  `async` startup hook). A naive Flask port that assigned `app =
  Flask(__name__)` at module scope and built the DB engine right there
  would run that code the instant `pytest`/`flask db ...`/`alembic`
  merely *imported* the module — meaning every test run and every
  migration command would try to reach the real `.env`-configured
  database, violating the "tests never touch the configured production
  database" guarantee (FR10) the moment `database=postgres` was chosen
  without a reachable Postgres. Fixed with an application-factory
  pattern (`create_app(*, database_url=None, testing=False)`, never
  called at module scope) — `flask run`/`flask db ...` auto-detect the
  factory from `--app`, the Dockerfile's `gunicorn` points at
  `{{ package_name }}.main:create_app()`, and tests call the factory
  directly with an isolated `sqlite:///:memory:` URL. Only surfaced by
  actually running `flask db migrate`/`pytest` against a
  `database=postgres` project with no Postgres reachable — an
  `ast.parse()` check has no way to know an import has a side effect.
- **Flask-Migrate needs a Flask-SQLAlchemy `db` object**, so it can't
  share `db.py` with the manual-SQLAlchemy ORM choice the way FastAPI's
  `db-sqlmodel`/`db-sqlalchemy` migrations layers do (both wrap the same
  Alembic). Flask's `orm=flask-sqlalchemy` uses `flask db migrate/
  upgrade` (Flask-Migrate, registers a CLI command group via
  `migrate.init_app(app, db)`); `orm=sqlalchemy` uses bare Alembic
  instead (`migrations-sqlalchemy` layer, same shape as FastAPI's) —
  two separate migrations layers rather than one shared implementation.
- **`create_all()` unconditionally alongside migrations made the
  migrations decorative, in *both* frameworks** (present since `rest-
  api`'s original `v0.3.0` migrations support — not something the Flask
  work introduced, just inherited and then noticed while building
  Flask's mirror of it). `init_db()`/`create_app()` called
  `Base.metadata.create_all()` (or `db.create_all()`) on every app boot
  regardless of whether `migrations` was enabled — so by the time anyone
  ran `alembic revision --autogenerate`/`flask db migrate`, the tables
  already existed and matched the models exactly (created by the eager
  `create_all()`, not by any migration), and autogenerate reported "No
  changes in schema detected" instead of generating the real initial
  migration. On a genuinely fresh database this doesn't just produce an
  empty migration, it's a footgun waiting to fire: `alembic upgrade
  head`/`flask db upgrade` would eventually try to create tables that
  `create_all()` had already silently created outside migration history,
  since `alembic_version` was never stamped. `uv sync && pytest` never
  caught this because both frameworks' test fixtures build their own
  schema directly (FastAPI: a separate `test_engine` + `create_all`/
  `drop_all` in `conftest.py`, bypassing `init_db()` entirely; Flask:
  `create_app(testing=True)` still needs *some* way to get a schema for
  a throwaway in-memory database, since there's no migration history to
  replay against it) — only actually running `alembic revision
  --autogenerate`/`flask db migrate` against a fresh on-disk database and
  checking whether it detected the model as new caught it. Fixed by
  making `create_all()`/`db.create_all()` conditional on `migrations`:
  FastAPI's `main.py` simply never calls `init_db()` when `migrations`
  is true (schema comes solely from `alembic upgrade head`); Flask's
  `init_db()` gained a `testing` parameter so it's *only* auto-created
  for the isolated in-memory test database, never for a real one. Both
  frameworks' README.md now say the database is **not** auto-created on
  startup when `migrations` is enabled, and to run the migration first.

## 8. Versioning & release mechanics

- `src/flint/__init__.py` holds `__version__`, single source of truth;
  `pyproject.toml`'s `version` is kept in sync manually for v0 (a
  version-sync script/tool is a reasonable v0.x addition, not needed for
  one release).
- `CHANGELOG.md` follows the `v{release}.{feature}.{fixes}` scheme
  defined in the product spec; every entry links the version to the
  behavior change, newest first.
- **CI** (`.github/workflows/ci.yml`, since v0.10.1): on every push to
  `main` and every PR — `uv sync --locked` (fails if `uv.lock` drifted
  from `pyproject.toml`), `uv run pytest` (the same 100%-coverage-gated
  suite documented in §7), and a smoke check that the installed console
  script actually runs (`uv run flint --version`). Single Python
  version (3.11, the floor in `requires-python`) — flint's own code has
  no version-specific branches, so a matrix would mostly re-run the
  same thing.
- **CD** (`.github/workflows/cd.yml`, since v0.10.1): fires on pushing a
  `v*` tag (the same tag the manual release step already produced pre-
  automation — bump `__version__`/`pyproject.toml`, update
  `CHANGELOG.md`, commit, tag, push). Two jobs: `test` (identical gate
  to CI — a tag with a red test suite never reaches `publish`), then
  `publish`, which verifies the pushed tag's version matches
  `pyproject.toml`'s (refuses to publish on a mismatch — a manually
  mistagged commit must not ship under the wrong version), runs `uv
  build`, and publishes via `pypa/gh-action-pypi-publish` using PyPI's
  **Trusted Publishing** (OIDC) — no long-lived API token stored as a
  GitHub secret; the `publish` job's `id-token: write` permission and
  its `pypi` environment are what PyPI's trusted-publisher config keys
  off of (repo, workflow filename, and environment name all have to
  match what's registered on PyPI's side for the token exchange to
  succeed).
- **Docs** (`.github/workflows/docs.yml`, since v0.11.0): fires on a
  push to `main` that touches `docs/**`, `mkdocs.yml`, or the workflow
  file itself (path-filtered — a code-only change doesn't trigger a
  docs rebuild), plus `workflow_dispatch` for a manual re-run. `build`
  job: `uv sync --group docs`, `uv run mkdocs build --strict` (fails on
  any broken link/nav reference — the same command a contributor runs
  locally, see §4.6), uploads the built `site/` as a Pages artifact.
  `deploy` job: `actions/deploy-pages` publishes it — no `gh-pages`
  branch, no separate token; this uses GitHub's own OIDC-based Pages
  deploy mechanism (`id-token: write` + `pages: write` permissions),
  the same trusted-publishing *shape* as `cd.yml`'s PyPI publish, just
  for a different provider. Requires one manual, one-time repo setting
  (can't be done via a workflow file): **Settings → Pages → Build and
  deployment → Source: "GitHub Actions"**.
- **Release tagging** (`.github/workflows/release.yml`, since v0.14.1):
  fires on a push to `main` that touches `pyproject.toml`. Reads the
  version and, if `vX.Y.Z` isn't already tagged, creates and pushes
  that tag using the workflow's own `GITHUB_TOKEN` — needed because an
  external git credential pushing branches fine can still get a plain
  403 trying to push a tag if the repo has a tag-protection rule
  scoped tighter than branch push access.
- **Chaining `release.yml` into `cd.yml`** (since v0.14.2 — v0.14.1's
  first attempt is a documented incident, not just history): a tag push
  from the default `GITHUB_TOKEN` doesn't retrigger other workflows
  (GitHub explicitly suppresses that, as a loop guard), so `release.yml`
  can't just push the tag and rely on `cd.yml`'s `push: tags: v*`
  trigger to fire. The first fix — `release.yml` calling `cd.yml`
  directly via `workflow_call` — ran, tested, and built correctly, then
  failed at the actual PyPI upload: PyPI's Trusted Publishing OIDC
  verification checks the certificate's Build Config URI, which names
  the *top-level* workflow that ran (`release.yml`), not any reusable
  workflow it calls — so it never matches a Trusted Publisher
  registered for `cd.yml`, no matter what `cd.yml` itself declares.
  Fixed by giving `cd.yml` a `workflow_run` trigger
  (`workflows: ["Release"]`, gated on `github.event.workflow_run.conclusion
  == 'success'`) instead — `cd.yml` then runs as its own genuinely
  top-level workflow, matching what's registered on PyPI. Since a
  `workflow_run`-triggered job has no `workflow_call` `ref` input to
  read the intended tag from, the "does this commit's tag match
  `pyproject.toml`" safety check now does `git describe --tags
  --exact-match HEAD` (checkout uses `fetch-depth: 0` so the tag is
  actually present locally) instead of parsing `github.ref_name` — this
  works the same whether `cd.yml` was triggered by a real tag push or
  by `release.yml` finishing. `cd.yml`'s original `push: tags: v*`
  trigger is unchanged, so a tag pushed by a human from their own
  machine still works exactly as before.

## 9. Explicitly deferred (tracked, not forgotten)

Nothing is currently deferred — as of v0.10.0 every item previously
tracked here is resolved (see PRODUCT_SPEC.md §12 and CHANGELOG.md):
`--force` overwrite confirmation and `flint list-templates` shipped;
package-manager choice and template distribution were closed as
deliberate design decisions (uv-only, bundled-only) rather than left
open. This section exists so a *new* non-goal has a documented home —
not every future idea needs one; only things worth explicitly saying
"not now, but not forgotten either."

Package-manager choice, if ever revisited: `postgen.py`'s install step
is already isolated behind one function, swappable per an `Answers.pm`
field without touching the rest of the pipeline. Remote/pluggable
template sources, if ever revisited: would live behind the same
`generator.render(framework_id, template_id, ...)` interface — the ids
could become a path/URL instead of a bundled-package lookup without
changing callers. Neither is planned work.
