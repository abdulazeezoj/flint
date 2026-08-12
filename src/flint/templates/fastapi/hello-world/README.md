# Template: fastapi / hello-world

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A minimal, `uv`-managed FastAPI app: a `src/<package>/main.py` with one
`GET /` route returning `{"message": "Hello, World!"}`, a passing
`pytest` test, an `AGENTS.md`, and (with `--docker`) a `Dockerfile`.

## Layout

```
template.json     framework-scoped id/label/description/enabled
README.md         this file
files/             rendered into every generated project
docker/            rendered in addition, only when --docker is passed
```

## Rendering rules (see PRODUCT_ARCH.md §4 for the full mechanism)

- Both file/directory *names* and file *contents* are run through Jinja2.
  A path segment named `{{ "{{package_name}}" }}` becomes e.g. `my_api`.
- `*.jinja` files render and have the suffix stripped
  (`main.py.jinja` → `main.py`).
- `gitignore.jinja` → `.gitignore`, `dockerignore.jinja` → `.dockerignore`
  (see `generator._RENAME_MAP` — dotfiles don't round-trip cleanly as
  literal source filenames in every packaging tool).

## Available context (`Answers`, see `generator.py`)

`project_name`, `slug`, `package_name`, `framework`, `template`,
`git_init`, `install`, `docker`.

## Testing this template

`tests/test_generator.py` renders this template into a `tmp_path` and
asserts the exact file set + spot-checks substitutions. There's no
automated check that the *generated* project actually runs (that would
require a real `uv sync` + network) — that's verified manually before
each release; see the release checklist in `docs/PRODUCT_ARCH.md`.

## Adding a new variant under `fastapi/`

Copy this directory, change `template.json`'s `id`/`label`/`description`,
set `enabled: false` until it's ready, and adjust `files/` (and
`docker/`, if applicable). No code changes are needed elsewhere — the
CLI and generator discover variants by walking the framework's
directory.
