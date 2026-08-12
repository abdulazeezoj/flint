# flint

`create-next-app`, for Python. One command, a short interactive wizard,
and you have a running project — no hand-written boilerplate.

```
uvx flint
```

```
? What is your project named? my-api
? Which framework? FastAPI
? Which template? Hello World
Using uv to manage dependencies.
? Add a Dockerfile? No
? Initialize a git repository? Yes
? Install dependencies with uv now? Yes

Creating my-api/ from fastapi/hello-world...
  ✔ AGENTS.md
  ✔ pyproject.toml
  ✔ README.md
  ✔ .gitignore
  ✔ src/my_api/__init__.py
  ✔ src/my_api/main.py
  ✔ tests/test_main.py
✔ Initialized git repository
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run fastapi dev src/my_api/main.py

Then open http://127.0.0.1:8000
```

## Install

```
uv tool install flint-cli   # persistent `flint` on PATH
# or run it ephemerally, no install:
uvx flint
```

## Usage

```
flint                            # interactive wizard
flint new my-api                  # interactive, name pre-filled
flint new my-api \
  --framework fastapi --template hello-world \
  --docker --git --install --yes  # fully non-interactive, for scripts/CI
flint --version
flint --help
```

Every prompt has a matching flag: `--framework`, `--template`,
`--docker/--no-docker`, `--git/--no-git`, `--install/--no-install`,
`--yes` (accept all defaults), `--force` (generate into a non-empty dir).

## What v0 ships

A project is always generated from a `<framework>/<template>` pair — the
**framework** is the underlying library (FastAPI, Flask, ...), the
**template** is a specific project shape built on it (Hello World, REST
API, ...). Today:

- **`fastapi/hello-world`** — a `uv`-managed, `src/`-layout FastAPI app
  with a passing test and an `AGENTS.md`, ready to run with no edits.
  Pass `--docker` for a `Dockerfile` + `.dockerignore` too.

More frameworks (Flask, Django) and templates (REST API, AI App) are on
the roadmap; the wizard already lists them as "coming soon". See
`docs/PRODUCT_SPEC.md` for full v0 scope and non-goals.

## Docs

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — vision, scope, requirements
- [`docs/PRODUCT_FLOW.md`](docs/PRODUCT_FLOW.md) — exact wizard/CLI behavior
- [`docs/PRODUCT_ARCH.md`](docs/PRODUCT_ARCH.md) — technical design
- [`CHANGELOG.md`](CHANGELOG.md) — release history

## Development

```
uv sync
uv run pytest       # also runs coverage — the suite fails under 100%
uv run flint --help
```

Adding a framework or template is a content-only change — no code edits
needed. See `src/flint/templates/fastapi/hello-world/README.md` for the
layout a new template directory needs.
