# flint

`create-next-app`, for Python. One command, a short interactive wizard,
and you have a running project — no hand-written boilerplate. Pick a
richer template and the same wizard wires up a real database,
migrations, and a background worker too.

```
uvx flint
```

```
? What is your project named? my-api
? Which framework? FastAPI
? Which template? REST API
? Database? PostgreSQL
? ORM? SQLModel
? Add Alembic migrations? Yes
? Background worker? Taskiq
Using uv to manage dependencies.
? Add a Dockerfile? No
? Initialize a git repository? Yes
? Install dependencies with uv now? Yes

Options: database=postgres, orm=sqlmodel, migrations=True, worker=taskiq, broker=redis, redis=True
Creating my-api/ from fastapi/rest-api...
  ✔ ...
✔ Initialized git repository
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run alembic upgrade head
  uv run fastapi dev src/my_api/main.py
  uv run taskiq worker my_api.worker:broker --app-dir src   # separate process
```

## Install

```
uv tool install flint-cli   # persistent `flint` on PATH
# or run it ephemerally, no install:
uvx flint
```

## Usage

```
flint                                     # interactive wizard
flint new my-api                           # interactive, name pre-filled
flint new my-api \
  --framework fastapi --template rest-api \
  -o database=sqlite -o orm=sqlmodel \
  --docker --git --install --yes            # fully non-interactive, for scripts/CI
flint --version
flint --help
```

Every prompt has a matching flag: `--framework`, `--template`,
`--option`/`-o key=value` (repeatable — one per template-specific
choice, e.g. `-o database=postgres -o worker=celery`), `--docker/
--no-docker`, `--git/--no-git`, `--install/--no-install`, `--yes`
(accept all defaults), `--force` (generate into a non-empty dir).

Flint remembers your last framework/template and per-template choices in
`~/.flint/last.json`, and uses them as the new default the next time you
run it — both for what the wizard preselects and for what a flagless
`--yes`/CI run falls back to. An explicit flag or `--option` always wins
regardless of what's remembered. Pass `--no-remember` to opt a single run
out of both reading and writing that file.

## What v0 ships

A project is always generated from a `<framework>/<template>` pair — the
**framework** is the underlying library (FastAPI, Flask, ...), the
**template** is a specific project shape built on it (Hello World, REST
API, ...). A template can declare its own follow-up **options** — Flint
itself has no built-in notion of "database" or "worker," it just renders
whatever the chosen template's `template.json` declares. Today:

- **`fastapi/hello-world`** — a `uv`-managed, `src/`-layout FastAPI app
  with a passing test and an `AGENTS.md`, ready to run with no edits.
  `-o config=true` adds `pydantic-settings`-based configuration (`.env`
  + a checked-in `.env.example`). `--docker` adds a `Dockerfile` +
  `.dockerignore`.
- **`fastapi/rest-api`** — the same, plus real head-start choices:
  - `-o database=none|sqlite|postgres` (default: `sqlite`)
  - `-o orm=sqlmodel|sqlalchemy` (only asked with a database; default: `sqlmodel`)
  - `-o migrations=true|false` — async Alembic, autogenerate-ready (default: `true` with a database)
  - `-o worker=none|taskiq|celery`, with a demo `/tasks/add` endpoint
  - `-o broker=redis|rabbitmq` (only asked with a worker; default: `redis`)
  - `-o redis=true|false` — Redis for caching; implied whenever `broker == redis`, otherwise an independent choice
  - Tests always run against an isolated SQLite database, whatever
    production database was configured — `uv run pytest` never needs a
    real Postgres.

Flask is next on the roadmap; the wizard already lists it as
"coming soon". See `docs/PRODUCT_SPEC.md` for full v0
scope and non-goals.

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
minimal layout a new template needs, or `src/flint/templates/fastapi/
rest-api/template.json` for an example with options and gated layers.
