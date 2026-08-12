# Template: flask / hello-world

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A minimal, `uv`-managed Flask app: a `src/<package>/main.py` with one
`GET /` route returning `{"message": "Hello, World!"}`, a passing
`pytest` test (via `app.test_client()`), an `AGENTS.md`, and:

- with `--docker`: a `Dockerfile` + `.dockerignore`
- with `-o config=true`: `pydantic-settings`-based config (`config.py`,
  `.env` + `.env.example`), and `main.py` reads the app name/debug flag
  from `Settings` instead of hardcoding them

This is the Flask equivalent of `fastapi/hello-world` — same shape,
same options, same layer structure — so a developer switching between
flint-generated frameworks finds the same landmarks (`main.py`,
`AGENTS.md`, the `config` option, the `docker` layer).

## Layout

```
template.json     id/label/description/enabled, options: [config], layers: [docker, config]
README.md         this file
files/             always rendered — plain app, no config
docker/            rendered in addition, only when --docker is passed
config/            rendered in addition, only when -o config=true;
                   overrides files/'s main.py to wire up Settings
```

## Design decisions (where this deviates from a literal 1:1 mirror of fastapi/hello-world)

- **No app-factory pattern.** `main.py` is a plain module-level
  `app = Flask(__name__)`, exactly mirroring `fastapi/hello-world`'s
  module-level `app = FastAPI(...)` — no `create_app()` factory. Flask's
  own docs treat the factory pattern as something you reach for once an
  app needs multiple configurations/instances (testing config, multiple
  deployments, extensions with `init_app()`); a one-route hello-world
  doesn't need it, and consistency with the FastAPI template (which
  also skips this kind of indirection) matters more here than showing
  off a pattern this template doesn't need yet. `rest-api`'s Flask
  variant is free to reconsider this once there's more to configure.
- **Entrypoint is still `main.py`, not `app.py`/`wsgi.py`.** Flask
  tutorials often use `app.py`; flint uses `main.py` everywhere
  (PRODUCT_ARCH.md §4.4 — "strictly opinionated" entrypoint naming) so
  the landmark file is identical across frameworks.
- **Route returns a plain `dict`, not `flask.jsonify(...)`.** Flask
  (>=1.1) auto-serializes a returned `dict`/`list` to a JSON response
  with the right `Content-Type` — this mirrors FastAPI's own plain-dict
  return exactly, so the two templates' `main.py` read almost
  identically side by side.
- **`flask run` invocation**: because this is a `src/`-layout project
  and `[tool.uv] package = false` (no editable install of the project
  itself — same as fastapi/hello-world), `{{ package_name }}` is not
  necessarily importable from the repo root. Flask's own `--app` flag
  accepts either an import path (`pkg.main`) or a file path
  (`src/pkg/main.py`, or extension-less `src/pkg/main`) and in the
  file-path form it correctly resolves the package for absolute imports
  inside that file too (verified locally, including the `config=true`
  variant where `main.py` does `from {{ package_name }}.core.config
  import settings`). So the documented run command is:
  `uv run flask --app src/{{ package_name }}/main run` — this is the
  one command verified to actually boot the app and serve `GET /`,
  not a guess.
- **WSGI server in Docker: `gunicorn`, not `flask run`.** Flask's own
  dev server prints a warning against production use; unlike FastAPI
  (whose `fastapi run` *is* a production-appropriate Uvicorn wrapper),
  Flask has no such built-in, so the container's `CMD` uses `gunicorn`
  instead. Because the project is `src/`-layout and not editable-
  installed, gunicorn is invoked with `--chdir src` so `{{ package_name
  }}.main:app` resolves correctly:
  `gunicorn --chdir src --bind 0.0.0.0:8000 {{ package_name }}.main:app`
  — also verified locally against a real generated-shape package before
  being written into the Dockerfile. `gunicorn` is therefore only added
  to `dependencies` when `docker=true` (see `files/pyproject.toml.jinja`)
  — no point pulling in a production WSGI server for projects that never
  asked for a container.
- **Config wiring differs slightly from FastAPI's, because Flask's
  constructor differs.** FastAPI's `FastAPI(title=...)` takes a display
  name directly. Flask's constructor's first argument is the *import
  name* (used for resource/template/static-folder resolution) and must
  stay `__name__` — passing `settings.app_name` there instead would be a
  bug, not a config feature. So `config/src/{{ package_name
  }}/main.py.jinja` keeps `Flask(__name__)` and instead stores the
  configured values on `app.config["APP_NAME"]` / `app.config["DEBUG"]`
  — `DEBUG` is a real Flask config key Flask itself reads (e.g. for
  the reloader/debugger when run via `flask run --debug` or
  `app.config["DEBUG"]` combined with `app.run(debug=...)`); `APP_NAME`
  is just a place to keep the settings-driven value visible/available to
  route code, the closest Flask idiom to FastAPI's `title=`.

## Rendering rules (see PRODUCT_ARCH.md §4 for the full mechanism)

- Both file/directory *names* and file *contents* are run through Jinja2.
  A path segment named `{{ "{{package_name}}" }}` becomes e.g. `my_api`.
- `*.jinja` files render and have the suffix stripped
  (`main.py.jinja` → `main.py`).
- `gitignore.jinja` → `.gitignore`, `dockerignore.jinja` → `.dockerignore`,
  `env.jinja` → `.env` (see `generator._RENAME_MAP` — dotfiles don't
  round-trip cleanly as literal source filenames in every packaging tool).
  `.env` also automatically gets a sibling `.env.example` with identical
  content (`generator.py`'s `_render_layer` — templates only author one
  `env.jinja`).
- A layer's files silently overwrite an earlier layer's files at the same
  relative path — that's how `config/src/{{package_name}}/main.py.jinja`
  replaces the plain one from `files/` when `config=true`.
- No Docker Compose anything — one optional `Dockerfile` is the entire
  Docker story for this template, matching every other template in the
  repo (PRODUCT_SPEC §5: a generated `docker-compose.yml` bakes in a
  container-topology opinion that doesn't fit every project shape).

## Available context (`Answers.context()`, see `generator.py`)

Fixed fields: `project_name`, `slug`, `package_name`, `framework`,
`template`, `git_init`, `install`, `docker`. Plus this template's own
option: `config` (bool, default `false`).

## Testing this template

`tests/test_flask_hello_world.py` (repo root `tests/`, not this
directory — kept in its own file rather than appended to
`test_generator.py` to avoid a merge conflict with the parallel
`flask/rest-api` template's own new test file) renders this template
into a `tmp_path` (with and without `config`/`docker`) and asserts the
exact file set + spot-checks substitutions, mirroring the coverage
`test_generator.py` has for `fastapi/hello-world`. There's no automated
check that the *generated* project actually runs (that would require a
real `uv sync` + network) — that's verified manually before each
release; see PRODUCT_ARCH.md §7/§7.1 for bugs that level of check has
caught in the past (this template's `flask run`/`gunicorn` invocations
above were themselves verified this way while building it).

## Adding a new variant under `flask/`

Copy this directory, change `template.json`'s `id`/`label`/`description`,
set `enabled: false` until it's ready, and adjust `files/` (and any
option-gated layers). No code changes are needed elsewhere — the CLI and
generator discover variants, options, and layers by reading each
`template.json`. See `../../fastapi/rest-api/template.json` for an
example with multiple dependent options and several gated layers.
