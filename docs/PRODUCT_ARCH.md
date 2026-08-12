# Flint — Architecture

**Status:** Draft for v0
**Owner:** Engineering
**Last updated:** 2026-08-12 (v0.3: per-template options, generalized layer gating, restapi)

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

- PyPI distribution name: `flint-cli` (see PRODUCT_SPEC §10 for why).
- Console script entry point: `flint`.
- Primary usage is via `uvx flint` (ephemeral run, no install) or
  `uv tool install flint-cli` (persistent `flint` on PATH) — mirrors how
  `npx create-next-app` is normally invoked.
- Build backend: `hatchling` via `uv`'s default `uv init --package`
  project shape (src layout).

## 3. Repository layout

```
flint/
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── PRODUCT_FLOW.md
│   └── PRODUCT_ARCH.md
├── src/
│   └── flint/
│       ├── __init__.py          # __version__
│       ├── __main__.py          # `python -m flint`
│       ├── cli.py               # Typer app, `new` command, flags incl. --option
│       ├── prompts.py           # questionary wizard steps + option resolution
│       ├── naming.py            # project name -> slug/package_name validation
│       ├── generator.py         # template renderer: options, layers, Jinja2
│       ├── postgen.py           # git init, uv sync, summary printing
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
│           │   └── restapi/
│           │       ├── template.json               # options: [database, orm, migrations, worker, redis]
│           │       ├── files/                       # always rendered — in-memory CRUD, config, schemas
│           │       ├── docker/                       # rendered iff --docker
│           │       ├── db-sqlmodel/                   # rendered iff orm == sqlmodel; overrides routes/items.py
│           │       ├── db-sqlalchemy/                 # rendered iff orm == sqlalchemy; overrides routes/items.py
│           │       ├── migrations-sqlmodel/            # rendered iff migrations && orm == sqlmodel
│           │       ├── migrations-sqlalchemy/          # rendered iff migrations && orm == sqlalchemy
│           │       ├── worker-taskiq/                   # rendered iff worker == taskiq
│           │       ├── worker-celery/                   # rendered iff worker == celery
│           │       └── redis/                            # rendered iff redis is true (requested or implied)
│           ├── flask/template.json                  # disabled stub — roadmap
│           └── django/template.json                 # disabled stub — roadmap
├── tests/
│   ├── test_naming.py
│   ├── test_generator.py
│   ├── test_prompts.py
│   ├── test_cli.py
│   ├── test_postgen.py
│   └── test_main.py
├── pyproject.toml
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## 4. Template system design

Templates are organized two levels deep: `templates/<framework>/<template>/`
(PRODUCT_SPEC §3 defines the framework/template/option distinction). A
**framework** directory (`templates/fastapi/`) has its own
`template.json` and one subdirectory per **template** variant
(`hello-world/`, `restapi/`), each with its own `template.json`. Disabled
frameworks (`flask`, `django`) are stubs — just a `template.json` with
`"enabled": false`, no `files/` — that exist purely so the wizard/CLI can
list them as "coming soon" (PRODUCT_FLOW §2 step 3) without any code
changes.

### `template.json` schema

```json
{
  "id": "restapi",
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
  (§5) in the order listed. Each is `type: "select"` (needs `choices`,
  a list of `{value, label}`) or `type: "confirm"` (a y/n). `when` makes
  an option depend on an **earlier** option's resolved value — declaration
  order matters, since a `when` can only see already-resolved keys.
  When `when` is present and doesn't match, the option is never asked
  (interactive or not) and instead resolves to `skip_value` (falling
  back to `default` if `skip_value` is omitted). This is how restapi's
  `orm`/`migrations` collapse to `"none"`/`false` when no database was
  chosen, and how `redis` resolves to `true` — implied, not asked — the
  moment a worker is chosen (its `when` is `{"worker": ["none"]}`; picking
  any other worker makes that not match, triggering `skip_value: true`).
  `generator.when_matches(when, values)` implements the predicate itself,
  shared between option resolution and layer gating below — an empty/
  absent `when` always matches.
- **`layers`** (optional) — extra directories rendered *in addition to*
  the always-on `files/` layer, each gated by the same `when` predicate,
  evaluated against the *fully resolved* answers (fixed fields like
  `docker`/`git_init` merged with the template's own resolved options —
  see `Answers.context()`). This is how `--docker` adds a Dockerfile
  (`{"dir": "docker", "when": {"docker": [true]}}` — no code path is
  hardcoded to "docker" anymore, it's just data) and how e.g. restapi's
  `worker-taskiq` layer adds worker code only when that worker was
  chosen. **A later layer's file silently overwrites an earlier one at
  the same relative path** — that's the mechanism restapi uses to swap
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
    template: str            # "restapi"
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
new *framework* is the same, one level up. Adding Flask/Django for real
is purely a content change (swap `enabled: false` → `true` and fill in
`files/`), not an architecture change.

### 4.1 A worked example: restapi's `redis` option

Three moving pieces, all data-driven:

1. `template.json`'s `redis` option: `"when": {"worker": ["none"]},
   "skip_value": true`. Read as: *ask about Redis only if no worker was
   chosen; if a worker **was** chosen, Redis is implied — resolve to
   `true` without asking.*
2. `template.json`'s `redis` **layer**: `{"dir": "redis", "when":
   {"redis": [true]}}`. Once the option above resolves (asked or
   implied), the layer gate just checks the final value — it doesn't
   care *why* `redis` ended up `true`.
3. `redis/src/{{package_name}}/core/redis.py.jinja` — the one new file
   that layer adds (an async Redis client). It doesn't touch `main.py`,
   deliberately, so it can't conflict with the `worker-*` layers, which
   *do* override `main.py` (to add lifespan wiring and a demo
   task-enqueue endpoint).

### 4.2 When to use a layer vs. an inline `{% if %}`

Two mechanisms exist for conditional content; picking the wrong one for
a given file makes templates harder to maintain:

- **Layers** (preferred for code): a whole file either exists for a
  given combination of choices or it doesn't. `db-sqlmodel/` and
  `db-sqlalchemy/` each ship their own complete `routes/items.py` and
  `db/session.py` — no shared file has ORM-specific branches in it.
  Keeps generated *code* readable (a developer opens `routes/items.py`
  and sees one clean implementation, not four nested `{% if %}` blocks).
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

## 5. CLI flow → code mapping

| PRODUCT_FLOW step | Module |
|---|---|
| Entry points, flag parsing | `cli.py` (Typer app; `new` command; bare `flint` invokes `new` via Typer's default-command pattern) |
| Interactive prompts | `prompts.py` — one function per step, each accepting a pre-supplied flag value and skipping its own prompt if set or if `--yes`/non-TTY. `prompt_framework`/`prompt_template` share a `_select_enabled` helper. |
| Template option resolution | `prompts.prompt_template_options(template, provided, interactive)` — walks `template.options` in order, honoring an explicit `--option`/`-o key=value` override first (validated against the option's `type`/`choices`), else `when`-gating (§4), else prompting or defaulting. `cli.py` parses the repeatable `--option` flag into a `dict[str, str]` via `prompts.parse_option_flags` and rejects unknown keys before resolution. |
| Name validation | `naming.py` — pure functions, no I/O, exhaustively unit tested |
| Directory existence check | `generator.py` (single source of truth, both interactive and non-interactive paths call it) |
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

## 6. Testing strategy

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
  skipped rather than failing. A dedicated block of `restapi`-specific
  tests renders real combinations (in-memory, SQLite+SQLModel+migrations,
  Postgres+SQLAlchemy, Taskiq, Celery, Redis, "all features combined")
  and asserts the right files exist/don't, then runs every `.py` file
  through `ast.parse()` and `pyproject.toml` through `tomllib.loads()` —
  catches template bugs (like the whitespace ones in §4.3) that only a
  rendered-output check would catch, without needing a live `uv sync`
  for every combination.
- `test_prompts.py` — monkeypatches `questionary`'s `.ask()` calls (it
  drives a real TTY via `prompt_toolkit`, which can't be exercised
  through Typer's `CliRunner`) to cover the interactive branches for
  every prompt function, plus `parse_option_flags` and
  `prompt_template_options` against both a synthetic template (a
  `database`/`orm`/`migrations` option chain mirroring restapi's shape,
  for isolated `when`/`skip_value` testing) and the real `restapi`
  template (confirming its actual declared defaults and that `worker`
  really does imply `redis`).
- `test_cli.py` — Typer's `CliRunner`, covering: full non-interactive
  happy path (with and without `--docker`), `--option` end-to-end for
  restapi (and its "Options: ..." summary line), unknown/invalid
  `--option` values, a malformed `--option` (no `=`), `--version`,
  `--help`, existing-directory error, invalid name, unknown/disabled
  framework/template, `--docker` requested against a template that
  doesn't support it, a `typer.Exit` raised mid-flow passing through
  unchanged, and an unexpected exception mapping to exit code 2. The
  fully-interactive path (including the "Using uv..." message) is
  exercised by calling `cli._run_new` directly with `sys.stdin` patched
  and `questionary` stubbed, rather than through `CliRunner` — Click's
  `CliRunner.invoke()` swaps `sys.stdin` out for its own stream for the
  duration of the call, which would clobber an `isatty()` patch made
  beforehand.
- `test_postgen.py` — `git_init`/`install_dependencies` directly, with
  `subprocess.run` monkeypatched: binary-not-found, success, and
  `CalledProcessError` for each; `print_summary`'s options-line
  presence/absence.
- `test_main.py` — covers the `python -m flint` / `python -m flint.cli`
  entry-point guards via `runpy.run_module(..., run_name="__main__")`,
  plus a plain `import flint.__main__` to cover the guard's not-taken
  branch.
- **Live end-to-end verification (manual, done before every template
  change ships — not part of the automated suite or the coverage
  gate)**: actually run generated output through `uv sync && uv run
  pytest` for representative combinations; run real Alembic migrations
  against real SQLite *and* real PostgreSQL; boot the generated app plus
  a real Taskiq and a real Celery worker against real Redis and enqueue/
  execute an actual task end-to-end; `docker build`/`docker run` +a live
  request. This is what caught the bugs in §6.1 below — `ast.parse()`
  and `uv sync` alone did not.

### 6.1 Bugs this level of verification caught (and why lighter checks missed them)

Worth recording — each was invisible to `uv sync && pytest`, only
surfaced by actually running the generated tooling:

- **Missing top-level `__init__.py`** in restapi's `files/` layer (only
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
  import `tasks.py` (which registers the actual tasks) — the worker
  starts cleanly and reports zero known tasks. Fixed by importing
  `tasks` at the *bottom* of `worker.py` (after the broker/app object
  exists, to sidestep the circular import — `tasks.py` needs to import
  `broker`/`celery_app` from `worker.py`). Only a real worker process
  boot ("`[tasks]` empty" / "task not found") surfaces this — the code
  imports and type-checks fine either way.
- **`aiosqlite` only in prod deps for `database == "sqlite"`**: but
  restapi's tests *always* use an isolated SQLite database for
  isolation (FR10), regardless of which database was configured for
  production — so `database == "postgres"` generated a project whose
  own test suite couldn't run (`ModuleNotFoundError: aiosqlite`) unless
  `aiosqlite` was *also* an unconditional dev-dependency. Caught only by
  actually running `pytest` inside a `database=postgres` project — a
  postgres-flavored `ast.parse()`/`tomllib` check has no way to know the
  test suite needs a package the production code doesn't.

## 7. Versioning & release mechanics

- `src/flint/__init__.py` holds `__version__`, single source of truth;
  `pyproject.toml`'s `version` is kept in sync manually for v0 (a
  version-sync script/tool is a reasonable v0.x addition, not needed for
  one release).
- `CHANGELOG.md` follows the `v{release}.{feature}.{fixes}` scheme
  defined in the product spec; every entry links the version to the
  behavior change, newest first.
- No CI/publish automation in v0 (non-goal); the release step is a
  manual `uv build` + tag, documented in the CHANGELOG's Unreleased →
  version-heading workflow.

## 8. Explicitly deferred (tracked, not forgotten)

- Remote/pluggable template sources (would live behind the same
  `generator.render(framework_id, template_id, ...)` interface — the ids
  could become a path/URL instead of a bundled-package lookup without
  changing callers).
- Package-manager choice (pip/poetry) — `postgen.py`'s install step is
  already isolated behind one function, swappable per an `Answers.pm`
  field if that's ever added.
- Message brokers other than Redis for restapi's `worker` option (e.g.
  RabbitMQ for Celery) — would multiply the worker×broker combinations
  to support and verify; deferred until there's real demand.
- `.agents/skills/<framework>` — a directory of framework-specific,
  agent-consumable skills shipped into generated projects. Deferred per
  PRODUCT_SPEC §12: needs real content and a target skill format/consumer
  decided, not just plumbing. `AGENTS.md` (always-on) ships now as the
  lightweight version of "give agents context."
- `--force` overwrite confirmation UX polish, `flint list-templates`
  introspection command.
