# Template: fastapi / rest-api

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A layered FastAPI REST API with an opinionated, Next.js-inspired
layout (PRODUCT_ARCH.md §4.4): `main.py`/`worker.py` are fixed
entrypoints, `routes/`/`tasks/` are "one file per resource/job" folders,
`core/` holds shared infrastructure — everything else (`schemas.py`,
`models.py`) is a reasonable default, not an enforced convention.
`pydantic-settings` config is always on (unlike `hello-world`, where
it's optional) — this template exists to demonstrate the shape past
"hello world." A single `items` resource (`GET/POST /items/`,
`GET/DELETE /items/{id}`) backed by an in-memory store by default, or a
real database if one is chosen.

## Options (`template.json`, resolved in this order)

| key | type | default | depends on | notes |
|---|---|---|---|---|
| `database` | select | `sqlite` | — | `none`, `sqlite`, `postgres` |
| `orm` | select | `sqlmodel` | `database != none` | `sqlmodel`, `sqlalchemy`; skip_value `"none"` |
| `migrations` | confirm | `true` | `database != none` | skip_value `false` |
| `worker` | select | `none` | — | `none`, `taskiq`, `celery` |
| `broker` | select | `redis` | `worker != none` | `redis`, `rabbitmq`; skip_value `"none"` when no worker |
| `redis` | confirm | `false` | `broker != redis` | skip_value `true` — implied whenever `broker == "redis"`; otherwise an independent "add Redis for caching" question, so `broker == "rabbitmq"` doesn't preclude also wanting Redis for caching |

## Layout (of this template's directory, not the generated project)

```
template.json            options + layers (see below)
README.md                this file
files/                    always rendered — main.py, core/config.py, schemas.py,
                          routes/items.py (in-memory), tests/test_main.py,
                          env.jinja (renders to both .env and .env.example)
docker/                   iff --docker
db-sqlmodel/              iff orm == sqlmodel — overrides routes/items.py,
                          adds core/db.py + top-level models.py
db-sqlalchemy/            iff orm == sqlalchemy — same shape, SQLAlchemy Core/ORM
migrations-sqlmodel/      iff migrations && orm == sqlmodel — async Alembic
migrations-sqlalchemy/    iff migrations && orm == sqlalchemy
worker-taskiq/            iff worker == taskiq — worker.py, tasks/example.py;
                          worker.py itself branches on `broker` (redis/rabbitmq)
worker-celery/            iff worker == celery — same shape, Celery; same
                          broker-branching in worker.py
redis/                    iff redis resolves true — core/redis.py client
```

There's no `broker-rabbitmq/` layer — RabbitMQ needs no app-level client
the way Redis does (`redis_client`, reused for caching). It's purely
internal to `worker.py` (via `taskiq-aio-pika`/Celery's built-in AMQP
transport), so the only RabbitMQ-specific content is a few `{% if broker
== "rabbitmq" %}` branches in `worker.py.jinja`/`config.py.jinja`/
`env.jinja`/`pyproject.toml.jinja` — not worth a whole layer for.

The **generated project's** layout (what a developer actually sees) is:

```
src/{{package_name}}/
  main.py              FastAPI entrypoint — fixed name/location
  worker.py            {worker} entrypoint — fixed name/location (iff a worker is chosen)
  routes/               one module per HTTP resource
  tasks/                 one module per background job (iff a worker is chosen)
  core/                   shared infrastructure: config.py, db.py, redis.py
  schemas.py             Pydantic contracts — a plain default, not enforced
  models.py                {orm} models — same, iff a database is chosen
```

`main.py` (in `files/`) is a deliberate exception to "layers own whole
files, not `{% if %}`": both a database and a worker need to touch its
startup wiring (DB init, Taskiq's `broker.startup()`/`shutdown()` in a
`lifespan`), and only a worker adds the demo `/tasks/add` endpoint. See
PRODUCT_ARCH.md §4.2 for why this file stays inline-conditional while
`routes/items.py`, `core/db.py`, etc. are full layer overrides.

## Four real gotchas baked into this template — don't regress them

See PRODUCT_ARCH.md §6.1 for the full incident write-ups; the short
version, since it's easy to "fix" these back in accidentally:

1. **`files/src/{{package_name}}/__init__.py.jinja` must exist.**
   Without it, plain Python imports and pytest still work (namespace
   packages), but `fastapi dev`/`fastapi run`'s own directory-detection
   silently breaks.
2. **`alembic.ini`'s `prepend_sys_path = src`**, not `.` — needed so
   `alembic revision --autogenerate` can import the app's models from
   the `src/`-layout package.
3. **`worker.py` imports the `tasks/` submodule(s) at the bottom**,
   after `broker`/`celery_app` is defined — the worker CLI only
   discovers `@broker.task`/`@celery_app.task`-decorated functions by
   importing the module that defines them, and pointing the worker CLI
   at `worker.py` doesn't transitively pull in `tasks/example.py` on
   its own. A bare `tasks/__init__.py` doesn't help either — importing
   a package doesn't auto-import its submodules; each `tasks/*.py`
   module needs its own explicit import line in `worker.py`.
4. **`db-*` layers write `core/db.py` and top-level `models.py`, not a
   `db/` package** — keeps model definitions out of `core/` (they're
   domain content, not infrastructure) while still giving the session/
   engine setup a fixed, predictable home alongside `config.py`/
   `redis.py`.

## Testing this template

`tests/test_generator.py` has a dedicated block of `rest-api`-specific
tests: in-memory, SQLite+SQLModel+migrations, Postgres+SQLAlchemy,
Taskiq, Celery, Taskiq/Celery+RabbitMQ, the `redis`/`broker` decoupling,
and "all features combined." Each asserts the right files exist/don't
(including the specific paths from gotcha #4 above) and runs every
generated `.py` file through `ast.parse()` plus `pyproject.toml`
through `tomllib.loads()`.

That catches template bugs but **not** the gotchas above (imports
succeed, syntax is valid, TOML parses — none of that exercises
`fastapi_cli`'s path detection, a real Alembic run, or a real worker
process). Before shipping a change to this template, manually verify at
least one combination end-to-end: `uv sync`, `uv run pytest`, and — if
you touched migrations or the worker — a real `alembic revision
--autogenerate` + `upgrade head`, and a real worker boot + task enqueue
against **both** brokers. SQLite needs no external service and is
enough for the DB/migrations check; the worker check needs a local
Redis (`redis-server`) or RabbitMQ (`rabbitmq-server`), no Docker
required for either.

## Adding a new option or layer

Add an entry to `template.json`'s `options`/`layers` arrays and the
corresponding files — no code changes in `generator.py`/`prompts.py`/
`cli.py` are needed. Keep option declaration order meaningful: a later
option's `when` can only reference **earlier** options' resolved values
(see PRODUCT_ARCH.md §4).

## Adding a new resource (e.g. beyond `items`)

Following the opinionated layout: a new `POST /widgets` resource is a
new `routes/widgets.py` (+ one `app.include_router(...)` line in
`main.py`), a new `models.py`/`schemas.py` addition (or split into
`models/widgets.py`/`schemas/widgets.py` once there's enough of them to
warrant folders — not enforced, see gotcha #4's reasoning), and — if it
needs background work — a new `tasks/widgets.py` (+ one import line in
`worker.py`).
