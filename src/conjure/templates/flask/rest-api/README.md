# Template: flask / rest-api

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`). Flask equivalent of
`fastapi/rest-api`; read that template's own README first if you haven't
— this one calls out every place Flask's sync/WSGI nature forced a real
design decision instead of a mechanical port, and documents the decisions
that could plausibly have gone the other way.

## What it generates

A layered Flask REST API with an opinionated, Next.js-inspired layout
(PRODUCT_ARCH.md §4.4), the same spirit as `fastapi/rest-api`:
`main.py`/`worker.py` are fixed entrypoints, `routes/`/`tasks/` are
"one file per resource/job" folders, `core/` holds shared
infrastructure — everything else (`schemas.py`, `models.py`) is a
reasonable default, not an enforced convention. `pydantic-settings`
config is always on. A single `items` resource (`GET/POST /items/`,
`GET/DELETE /items/{id}`) backed by an in-memory store by default, or a
real database if one is chosen — directly comparable to the FastAPI
template's `items` resource.

## Design decisions (deviations from fastapi/rest-api, and why)

Flask is sync/WSGI; FastAPI is async-native. Every option below was
reconsidered on its own merits rather than mirrored 1:1.

- **`database`**: `none` / `sqlite` / `postgres` — same three choices as
  FastAPI, same reasoning. Drivers are **sync**, not async: the stdlib
  `sqlite3` for SQLite (no extra dependency — see gotcha 6 below), and
  `psycopg[binary]` (psycopg3) for PostgreSQL rather than `asyncpg`.
  There's no reason to fight Flask's sync request handlers with an async
  driver.
- **`orm`**: two choices, but not the same two as FastAPI. FastAPI offers
  SQLModel vs. SQLAlchemy (both async). Flask's idiomatic default is
  **Flask-SQLAlchemy** (`flask-sqlalchemy` — the de facto standard
  extension: wraps SQLAlchemy with Flask app-context integration,
  `db.session` resolves automatically against whichever app is
  currently active). The second choice, **`sqlalchemy`**, is "manual" —
  raw SQLAlchemy Core/ORM with an explicit `scoped_session`, no Flask
  extension — mirroring the *spirit* of FastAPI's guided-vs-manual split
  (SQLModel is the "batteries" choice there; Flask-SQLAlchemy is this
  template's) without pretending Flask has a SQLModel-shaped extension
  to offer. Both are offered because the guided path (less boilerplate,
  automatic Flask-Migrate integration) and the manual path (no extension
  magic, works the same whether or not `main.py` even uses Flask
  contexts) are both genuinely common ways real Flask projects are
  built — picking only one would misrepresent the ecosystem.
- **`migrations`**: **Flask-Migrate** for the `flask-sqlalchemy` ORM
  (the natural, idiomatic pairing — it wraps Alembic and needs a
  Flask-SQLAlchemy `db` object), **bare Alembic** for the manual
  `sqlalchemy` ORM (no Flask-SQLAlchemy `db` object to hand it, so
  there's nothing for Flask-Migrate to wrap — this is the direct
  equivalent of `fastapi/rest-api`'s own bare-Alembic layers, just sync).
  Two migration layers, gated on `orm`, same shape as FastAPI's
  `migrations-sqlmodel`/`migrations-sqlalchemy` split. See gotcha 2 below
  — the two flavors' `env.py` are **not** the same shape internally, even
  though both are "Alembic."
- **`worker`**: **`none`/`celery` only — Taskiq is deliberately dropped**
  for this template. Taskiq is async-first; wiring it into a sync WSGI
  app would mean wrapping every enqueue call in `asyncio.run()` (or
  running an event loop alongside the WSGI server), which isn't how
  anyone idiomatically uses Flask and would teach the wrong lesson as a
  scaffold. Celery is the standard, idiomatic Flask background-worker
  choice and is enough on its own to deliver the "background worker"
  head start. This is a deliberate scope reduction from FastAPI's
  two-worker offering, not an oversight.
- **`broker`**: `redis` / `rabbitmq`, exactly mirroring FastAPI's
  `broker` option and Celery's own native support for both (Redis
  broker+backend, or AMQP broker + `rpc://` backend) — see
  `worker-celery/src/{{package_name}}/worker.py.jinja`, adapted directly
  from `fastapi/rest-api`'s `worker-celery` layer (same broker/backend
  logic, since Celery itself doesn't change between the two frameworks).
- **`redis`**: same decoupled shape as FastAPI's (PRODUCT_ARCH.md §4.1)
  — an independent "add Redis for caching" question, `when`-gated on
  `broker` (not `worker`) so `broker == "redis"` implies `redis: true`
  without asking, while `broker == "rabbitmq"` still asks independently
  (picking RabbitMQ doesn't preclude also wanting Redis for caching).
  Copied verbatim from FastAPI's `template.json` shape — this design
  isn't framework-specific, it's about not conflating "a worker was
  chosen" with "the worker uses Redis."
- **Layout**: `routes/` (not `blueprints/`) for cross-framework
  consistency — a developer moving between a conjure-generated FastAPI
  project and a conjure-generated Flask project should find the same
  landmark folder for "where HTTP resources live," even though the
  *content* is Flask Blueprints (`Blueprint(...)`, registered via
  `app.register_blueprint(...)` in `main.py`) rather than FastAPI
  routers. `core/`/`tasks/` follow the same reasoning as FastAPI's.
- **Request validation**: FastAPI wires Pydantic models into request/
  response handling automatically. Flask has no equivalent, so this
  template keeps using **Pydantic models, validated manually**:
  `ItemCreate.model_validate(request.get_json())` on the way in,
  `ItemRead.model_validate(obj).model_dump()` (via `jsonify`) on the way
  out — `ItemRead` sets `model_config = ConfigDict(from_attributes=True)`
  so it can validate directly from an ORM object's attributes, not just
  a dict. This was chosen over "just use raw dicts" specifically so
  `schemas.py` stays structurally identical to the FastAPI template's —
  same file, same import, same mental model, only the call sites differ
  (explicit `.model_validate()`/`.model_dump()` instead of FastAPI's
  automatic wiring).
- **Entrypoint shape — `create_app()` factory, no module-level `app`**:
  this is *not* mirrored from FastAPI (which has no equivalent problem —
  see gotcha 5 below) and is the single biggest structural difference
  from a naive port. `main.py` exports `create_app(*, database_url=None,
  testing=False)` and nothing else at module scope. `flask run`/
  `flask db ...` auto-detect `create_app` as an implicit application
  factory from `--app src/{{package_name}}/main.py`; the Dockerfile's
  `gunicorn` points at `{{package_name}}.main:create_app()` (gunicorn's
  factory-call syntax); tests call `create_app(database_url=...,
  testing=True)` directly.

## Options (`template.json`, resolved in this order)

| key | type | default | depends on | notes |
|---|---|---|---|---|
| `database` | select | `sqlite` | — | `none`, `sqlite`, `postgres` |
| `orm` | select | `flask-sqlalchemy` | `database != none` | `flask-sqlalchemy`, `sqlalchemy` (manual); skip_value `"none"` |
| `migrations` | confirm | `true` | `database != none` | skip_value `false` |
| `worker` | select | `none` | — | `none`, `celery` (no Taskiq — see above) |
| `broker` | select | `redis` | `worker != none` | `redis`, `rabbitmq`; skip_value `"none"` when no worker |
| `redis` | confirm | `false` | `broker != redis` | skip_value `true` — implied whenever `broker == "redis"`; otherwise an independent "add Redis for caching" question |

## Layout (of this template's directory, not the generated project)

```
template.json                 options + layers (see above)
README.md                     this file
files/                         always rendered — main.py, core/config.py, schemas.py,
                               routes/items.py (in-memory), tests/test_main.py,
                               env.jinja (-> .env + .env.example)
docker/                         iff --docker
db-flask-sqlalchemy/             iff orm == flask-sqlalchemy — overrides routes/items.py,
                                 adds core/db.py + top-level models.py
db-sqlalchemy/                   iff orm == sqlalchemy (manual) — same shape, raw
                                 SQLAlchemy Core/ORM + scoped_session
migrations-flask-sqlalchemy/       iff migrations && orm == flask-sqlalchemy — Flask-Migrate
                                   (migrations/, overrides core/db.py to also register
                                   the Migrate extension)
migrations-sqlalchemy/             iff migrations && orm == sqlalchemy — bare Alembic
                                   (alembic/, same shape as fastapi/rest-api's, sync)
worker-celery/                     iff worker == celery — worker.py, tasks/example.py;
                                   worker.py branches on `broker` (redis/rabbitmq)
redis/                              iff redis resolves true — core/redis.py client (sync)
```

There's no `broker-rabbitmq/` layer, for the same reason FastAPI's
template has none: RabbitMQ needs no app-level client the way Redis does
for caching, it's purely internal to `worker.py` (Celery's built-in AMQP
transport, no extra package needed — see gotcha 4). The only
RabbitMQ-specific content is a few `{% if broker == "rabbitmq" %}`
branches in `worker.py.jinja`/`config.py.jinja`/`env.jinja`/
`pyproject.toml.jinja`.

The **generated project's** layout (what a developer actually sees) is:

```
src/{{package_name}}/
  main.py              Flask entrypoint — create_app() factory only, no module-level app
  worker.py            Celery entrypoint — fixed name/location (iff a worker is chosen)
  routes/               one module per HTTP resource (Flask Blueprints)
  tasks/                 one module per background job (iff a worker is chosen)
  core/                   shared infrastructure: config.py, db.py, redis.py
  schemas.py             Pydantic contracts — a plain default, not enforced
  models.py                {orm} models — same, iff a database is chosen
migrations/ or alembic/    iff migrations — dir name depends on orm (see above)
```

## Six real gotchas found while building this template — don't regress them

Two are the direct Flask-flavored equivalent of `fastapi/rest-api`'s own
gotchas (documented in PRODUCT_ARCH.md §7.1); the rest are new, specific
to Flask's synchronous, import-time-eager nature, and were only found by
actually running the generated tooling (`flask db migrate`, a live
Postgres, a live Celery worker) — not by `ast.parse()`/`tomllib` checks.

1. **`files/src/{{package_name}}/__init__.py.jinja` must exist.** Same
   root cause as the FastAPI gotcha, different tool: without it, plain
   Python imports and pytest still work (namespace packages), but
   Flask's own CLI app-loader (`flask.cli.prepare_import`, used by
   `flask run`/`flask db ...`) walks up through `__init__.py` files to
   find the package root to add to `sys.path` and derive the dotted
   import name. Missing it, Flask resolves the module as a bare `main`
   (not `{{package_name}}.main`) and never adds `src/` to `sys.path`,
   so `from {{package_name}} import ...` fails inside `main.py` itself.
   Verified by deleting it in a scratch project: `flask db init` /
   `flask db migrate` both fail with `ModuleNotFoundError:
   No module named '{{package_name}}'`.

2. **Flask-Migrate's `migrations/alembic.ini` does *not* need
   `prepend_sys_path` — but bare Alembic's (the `sqlalchemy`/manual ORM
   layer) still does, exactly like FastAPI.** These two migration
   layers are *not* structurally parallel, and it's not obvious until
   you read the generated `env.py`: Flask-Migrate's `env.py` obtains the
   database and metadata via `current_app.extensions['migrate'].db` —
   the already-running Flask app object (imported through the normal
   `FLASK_APP` app-loader, which needs no `prepend_sys_path` since it's
   not importing the app's *models* directly, just asking the live app
   for its already-registered metadata). Bare Alembic's `env.py` (the
   `migrations-sqlalchemy` layer) imports `{{package_name}}.models`
   directly, so it needs `prepend_sys_path = src` in `alembic.ini` for
   the same reason FastAPI's does. Verified both flavors end-to-end
   against real SQLite and real PostgreSQL (`flask db migrate`/`flask
   db upgrade` for the Flask-Migrate layer; `alembic revision
   --autogenerate`/`alembic upgrade head` for the bare-Alembic layer) —
   both correctly found the `Item`/`items` model and created the table.

3. **No eager `app = create_app()` at module scope in `main.py` —
   this one doesn't exist in the FastAPI template at all**, because
   FastAPI's database setup lives inside an ASGI lifespan handler that
   only runs when the app actually *starts* (a real server, or a test
   client's lifespan). Flask has no equivalent "only on start" hook for
   a plain WSGI app — a naive `app = create_app()` at the bottom of
   `main.py` (the obvious, common Flask pattern) means the database
   connection is opened the moment the module is **imported**, not when
   the app is run. That import happens far more often than "the app is
   actually being started": `pytest` collection imports
   `tests/conftest.py`, which imports `{{package_name}}.main`; a bare
   `alembic`/`flask db` invocation imports it too. Verified the failure
   mode directly: with `database == "postgres"` and Postgres stopped,
   `uv run pytest` failed with `sqlalchemy.exc.OperationalError:
   connection failed` — **before any test even ran**, purely from
   importing `main.py` — which is a direct FR10 violation (tests must
   never require the configured production database to be reachable).
   Fixed by never instantiating `app` at module scope: `create_app()` is
   only ever *called* by something that actually wants a running app —
   Flask CLI's implicit-factory auto-detection (`flask --app .../main.py
   run`), gunicorn's factory-call syntax (`{{package_name}}.main:
   create_app()`), or a test explicitly passing an isolated
   `database_url`. Re-verified with Postgres stopped after the fix:
   `uv run pytest` passes cleanly.

4. **Celery discovers `rabbitmq://`-broker tasks with zero extra
   dependencies — exactly like FastAPI's Celery layer, verified
   independently.** No `librabbitmq`/`amqp`-specific package needed;
   `kombu` (a `celery` dependency) ships the pure-Python `pyamqp`
   transport by default. Verified with a real `rabbitmq-server` and a
   real worker boot (`[queues] .> celery exchange=celery(direct)`
   connecting successfully), plus a real enqueue → execute round trip.

5. **`worker.py` imports the `tasks/` submodule(s) at the bottom**,
   after `celery_app` is defined — identical reasoning and fix to
   FastAPI's Celery layer (the worker CLI only discovers
   `@celery_app.task`-decorated functions by importing the module that
   defines them; a bare `tasks/__init__.py` doesn't auto-import
   submodules). Verified with a real worker boot showing `[tasks]
   . {{package_name}}.tasks.example.add` in the startup banner, then a
   real enqueue via `POST /tasks/add` → the worker log shows the task
   received and executed with the correct result.

6. **No `aiosqlite`-style "must be an unconditional dev dependency"
   gotcha here — and that's worth calling out explicitly, since it's the
   one FastAPI gotcha that does *not* carry over.** FastAPI's async
   SQLite driver (`aiosqlite`) is a real PyPI package that has to be
   installed even when the configured production database is Postgres,
   because the test suite always uses SQLite (FR10) regardless. Flask's
   sync SQLite access goes through the **stdlib `sqlite3` module** —
   nothing to add as a dependency, for any `database` choice. Verified
   by generating a `database == "postgres"` project and running its test
   suite with Postgres stopped entirely: it passes without `psycopg`
   (the production driver) ever being touched, and without needing any
   sqlite-specific package either. One thing that *does* still need
   care on the SQLite side (both ORM layers apply this in `core/db.py`):
   an in-memory `sqlite:///:memory:` database only exists for the
   lifetime of a single DB-API connection, so the default connection
   pool (which hands out a new connection per checkout) silently loses
   every write between requests unless the engine is built with
   `poolclass=StaticPool` — applied automatically whenever the resolved
   database URL contains `:memory:` (i.e., only for the test suite; a
   real file-based SQLite database doesn't need it).

**A seventh thing worth knowing about, not a bug in this template**:
Flask's default relative-SQLite-path resolution. `sqlite:///./app.db`
(the default `DATABASE_URL`) resolves relative to the Flask app's
*instance path*, not the process's working directory — for a
`src/`-layout package this lands the file at `src/instance/app.db`, not
`./app.db` at the project root. Verified directly (`flask db upgrade`
against the default config creates exactly that file). This is normal,
documented Flask/Flask-SQLAlchemy behavior — the instance folder is
Flask's own designated home for local, non-version-controlled files
like this — so it's left as-is rather than "fixed," and `.gitignore`'s
existing `*.db`/`instance/` entries already cover it.

**A known limitation this template does *not* attempt to fix**:
`src/conjure/postgen.py`'s `print_summary` hardcodes the FastAPI-specific
"next steps" run command (`uv run fastapi dev src/{package_name}/
main.py`, `http://127.0.0.1:8000`) rather than deriving it from the
chosen framework/template. This means the CLI's printed next-steps for
*any* Flask project (this template or `flask/hello-world`) are
currently wrong once the `flask` framework is switched on — confirmed
live via `conjure new ... --framework flask --template rest-api`. Fixing
it is a `postgen.py` change (core CLI code, not template content),
explicitly out of this template's scope per the task that produced it —
flagged here so it isn't mistaken for something this template forgot to
wire up, and so whoever enables the `flask` framework knows to fix it
at the same time.

## Testing this template

`tests/test_flask_rest_api.py` (repo root, standalone — deliberately not
appended to `test_generator.py`, to avoid colliding with unrelated
in-flight work there) has a dedicated block of `rest-api`-specific
tests: in-memory, SQLite+Flask-SQLAlchemy+migrations,
PostgreSQL+manual-SQLAlchemy, Celery+Redis, Celery+RabbitMQ, the
`redis`/`broker` decoupling, "all features combined" (twice — once per
ORM, since the two ORM choices exercise genuinely different `core/db.py`
implementations), and the Docker layer. Every rendered `.py` file is run
through `ast.parse()`, every `pyproject.toml` through `tomllib.loads()`.
Since `flask`'s framework `template.json` ships `"enabled": false`
(Flask isn't switched on for end users yet), every test uses an
`enable_flask` fixture that monkeypatches `generator.get_framework` for
the duration of the test — it never touches the real `template.json` on
disk.

That catches template bugs but **not** the gotchas above (imports
succeed, syntax is valid, TOML parses — none of that exercises Flask's
own CLI app-loader, a real Flask-Migrate/Alembic run, or a real Celery
worker process). Before shipping a change to this template, manually
verify at least one combination end-to-end: `uv sync`, `uv run pytest`
(with the configured production database intentionally stopped, per
gotcha 3), and — if you touched migrations or the worker — a real `flask
db migrate`/`flask db upgrade` (Flask-Migrate layer) or `alembic
revision --autogenerate`/`alembic upgrade head` (bare-Alembic layer)
against real SQLite *and* real PostgreSQL, and a real worker boot + task
enqueue against **both** brokers (`redis-server`/`rabbitmq-server`, no
Docker required for either).

## Adding a new option or layer

Add an entry to `template.json`'s `options`/`layers` arrays and the
corresponding files — no code changes in `generator.py`/`prompts.py`/
`cli.py` are needed. Keep option declaration order meaningful: a later
option's `when` can only reference **earlier** options' resolved values
(see PRODUCT_ARCH.md §4).

## Adding a new resource (e.g. beyond `items`)

Following the opinionated layout: a new `POST /widgets` resource is a
new `routes/widgets.py` (a new `Blueprint`, + one
`app.register_blueprint(...)` line in `main.py`'s `create_app()`), a new
`models.py`/`schemas.py` addition (or split into
`models/widgets.py`/`schemas/widgets.py` once there's enough of them to
warrant folders — not enforced), and — if it needs background work — a
new `tasks/widgets.py` (+ one import line in `worker.py`, see gotcha 5).
