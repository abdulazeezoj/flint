# Template: fastapi / hello-world

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A minimal, `uv`-managed FastAPI app: a `src/<package>/main.py` with one
`GET /` route returning `{"message": "Hello, World!"}`, a passing
`pytest` test, an `AGENTS.md`, and:

- with `--docker`: a `Dockerfile` + `.dockerignore`
- with `-o config=true`: `pydantic-settings`-based config (`config.py`,
  `.env` + `.env.example`), and `main.py` reads the app name/debug flag
  from `Settings` instead of hardcoding them

## Layout

```
template.json     id/label/description/enabled, options: [config], layers: [docker, config]
README.md         this file
files/             always rendered — plain app, no config
docker/            rendered in addition, only when --docker is passed
config/            rendered in addition, only when -o config=true;
                   overrides files/'s main.py to wire up Settings
```

## Rendering rules (see PRODUCT_ARCH.md §4 for the full mechanism)

- Both file/directory *names* and file *contents* are run through Jinja2.
  A path segment named `{{ "{{package_name}}" }}` becomes e.g. `my_api`.
- `*.jinja` files render and have the suffix stripped
  (`main.py.jinja` → `main.py`).
- `gitignore.jinja` → `.gitignore`, `dockerignore.jinja` → `.dockerignore`,
  `env.jinja` → `.env` (see `generator._RENAME_MAP` — dotfiles don't
  round-trip cleanly as literal source filenames in every packaging tool).
- A layer's files silently overwrite an earlier layer's files at the same
  relative path — that's how `config/src/{{package_name}}/main.py.jinja`
  replaces the plain one from `files/` when `config=true`.

## Available context (`Answers.context()`, see `generator.py`)

Fixed fields: `project_name`, `slug`, `package_name`, `framework`,
`template`, `git_init`, `install`, `docker`. Plus this template's own
option: `config` (bool, default `false`).

## Testing this template

`tests/test_generator.py` renders this template into a `tmp_path` (with
and without `config`/`docker`) and asserts the exact file set + spot-
checks substitutions. There's no automated check that the *generated*
project actually runs (that would require a real `uv sync` + network) —
that's verified manually before each release; see PRODUCT_ARCH.md §6.1
for bugs that level of check has caught in the past.

## Adding a new variant under `fastapi/`

Copy this directory, change `template.json`'s `id`/`label`/`description`,
set `enabled: false` until it's ready, and adjust `files/` (and any
option-gated layers). No code changes are needed elsewhere — the CLI and
generator discover variants, options, and layers by reading each
`template.json`. See `../rest-api/template.json` for an example with
multiple dependent options and several gated layers.
