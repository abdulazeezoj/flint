# Changelog

All notable changes to Flint are documented here.

Versions follow `v{release}.{feature}.{fixes}` (see `docs/PRODUCT_SPEC.md`
§10): `release` is the major epoch (starting at `0`), `feature` bumps for
new user-facing capability, `fixes` bumps for patches with no new
capability.

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
