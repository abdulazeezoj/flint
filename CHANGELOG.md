# Changelog

All notable changes to Flint are documented here.

Versions follow `v{release}.{feature}.{fixes}` (see `docs/PRODUCT_SPEC.md`
§11): `release` is the major epoch (starting at `0`), `feature` bumps for
new user-facing capability, `fixes` bumps for patches with no new
capability.

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
