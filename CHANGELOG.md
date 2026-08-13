# Changelog

All notable changes to Flint are documented here.

Versions follow `v{release}.{feature}.{fixes}` (see `docs/PRODUCT_SPEC.md`
§11): `release` is the major epoch (starting at `0`), `feature` bumps for
new user-facing capability, `fixes` bumps for patches with no new
capability.

## v0.10.1 — 2026-08-13

### Added

- **CI/CD via GitHub Actions.** `.github/workflows/ci.yml` runs on every
  push to `main` and every PR: `uv sync --locked`, the full test suite
  (`uv run pytest`, same 100%-coverage gate as local development), and
  a smoke check that the installed console script runs. `.github/
  workflows/cd.yml` fires on pushing a `v*` tag: re-runs the same test
  gate, verifies the tag's version matches `pyproject.toml` (refuses to
  publish on a mismatch), builds via `uv build`, and publishes to PyPI
  using Trusted Publishing (OIDC) — no API token stored as a repo
  secret. Publishing requires a one-time PyPI-side setup (see
  PRODUCT_ARCH.md §8 for exactly what to register). No change to the
  `flint` CLI itself — this is release infrastructure only.

## v0.10.0 — 2026-08-13

### Added

- **Interactive `--force` overwrite confirmation.** Running into a
  non-empty target directory without `--force` used to hard-error
  unconditionally. Now, in interactive mode, Flint asks "Directory 'x'
  already exists and is not empty. Overwrite?" instead of failing
  outright — confirming proceeds exactly as `--force` would have,
  declining aborts cleanly with no files written. Non-interactive runs
  (`--yes`/piped stdin/CI) are unchanged: no prompt, same hard error
  unless `--force` was already passed.
- **`flint list-templates`**: a new introspection command listing every
  framework/template pair — label, description, whether it supports
  `--docker` — including disabled/"coming soon" entries, so the roadmap
  stays visible outside the wizard too. Generates nothing.

### Changed

- **Package manager and template distribution are formally closed, not
  left open.** Both were long-standing "Open Questions" in
  PRODUCT_SPEC.md §12 with no code changes attached. Flint stays
  `uv`-only (every template's `pyproject.toml`/README/`AGENTS.md`/skill
  already assumes it end to end — supporting pip/poetry would mean a
  second rendering of every template, not a small addition) and
  bundled-templates-only (no remote/git-based sources — simplest model,
  no network dependency, no supply-chain exposure from executing a
  fetched Jinja template). Neither is a capability change; this just
  documents that they were decided, not forgotten.

## v0.9.0 — 2026-08-13

### Added

- **`.agents/skills/<id>/` — a shared, opt-in catalog of deeper agent
  reference material.** Beyond the always-on, lightweight `AGENTS.md`,
  every generated project now also gets `.agents/skills/<id>/` for
  each library it actually uses — a `SKILL.md`, `references/*.md`, and
  `guides/*.md` per library, plus a generated `.agents/skills/README.md`
  index and an `AGENTS.md` section pointing at whichever skills apply.
  Eleven skills ship: `fastapi`, `flask`, `pydantic-settings`,
  `sqlmodel`, `sqlalchemy` (covers both FastAPI's async and Flask's
  sync usage), `flask-sqlalchemy`, `alembic`, `flask-migrate`,
  `taskiq`, `celery`, `redis`, `pytest`. Selection is declarative — a
  new `skills` list in `template.json`, gated by the exact same `id`/
  `when` shape `layers` already use — and the catalog lives once, flat,
  at `src/flint/skills/<id>/`, decoupled from any one framework/
  template so a skill used by both (e.g. `pytest`, `redis`) isn't
  duplicated. Rendered through the same Jinja mechanism as everything
  else, so skill content gets real `{{ package_name }}` substitution
  and can branch on resolved options (e.g. the shared `sqlalchemy`
  skill reads async-first for a FastAPI project, sync-first for a
  Flask one). Every real gotcha already recorded in `PRODUCT_ARCH.md`
  §7.1 is folded into the relevant skill's `references/gotchas.md`
  (task-discovery for taskiq/celery, `create_all()`-vs-migrations for
  alembic/flask-migrate/flask-sqlalchemy/sqlalchemy, the
  app-factory-avoids-import-time-DB-connection bug for flask).
  Live-verified end-to-end across both frameworks and a range of
  option combinations: correct skill selection, correct `.env`-style
  `package_name` substitution, no leftover template syntax, and a real
  `uv sync && uv run pytest` pass on the generated output.

## v0.8.1 — 2026-08-12

### Fixed

- **`rest-api`: migrations were decorative in both frameworks.**
  `init_db()`/`create_app()` called `create_all()` on every app boot
  regardless of the `migrations` option, so by the time `alembic
  revision --autogenerate`/`flask db migrate` ran, the tables already
  existed (created outside migration history) and matched the models
  exactly — autogenerate always reported "No changes in schema
  detected" instead of generating a real migration. Fixed by making the
  eager `create_all()` conditional on `migrations`: FastAPI's `rest-api`
  no longer calls `init_db()` at all when `migrations` is enabled
  (schema comes solely from `alembic upgrade head`); Flask's `rest-api`
  only auto-creates the schema for the isolated in-memory test database.
  Verified live end-to-end: `alembic revision --autogenerate`/`flask db
  migrate` now correctly detects and generates the initial `item`/
  `items` table for all four database/ORM combinations (FastAPI
  SQLModel + SQLAlchemy, Flask Flask-SQLAlchemy + SQLAlchemy), and
  `alembic upgrade head`/`flask db upgrade` applies cleanly against a
  real on-disk SQLite database. Both frameworks' generated README.md now
  correctly say the database is **not** auto-created on startup when
  migrations are enabled. This bug predates Flask — it was present in
  `fastapi/rest-api` since migrations shipped in `v0.3.0` — and is fixed
  in both places by this release.

## v0.8.0 — 2026-08-12

### Added

- **Flask is enabled as a second framework**, with both templates
  live-verified end-to-end:
  - **`flask/hello-world`** — the same shape as `fastapi/hello-world`,
    on a WSGI `Flask(__name__)` app. `-o config=true` and `--docker`
    behave identically.
  - **`flask/rest-api`** — the sync counterpart to `fastapi/rest-api`:
    `database` (none/sqlite/postgres), `orm`
    (flask-sqlalchemy/sqlalchemy), `migrations` (Flask-Migrate for
    flask-sqlalchemy, bare Alembic for sqlalchemy), `worker`
    (none/celery — Taskiq is async-first and doesn't fit Flask's sync
    model, so it's FastAPI-exclusive), `broker` (redis/rabbitmq), and
    `redis` (caching, independent of `broker` — same decoupling as
    `fastapi/rest-api`). Built on an application-factory pattern
    (`create_app()`, never instantiated at module scope), so importing
    the app module — which `pytest`/`flask db ...`/`alembic` all do —
    never opens a connection to the configured production database.
- **Per-framework `run_command`**: each framework's `template.json` now
  declares its own dev-server command, so the generated project's "Next
  steps" line prints the right one (`uv run flask --app
  src/{package}/main.py run` vs. `uv run fastapi dev
  src/{package}/main.py`) instead of always assuming FastAPI.

## v0.7.0 — 2026-08-12

### Added

- **`rest-api`: RabbitMQ as a message broker choice.** New `broker`
  option (`redis`/`rabbitmq`, default `redis`), asked whenever a worker
  is chosen. `redis` (the caching add-on) is now a fully independent
  question — previously it was always implied the moment *any* worker
  was picked, which conflated "a worker exists" with "the worker uses
  Redis." Now it's implied only when `broker == "redis"`; picking
  RabbitMQ leaves the standalone Redis-for-caching question open.
  Verified live end-to-end: real Taskiq (`taskiq-aio-pika`) and real
  Celery (built-in AMQP transport + `rpc://` result backend) against a
  real RabbitMQ broker, enqueue → execute round trip on both.
- **`.env.example`**: wherever a template writes a `.env` (`rest-api`
  always; `hello-world` with `-o config=true`), a `.env.example` with
  identical content is written alongside it — `.env` stays git-ignored,
  `.env.example` is the checked-in reference of what vars exist.

### Changed

- **Breaking (pre-1.0):** the `django` framework stub is removed from
  the roadmap entirely (it was always a disabled "coming soon" stub with
  no content). Flask remains the next committed framework — this isn't
  a scope increase, just dropping a placeholder that was never going to
  ship.

## v0.6.0 — 2026-08-12

### Changed

- **Breaking (pre-1.0):** the `restapi` template is renamed to
  `rest-api`, to match the hyphenated id style used elsewhere (e.g.
  `hello-world`) instead of being the odd one out. `--template restapi`
  is no longer recognized — use `--template rest-api`. Anything already
  remembered in `~/.flint/last.json` under the old `fastapi/restapi` key
  (§ v0.5.0) is simply never looked up again under the new id and falls
  back to the template's own defaults, same as any other stale entry —
  no manual migration needed.

## v0.5.0 — 2026-08-12

### Added

- **Remembered preferences** (`~/.flint/last.json`): after a successful
  generation, Flint saves the last framework, the last template picked
  per framework, and — per `<framework>/<template>` — the resolved
  options plus `docker`/`git`/`install`. The next run uses these as the
  new default: the interactive wizard preselects them, and a flagless
  `--yes`/non-TTY run falls back to them instead of the template's own
  hardcoded defaults. An explicit flag or `--option` always wins
  regardless of what's remembered, and a stale remembered value (a
  choice no longer valid for the current template) is silently ignored
  in favor of the template's own default rather than erroring.
- `--remember/--no-remember` flag (default on) to opt a single run out
  of both reading and writing `~/.flint/last.json` — for anyone who
  wants a fully stateless run.

### Changed

- Reading/writing `~/.flint/last.json` is entirely best-effort: a
  missing, corrupt, or unwritable prefs file never fails or warns during
  generation — it's silently treated as "nothing remembered yet."

## v0.4.0 — 2026-08-12

### Changed

**Breaking (pre-1.0):** the `restapi` template's generated project
layout is now opinionated, borrowed from how Next.js only enforces
structure for routing and leaves everything else as convention:

- `main.py` / `worker.py` — fixed-name entrypoints (unchanged in
  spirit, now documented as load-bearing rather than incidental).
- `routes/` / `tasks/` — "one module per resource/job" folders. Worker
  tasks moved from a single `tasks.py` to a `tasks/` package
  (`tasks/example.py` for the demo task) so a project can grow the same
  way `routes/` already does.
- `core/` — shared infrastructure, now including the database
  session/engine: `core/db.py` (was `db/session.py`). `core/config.py`
  and `core/redis.py` already lived here and are unchanged.
- `models.py` — ORM models moved to a top-level file (was
  `db/models.py`); deliberately **not** under `core/`, since domain
  models aren't cross-cutting infrastructure the way config/db-session/
  redis-client are — see `docs/PRODUCT_ARCH.md` §4.4 for the full
  reasoning. `schemas.py` (already top-level) is unaffected.
- `hello-world`'s optional `config` option follows suit:
  `core/config.py` instead of a top-level `config.py`, for consistency
  across templates.

No CLI-facing behavior changed — same flags, same `--option` keys, same
prompts. Only the shape of what gets generated.

### Fixed

- Re-verified live end-to-end after the restructure (real Alembic
  migrations against SQLite and PostgreSQL, real Taskiq and Celery
  workers against real Redis) and caught a template gap along the way:
  the Celery worker layer was missing its actual task file
  (`tasks/example.py`) — present for Taskiq, not for Celery. Fixed.

## v0.3.0 — 2026-08-12

### Added

- **Per-template options**: a template can now declare its own
  interactive prompts in `template.json` (`select`/`confirm`, with
  dependency-aware `when`/`skip_value` gating), resolved by
  `prompts.prompt_template_options` and surfaced non-interactively via
  a new repeatable `--option`/`-o key=value` flag. `generator.py`'s
  layer mechanism (previously hardcoded to `--docker`) is now equally
  data-driven — `--docker` is one gated layer among others.
- **`fastapi/restapi` template** — no longer a disabled stub. A layered
  REST API with `pydantic-settings` config always on, plus:
  - `database`: none (in-memory) / SQLite / PostgreSQL
  - `orm`: SQLModel / SQLAlchemy (skipped, no DB → no ORM prompt)
  - `migrations`: Alembic, async, autogenerate-ready (skipped without a DB)
  - `worker`: none / Taskiq / Celery, with a demo `/tasks/add` endpoint
  - `redis`: async client; implied automatically the moment a worker is chosen
  - Tests always run against an isolated, ephemeral SQLite database
    regardless of the configured production database — no external
    service needed to run `pytest`.
  - Verified live end-to-end: real PostgreSQL migrations and CRUD, real
    Taskiq and Celery workers against real Redis (enqueue → execute),
    and a working `docker build`/`docker run`.
- **`fastapi/hello-world` gains an optional `config` option**
  (`-o config=true` or the wizard prompt, default off): adds
  `pydantic-settings`-based configuration (`config.py`, `.env`) without
  changing the template's default zero-config shape.

### Changed

- **Breaking (pre-1.0):** the `ai` template (a disabled stub with no
  content) is removed. Revisit later with a deliberately small shape —
  one streaming completion endpoint + `pydantic-settings` for the
  provider key/model — rather than the RAG/agent-framework scope common
  in comparable tools.
- `generator._env` now sets `trim_blocks=True, lstrip_blocks=True`,
  simplifying every template's conditional blocks (no more manual
  `{%- -%}` trimming) — fixes whitespace bugs this surfaced in
  `hello-world`'s existing templates along the way.

### Fixed

Bugs caught only by actually running the generated tooling (not by
`uv sync && pytest` alone) — see `docs/PRODUCT_ARCH.md` §6.1 for the
full write-up of why each was invisible to lighter checks:

- restapi's `files/` layer was missing the top-level package
  `__init__.py`, which broke `fastapi dev`/`fastapi run`'s own
  directory-detection (namespace packages masked it for plain imports
  and pytest, but not for `fastapi_cli`).
- Alembic's `prepend_sys_path` needed to be `src`, not the default `.`,
  for a `src/`-layout project — otherwise `alembic revision
  --autogenerate` can't import the app's models.
- Taskiq/Celery workers pointed at `worker.py` never discovered tasks
  registered in `tasks.py` unless something imported it — fixed by
  importing `tasks` at the bottom of `worker.py`.
- `aiosqlite` was only a production dependency when `database ==
  "sqlite"`, but restapi's tests always use SQLite for isolation
  regardless of the configured database — a `database=postgres` project
  couldn't run its own test suite until `aiosqlite` became an
  unconditional dev dependency whenever a database is configured.

## v0.2.1 — 2026-08-12

### Fixed

- `generator.render` now rolls back a partially-written target directory
  when a `FlintError` (not just any other exception) is raised mid-render
  — previously that branch re-raised without cleaning up, breaking the
  documented all-or-nothing generation guarantee. Currently unreachable
  via any real input, but would have mattered the moment a future layer
  hook raised one.

### Changed

- Test suite now enforces 100% statement + branch coverage
  (`--cov-fail-under=100` in `pyproject.toml`, branch coverage on) —
  every module in `src/flint/` is fully covered, including the
  `python -m flint` entry points, `git`/`uv` subprocess failure paths,
  and every prompt cancellation branch.

## v0.2.0 — 2026-08-12

### Added

- `--docker/--no-docker` flag (and matching wizard prompt, default off):
  adds a `Dockerfile` and `.dockerignore` to the generated project. The
  `fastapi/hello-world` template's generated README gains a Docker
  section when used; the CLI summary prints `docker build`/`docker run`
  next steps.
- Every generated project now includes `AGENTS.md` — run/test commands,
  layout, and conventions for AI coding agents working in the repo.
  Always on, no flag.
- `templates/fastapi/hello-world/README.md` — maintainer docs for the
  template itself (not shipped to generated projects).

### Changed

- **Breaking (pre-1.0):** templates are now addressed as
  `--framework <id> --template <id>` (e.g. `--framework fastapi
  --template hello-world`) instead of a single combined
  `--framework fastapi-hello-world`. The wizard now asks framework and
  template as two separate steps. `restapi` and `ai` are listed as
  disabled ("coming soon") templates under `fastapi`; `flask` and
  `django` are listed as disabled frameworks — signaling the template
  roadmap the same way disabled frameworks already did.

## v0.1.0 — 2026-08-12

First release. `flint` scaffolds a runnable project from a short
interactive wizard, in the spirit of `create-react-app`/`create-next-app`.

### Added

- `flint` / `flint new [NAME]` — interactive wizard: project name,
  framework, git init, dependency install.
- Fully non-interactive mode via `--framework`, `--git/--no-git`,
  `--install/--no-install`, `--yes`, and `--force`; auto-detected when
  stdin isn't a TTY.
- `fastapi-hello-world` template: a `uv`-managed, `src/`-layout FastAPI
  project with a passing `pytest` test, ready to run with
  `uv run fastapi dev src/<package>/main.py`.
- `flint --version`.
- Project name validation: derives a filesystem-safe slug and a valid,
  importable Python package name; rejects empty/keyword/stdlib-shadowing
  names instead of silently mutating them.
- All-or-nothing generation: a failure mid-render rolls back any
  partially-written target directory.
- `docs/PRODUCT_SPEC.md`, `docs/PRODUCT_FLOW.md`, `docs/PRODUCT_ARCH.md`.
