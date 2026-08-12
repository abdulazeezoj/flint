# Flint — Architecture

**Status:** Draft for v0
**Owner:** Engineering
**Last updated:** 2026-08-12

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

No cookiecutter/copier dependency: v0 ships exactly one template, bundled
in the package. Pulling in a full templating framework for one template
is unnecessary weight; the template *system* (§4) is still designed so
that swapping in cookiecutter/copier — or a remote template registry —
later is a contained change, not a rewrite.

## 2. Distribution

- PyPI distribution name: `flint-cli` (see PRODUCT_SPEC §9 for why).
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
│           └── fastapi_hello_world/
│               ├── template.json                       # template metadata
│               └── files/
│                   ├── pyproject.toml.jinja
│                   ├── README.md.jinja
│                   ├── gitignore.jinja                  # -> .gitignore (dotfiles can't ship as literal dotfiles cleanly in all tooling)
│                   ├── src/
│                   │   └── {{package_name}}/
│                   │       ├── __init__.py.jinja
│                   │       └── main.py.jinja
│                   └── tests/
│                       └── test_main.py.jinja
├── tests/
│   ├── test_naming.py
│   ├── test_generator.py
│   └── test_cli.py
├── pyproject.toml
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## 4. Template system design

Each template is a directory under `src/flint/templates/<template_id>/`
containing:

- `template.json` — metadata: `id`, `label`, `description`, `enabled`
  (lets Flask/Django be *listed but disabled* per PRODUCT_FLOW §2 step 3
  without any code beyond adding the JSON + a "coming soon" flag).
- `files/` — the literal file tree to render. Both **file/directory
  names** and **file contents** are run through Jinja2:
  - A path segment literally named `{{package_name}}` becomes e.g.
    `my_api`.
  - `*.jinja` file extensions are stripped after rendering
    (`main.py.jinja` → `main.py`); files without `.jinja` are copied
    verbatim (for binary/static assets, none needed in v0).
  - `gitignore.jinja` renders to `.gitignore` — an explicit rename table
    in `generator.py` (`{"gitignore.jinja": ".gitignore"}`) sidesteps
    packaging tools that mishandle literal leading-dot filenames in
    source control / sdists.

Render context (the "answers" passed to every template):

```python
class Answers(BaseModel):
    project_name: str      # raw user input, "My Api"
    slug: str               # "my-api" — directory / distribution name
    package_name: str       # "my_api" — importable package name
    framework: str          # "fastapi"
    git_init: bool
    install: bool
```

`generator.render(template_id, target_dir, answers)`:
1. Resolve template directory, load `template.json`, verify `enabled`.
2. Refuse if `target_dir` exists and is non-empty, unless `force=True`.
3. Walk `files/` (`os.walk`, deterministic sorted order).
4. For each path: render the *path itself* through Jinja2, render
   *contents* through Jinja2 (skip binary files by extension allowlist —
   none in v0, forward-compatible), write to `target_dir`.
5. On any exception: remove everything written so far under `target_dir`
   before re-raising (all-or-nothing generation, per PRODUCT_FLOW §5).
6. Return the list of created paths (used for the CLI summary).

This keeps "add a new template" to: add a directory + `template.json`,
no changes to `generator.py`. Adding Flask in `v0.x` is purely a content
change, not an architecture change — satisfies the non-goal in the spec
about not blocking future frameworks.

## 5. CLI flow → code mapping

| PRODUCT_FLOW step | Module |
|---|---|
| Entry points, flag parsing | `cli.py` (Typer app; `new` command; bare `flint` invokes `new` via Typer's default-command pattern) |
| Interactive prompts | `prompts.py` — one function per step, each accepting a pre-supplied flag value and skipping its own prompt if set or if `--yes`/non-TTY |
| Name validation | `naming.py` — pure functions, no I/O, exhaustively unit tested |
| Directory existence check | `generator.py` (single source of truth, both interactive and non-interactive paths call it) |
| File generation | `generator.py` |
| git init / uv sync | `postgen.py` — each step wrapped so a missing `git`/`uv` binary warns and continues rather than raising |
| Summary / next steps | `postgen.py` (`print_summary`), using `rich` |
| Exit codes | `errors.py` defines `FlintUserError` (→1) and lets anything else bubble to Typer's default handler (→2); the top-level command wraps generation in a `try/except FlintUserError` |

TTY detection for non-interactive mode: `sys.stdin.isatty()`, overridable
by explicit `--yes`.

## 6. Testing strategy

- `test_naming.py` — table-driven tests of the slugify/package-name
  rules (keywords, leading digits, unicode, empty string, etc.).
- `test_generator.py` — renders the `fastapi_hello_world` template into a
  `tmp_path`, asserts exact expected file set and spot-checks rendered
  content (e.g. `package_name` substitution landed correctly); asserts
  the non-empty-directory guard and the rollback-on-failure behavior.
- `test_cli.py` — Typer's `CliRunner`, covering: full non-interactive
  happy path, `--version`, `--help`, existing-directory error, invalid
  name error. Interactive-prompt paths are exercised by feeding
  `questionary`'s prompt functions through monkeypatching rather than
  driving a real TTY.
- End-to-end smoke test (manual for v0, candidate for CI later): actually
  run generated output through `uv run pytest` inside the generated
  project to confirm the *template* itself is a valid, passing project —
  this is a property of the template content, not of Flint's own code,
  but it's the ultimate acceptance check for the spec's "zero manual
  edits" goal.

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
  `generator.render(template_id, ...)` interface — `template_id` could
  become a path/URL instead of a bundled-package lookup without changing
  callers).
- Package-manager choice (pip/poetry) — `postgen.py`'s install step is
  already isolated behind one function, swappable per `Answers.pm` if
  that field is ever added.
- `--force` overwrite confirmation UX polish, `flint list-templates`
  introspection command.
