# Template: fastapi / restapi

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A layered FastAPI REST API. `pydantic-settings` config is always on
(unlike `hello-world`, where it's optional) — this template exists to
demonstrate the shape past "hello world." A single `items` resource
(`GET/POST /items/`, `GET/DELETE /items/{id}`) backed by an in-memory
store by default, or a real database if one is chosen.

## Options (`template.json`, resolved in this order)

| key | type | default | depends on | notes |
|---|---|---|---|---|
| `database` | select | `sqlite` | — | `none`, `sqlite`, `postgres` |
| `orm` | select | `sqlmodel` | `database != none` | `sqlmodel`, `sqlalchemy`; skip_value `"none"` |
| `migrations` | confirm | `true` | `database != none` | skip_value `false` |
| `worker` | select | `none` | — | `none`, `taskiq`, `celery` |
| `redis` | confirm | `false` | `worker == none` | skip_value `true` — implied the moment a worker is chosen |

## Layout

```
template.json            options + layers (see below)
README.md                this file
files/                    always rendered — in-memory CRUD, config, schemas
docker/                   iff --docker
db-sqlmodel/              iff orm == sqlmodel — overrides routes/items.py, adds db/
db-sqlalchemy/            iff orm == sqlalchemy — same shape, SQLAlchemy Core/ORM
migrations-sqlmodel/      iff migrations && orm == sqlmodel — async Alembic
migrations-sqlalchemy/    iff migrations && orm == sqlalchemy
worker-taskiq/            iff worker == taskiq — worker.py, tasks.py
worker-celery/            iff worker == celery — same shape, Celery
redis/                    iff redis resolves true — core/redis.py client
```

`main.py` (in `files/`) is a deliberate exception to "layers own whole
files, not `{% if %}`": both a database and a worker need to touch its
startup wiring (DB init, Taskiq's `broker.startup()`/`shutdown()` in a
`lifespan`), and only a worker adds the demo `/tasks/add` endpoint. See
PRODUCT_ARCH.md §4.2 for why this file stays inline-conditional while
`routes/items.py`, `db/session.py`, etc. are full layer overrides.

## Two real gotchas baked into this template — don't regress them

See PRODUCT_ARCH.md §6.1 for the full incident write-ups; the short
version, since it's easy to "fix" these back in accidentally:

1. **`files/src/{{package_name}}/__init__.py.jinja` must exist.**
   Without it, plain Python imports and pytest still work (namespace
   packages), but `fastapi dev`/`fastapi run`'s own directory-detection
   silently breaks.
2. **`alembic.ini`'s `prepend_sys_path = src`**, not `.` — needed so
   `alembic revision --autogenerate` can import the app's models from
   the `src/`-layout package.
3. **`worker.py` imports `tasks` at the bottom**, after `broker`/
   `celery_app` is defined — the worker CLI only discovers
   `@broker.task`/`@celery_app.task`-decorated functions by importing
   the module that defines them, and pointing the worker CLI at
   `worker.py` doesn't transitively pull in `tasks.py` on its own.

## Testing this template

`tests/test_generator.py` has a dedicated block of `restapi`-specific
tests: in-memory, SQLite+SQLModel+migrations, Postgres+SQLAlchemy,
Taskiq, Celery, Redis-standalone, and "all features combined." Each
asserts the right files exist/don't and runs every generated `.py` file
through `ast.parse()` plus `pyproject.toml` through `tomllib.loads()`.

That catches template bugs but **not** the three gotchas above (imports
succeed, syntax is valid, TOML parses — none of that exercises
`fastapi_cli`'s path detection, a real Alembic run, or a real worker
process). Before shipping a change to this template, manually verify at
least one combination end-to-end: `uv sync`, `uv run pytest`, and — if
you touched migrations or the worker — a real `alembic revision
--autogenerate` + `upgrade head`, and a real worker boot + task enqueue.
SQLite needs no external service and is enough for the DB/migrations
check; the worker check needs a local Redis (`redis-server`, no Docker
required).

## Adding a new option or layer

Add an entry to `template.json`'s `options`/`layers` arrays and the
corresponding files — no code changes in `generator.py`/`prompts.py`/
`cli.py` are needed. Keep option declaration order meaningful: a later
option's `when` can only reference **earlier** options' resolved values
(see PRODUCT_ARCH.md §4).
