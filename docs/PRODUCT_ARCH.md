# Flint — Architecture

**Status:** Draft for v0
**Owner:** Engineering
**Last updated:** 2026-08-12 (v0.2: framework/template split, `--docker`, AGENTS.md)

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

No cookiecutter/copier dependency: v0 ships one framework/template pair,
bundled in the package. Pulling in a full templating framework for that
is unnecessary weight; the template *system* (§4) is still designed so
that swapping in cookiecutter/copier — or a remote template registry —
later is a contained change, not a rewrite.

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
│       ├── cli.py               # Typer app, `new` command, flags
│       ├── prompts.py           # questionary wizard steps
│       ├── naming.py            # project name -> slug/package_name validation
│       ├── generator.py         # template renderer (fs walk + Jinja2)
│       ├── postgen.py           # git init, uv sync, summary printing
│       ├── errors.py            # FlintError and friends -> exit codes
│       └── templates/
│           ├── fastapi/
│           │   ├── template.json                # framework metadata
│           │   ├── hello-world/
│           │   │   ├── template.json             # variant metadata
│           │   │   ├── README.md                 # maintainer docs (not rendered)
│           │   │   ├── files/                    # always rendered
│           │   │   │   ├── pyproject.toml.jinja
│           │   │   │   ├── README.md.jinja
│           │   │   │   ├── AGENTS.md.jinja
│           │   │   │   ├── gitignore.jinja        # -> .gitignore
│           │   │   │   ├── src/
│           │   │   │   │   └── {{package_name}}/
│           │   │   │   │       ├── __init__.py.jinja
│           │   │   │   │       └── main.py.jinja
│           │   │   │   └── tests/
│           │   │   │       └── test_main.py.jinja
│           │   │   └── docker/                   # only rendered if --docker
│           │   │       ├── Dockerfile.jinja
│           │   │       └── dockerignore.jinja     # -> .dockerignore
│           │   ├── restapi/template.json          # disabled stub — roadmap
│           │   └── ai/template.json                # disabled stub — roadmap
│           ├── flask/template.json                  # disabled stub — roadmap
│           └── django/template.json                 # disabled stub — roadmap
├── tests/
│   ├── test_naming.py
│   ├── test_generator.py
│   ├── test_prompts.py
│   └── test_cli.py
├── pyproject.toml
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## 4. Template system design

Templates are organized two levels deep: `templates/<framework>/<template>/`
(PRODUCT_SPEC §3 defines the framework-vs-template distinction). A
**framework** directory (`templates/fastapi/`) has its own
`template.json` and one subdirectory per **template** variant
(`hello-world/`, `restapi/`, `ai/`), each with its own `template.json`.
Disabled entries (`restapi`, `ai`, `flask`, `django`) are stubs — just a
`template.json` with `"enabled": false`, no `files/` — that exist purely
so the wizard/CLI can list them as "coming soon" (PRODUCT_FLOW §2 steps
3–4) without any code changes.

Each enabled template variant contains:

- `template.json` — metadata: `id`, `label`, `description`, `enabled`.
- `README.md` (optional) — maintainer-facing docs for the template
  itself; lives at the template root (sibling to `files/`), so it is
  **not** picked up by the renderer (only `files/` and `docker/` are
  rendered) and never ships in a generated project.
- `files/` — the base file tree, always rendered.
- `docker/` (optional) — an extra layer rendered *in addition to*
  `files/`, only when `Answers.docker` is true. If a template has no
  `docker/` directory, `--docker` is a no-op warning rather than an
  error (PRODUCT_FLOW §5) — `TemplateMeta.supports_docker` checks for
  the directory's existence.

Within any layer, both **file/directory names** and **file contents**
are run through Jinja2:
- A path segment literally named `{{package_name}}` becomes e.g.
  `my_api`.
- `*.jinja` file extensions are stripped after rendering
  (`main.py.jinja` → `main.py`); files without `.jinja` are copied
  verbatim (for binary/static assets, none needed in v0).
- `gitignore.jinja` renders to `.gitignore`, `dockerignore.jinja` to
  `.dockerignore` — an explicit rename table in `generator.py`
  (`_RENAME_MAP`) sidesteps packaging tools that mishandle literal
  leading-dot filenames in source control / sdists.

Render context (the "answers" passed to every template):

```python
class Answers(BaseModel):
    project_name: str      # raw user input, "My Api"
    slug: str               # "my-api" — directory / distribution name
    package_name: str       # "my_api" — importable package name
    framework: str          # "fastapi"
    template: str            # "hello-world"
    git_init: bool
    install: bool
    docker: bool
```

`generator.render(framework_id, template_id, target_dir, answers, force=False)`:
1. Resolve the framework, then the template within it; verify both
   `enabled`.
2. Refuse if `target_dir` exists and is non-empty, unless `force=True`.
3. Build the layer list: `["files"]`, plus `["docker"]` if
   `answers.docker` and `template.supports_docker`.
4. For each layer, walk its directory (`rglob`, deterministic sorted
   order); for each file, render the *path itself* through Jinja2,
   render *contents* through Jinja2, write to `target_dir`.
5. On any exception: remove everything written so far under `target_dir`
   before re-raising (all-or-nothing generation, per PRODUCT_FLOW §5).
6. Return the sorted list of created paths (used for the CLI summary;
   `postgen.print_summary` checks for `Path("Dockerfile")` in it to
   decide whether to print Docker next-steps).

This keeps "add a new template" to: add a directory + `template.json`
(+ optionally `docker/`), no changes to `generator.py`. Adding a new
*framework* is the same, one level up. Adding Flask/restapi/ai for real
in `v0.x` is purely a content change (swap `enabled: false` → `true` and
fill in `files/`), not an architecture change.

## 5. CLI flow → code mapping

| PRODUCT_FLOW step | Module |
|---|---|
| Entry points, flag parsing | `cli.py` (Typer app; `new` command; bare `flint` invokes `new` via Typer's default-command pattern) |
| Interactive prompts | `prompts.py` — one function per step, each accepting a pre-supplied flag value and skipping its own prompt if set or if `--yes`/non-TTY. `prompt_framework`/`prompt_template` share a `_select_enabled` helper (identical shape: pick one enabled entry from a list, flag short-circuits, non-interactive picks the first enabled). |
| Name validation | `naming.py` — pure functions, no I/O, exhaustively unit tested |
| Directory existence check | `generator.py` (single source of truth, both interactive and non-interactive paths call it) |
| File generation | `generator.py` |
| git init / uv sync | `postgen.py` — each step wrapped so a missing `git`/`uv` binary warns and continues rather than raising |
| Summary / next steps | `postgen.py` (`print_summary`), using `rich` |
| Exit codes | `errors.py` defines `FlintUserError` (→1) and lets anything else bubble to Typer's default handler (→2); the top-level command wraps generation in a `try/except FlintUserError` |

TTY detection for non-interactive mode: `sys.stdin.isatty()`, overridable
by explicit `--yes`.

`--docker` support-check ordering: `cli.py` picks the template first,
then calls `prompts.prompt_docker`, then — if docker was requested but
`chosen_template.supports_docker` is false — downgrades to
`docker=False` with a warning *before* calling `generator.render`, so
the render context (`Answers.docker`) always matches what was actually
generated (a template's own `files/README.md.jinja` can safely branch on
`{% if docker %}` without knowing about the fallback).

## 6. Testing strategy

`pytest` runs with `--cov=flint --cov-report=term-missing
--cov-fail-under=100` by default (`[tool.pytest.ini_options]` in
`pyproject.toml`), with branch coverage on
(`[tool.coverage.run] branch = true`) — the suite fails the moment any
line *or* branch in `src/flint/` goes uncovered, not just when a whole
function is untested. `uv run pytest` is enough to check both tests and
coverage locally.

- `test_naming.py` — table-driven tests of the slugify/package-name
  rules (keywords, leading digits, unicode, empty string, etc.), plus one
  test that forces the defensive non-identifier guard in
  `validate_project_name` (unreachable via real input — `slugify`/
  `package_name_from_slug` only ever produce valid identifiers — so it's
  exercised by monkeypatching `package_name_from_slug` directly).
- `test_generator.py` — renders `fastapi/hello-world` into a `tmp_path`
  (with and without `docker=True`), asserts exact expected file set and
  spot-checks rendered content (e.g. `package_name` substitution landed
  correctly, the README's Docker section only appears when requested);
  asserts the non-empty-directory guard, disabled-framework/-template
  rejection, the rollback-on-failure behavior (including that a
  `FlintError` raised mid-render still rolls back, and that a
  pre-existing `--force` target directory is *never* deleted), the
  verbatim-copy path for non-`.jinja` files, and that `list_frameworks`/
  `list_templates` skip directory entries with no `template.json`.
- `test_prompts.py` — monkeypatches `questionary`'s `.ask()` calls (it
  drives a real TTY via `prompt_toolkit`, which can't be exercised
  through Typer's `CliRunner`) to cover the interactive branches:
  select/confirm happy paths, re-prompt on invalid input, flag
  short-circuiting, cancellation (every prompt function, not just
  project name).
- `test_cli.py` — Typer's `CliRunner`, covering: full non-interactive
  happy path (with and without `--docker`), `--version`, `--help`,
  existing-directory error, invalid name, unknown/disabled
  framework/template, `--docker` requested against a template that
  doesn't support it, a `typer.Exit` raised mid-flow passing through
  unchanged, and an unexpected exception mapping to exit code 2. The
  fully-interactive path (including the "Using uv..." message) is
  exercised by calling `cli._run_new` directly with `sys.stdin` patched
  and `questionary` stubbed, rather than through `CliRunner` — Click's
  `CliRunner.invoke()` swaps `sys.stdin` out for its own stream for the
  duration of the call, which would clobber an `isatty()` patch made
  beforehand. Tests that don't need the real subprocesses (bare
  invocation, the interactive path) monkeypatch `postgen.git_init` /
  `install_dependencies` so the suite makes no real subprocess or
  network calls.
- `test_postgen.py` — `git_init`/`install_dependencies` directly, with
  `subprocess.run` monkeypatched: binary-not-found, success, and
  `CalledProcessError` for each.
- `test_main.py` — covers the `python -m flint` / `python -m flint.cli`
  entry-point guards via `runpy.run_module(..., run_name="__main__")`
  (executes in-process, unlike `subprocess`, so `coverage.py` sees it),
  plus a plain `import flint.__main__` to cover the guard's
  not-taken branch.
- End-to-end smoke test (manual for v0, candidate for CI later): actually
  run generated output through `uv sync && uv run pytest`, and — with
  `--docker` — `docker build`/`docker run` + a live request, to confirm
  the *template* itself is a valid, passing, deployable project. This is
  a property of the template content, not of Flint's own code, and
  isn't part of the 100% coverage gate, but it's the ultimate acceptance
  check for the spec's "zero manual edits" goal.

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
- `.agents/skills/<framework>` — a directory of framework-specific,
  agent-consumable skills shipped into generated projects. Deferred per
  PRODUCT_SPEC §12: needs real content and a target skill format/consumer
  decided, not just plumbing. `AGENTS.md` (§4, always-on) ships now as
  the lightweight version of "give agents context."
- `--force` overwrite confirmation UX polish, `flint list-templates`
  introspection command.
