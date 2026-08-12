# Changelog

All notable changes to Flint are documented here.

Versions follow `v{release}.{feature}.{fixes}` (see `docs/PRODUCT_SPEC.md`
§11): `release` is the major epoch (starting at `0`), `feature` bumps for
new user-facing capability, `fixes` bumps for patches with no new
capability.

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
