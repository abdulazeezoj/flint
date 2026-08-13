# Flask · REST API

A layered Flask REST API with `pydantic-settings`, your choice of
database/ORM, migrations, and a Celery background worker (Redis or
RabbitMQ), with optional Redis caching. This is the Flask counterpart to
[FastAPI · REST API](fastapi-rest-api.md) — same opinionated layout, same
spirit of "pick what you need, skip what you don't" — but not a mechanical
port. Flask is sync/WSGI, not async, and that forced a handful of genuine
design differences covered below: an application-factory entrypoint, two
different migration tools depending on which ORM you pick, and a
background-worker choice that's deliberately Celery-only.

Generated with a single `items` resource (`GET/POST /items/`,
`GET/DELETE /items/{id}`) backed by an in-memory store by default, or a
real database once you pick one.

## Quick start

```bash
flint new my-api \
  --framework flask --template rest-api \
  -o database=postgres -o orm=flask-sqlalchemy -o migrations=true \
  -o worker=celery -o broker=redis \
  --docker --git --install --yes
```

Because `broker=redis`, the `redis` (caching) option is never asked — it
resolves to `true` automatically (see [Redis](#redis-caching) below).
Resolved options: `database=postgres, orm=flask-sqlalchemy,
migrations=True, worker=celery, broker=redis, redis=True`.

What you'd do next:

```bash
cd my-api

# Migrations are on, so the schema isn't there yet — create and apply it:
uv run flask --app src/my_api/main.py db migrate -m "initial migration"
uv run flask --app src/my_api/main.py db upgrade

# Start the app
uv run flask --app src/my_api/main.py run
```

Then open <http://127.0.0.1:5000> — you should see `{"message": "Hello,
World!"}`, and `/items/` for the generated resource. In a separate
terminal, start the worker:

```bash
PYTHONPATH=src uv run celery -A my_api.worker.celery_app worker --loglevel=info
```

`PYTHONPATH=src` is required — the app lives under `src/`, and the Celery
CLI doesn't know about `pyproject.toml`'s `pythonpath` setting the way
pytest does.

## Options

| Key | Type | Default | Choices | Depends on |
|---|---|---|---|---|
| `database` | select | `sqlite` | `none`, `sqlite`, `postgres` | — |
| `orm` | select | `flask-sqlalchemy` | `flask-sqlalchemy`, `sqlalchemy` (manual) | asked only if `database != none`; otherwise skipped, resolves to `none` |
| `migrations` | confirm | `true` | — | asked only if `database != none`; otherwise skipped, resolves to `false` |
| `worker` | select | `none` | `none`, `celery` | — |
| `broker` | select | `redis` | `redis`, `rabbitmq` | asked only if `worker == celery`; otherwise skipped, resolves to `none` |
| `redis` | confirm | `false` | — | asked only if `broker` is `rabbitmq` or `none`; if `broker == redis`, skipped and resolves to `true` |

A few things worth calling out that aren't obvious from the table alone:

- **`orm` is not FastAPI's `orm`.** The FastAPI `rest-api` template offers
  `sqlmodel` / `sqlalchemy`. Flask's equivalent split is
  `flask-sqlalchemy` / `sqlalchemy` — **not** `sqlmodel`. There's no
  SQLModel-shaped Flask extension worth pretending exists, so the
  "guided, batteries-included" choice here is **Flask-SQLAlchemy**
  (`flask-sqlalchemy`, the de facto standard extension — it wraps
  SQLAlchemy with app-context integration, so `db.session` resolves
  automatically against whichever app is currently active) and the
  "manual" choice is bare **SQLAlchemy** with an explicit
  `scoped_session` and no Flask extension at all.
- **`migrations` doesn't mean one fixed tool.** Which migration tool you
  get depends on `orm` — see [Migrations](#migrations) below.
- **`worker` only offers Celery.** FastAPI's template offers Taskiq or
  Celery; this one drops Taskiq entirely — see
  [Background worker](#background-worker-celery-only).
- **Drivers are sync, not async**, for both databases: the stdlib
  `sqlite3` for SQLite, `psycopg[binary]` (psycopg3) for PostgreSQL.
  There's no reason to fight Flask's sync request handlers with an async
  driver the way FastAPI's template does with `asyncpg`.

## The core idea: `create_app()`, not `app = Flask(__name__)`

If you read nothing else on this page, read this section.

`main.py` exports exactly one thing at module scope: a factory function.

```python
def create_app(*, database_url: str | None = None, testing: bool = False) -> Flask:
    app = Flask(__name__)
    ...
    if database_url is not None:  # (illustrative — see below for the real shape)
        init_db(app, testing=testing)
    app.register_blueprint(items_bp)
    ...
    return app
```

There is **no** module-level `app = create_app()` anywhere in the
generated project.

!!! note "Why this matters — it's not a style choice"
    FastAPI's template never has this problem: its database setup lives
    inside an ASGI lifespan hook that only runs when the app actually
    *starts*. Flask has no equivalent "only on real startup" hook for a
    plain WSGI app. If `main.py` did the obvious, common Flask thing —
    `app = Flask(__name__)` at module scope, with the database engine
    built right there — the database connection would open the instant
    the module is **imported**, not when the app is run. And the module
    gets imported far more often than "the app is actually being
    started": `pytest` collection imports `tests/conftest.py`, which
    imports `main`; a bare `flask db ...`/`alembic` invocation imports it
    too.

    This was verified directly while building the template: with
    `database=postgres` and Postgres stopped, a naive module-level `app`
    made `uv run pytest` fail with
    `sqlalchemy.exc.OperationalError: connection failed` — **before any
    test even ran**, purely from importing `main.py`. That's a direct
    violation of the guarantee that tests never require the configured
    production database to be reachable. The fix is the factory: nothing
    calls `create_app()` except something that actually wants a running
    app — Flask's CLI (`flask --app src/my_api/main.py run`/`db ...`
    auto-detects `create_app` as an implicit application factory),
    gunicorn's factory-call syntax in the Dockerfile
    (`my_api.main:create_app()`), or a test calling it directly with an
    isolated `database_url`.

Every place the factory shows up:

| Caller | How |
|---|---|
| `flask run` / `flask db ...` | Auto-detects `create_app` from `--app src/{package}/main.py` (Flask's implicit factory convention — no code needed to opt in) |
| `gunicorn` (via `--docker`) | `CMD ["gunicorn", ..., "{package}.main:create_app()"]` — gunicorn's own factory-call syntax |
| Tests | `create_app(database_url="sqlite:///:memory:", testing=True)`, called directly in a `client` fixture |

## Generated layout

```text
src/{package_name}/
  main.py              Flask entrypoint — create_app() factory, no module-level app
  worker.py            Celery entrypoint (iff worker == celery)
  routes/               one module per HTTP resource — Flask Blueprints
    items.py              the example resource
  core/                  shared infrastructure
    config.py              Settings (pydantic-settings, always)
    db.py                  engine/session setup (iff database != none)
    redis.py                Redis client (iff redis resolves true)
  tasks/                 one module per background job (iff worker == celery)
    example.py             the /tasks/add demo task
  schemas.py             Pydantic request/response models
  models.py               {orm} models (iff database != none)
migrations/ or alembic/  iff migrations — directory name depends on orm, see below
tests/
  test_main.py
  conftest.py             (iff database != none — the isolated-db client fixture)
AGENTS.md
Dockerfile                iff --docker
```

`routes/` — not `blueprints/` — on purpose: a developer moving between a
flint-generated FastAPI project and a flint-generated Flask project should
find the same landmark folder for "where HTTP resources live," even
though the *contents* are genuinely different (`Blueprint(...)` objects
registered via `app.register_blueprint(...)` in `create_app()`, not
FastAPI routers). `core/`/`tasks/`/`models.py`/`schemas.py` follow the
same [opinionated layout](index.md) as every other template: `main.py`,
`worker.py`, `routes/`, and `tasks/` are fixed, load-bearing names; `core/`
is shared infrastructure; `schemas.py`/`models.py` are a reasonable
default that's free to become `schemas/`/`models/` folders once a project
grows past one resource.

**Request validation** is manual, unlike FastAPI's automatic wiring —
there's no Flask equivalent of FastAPI parsing Pydantic models straight
out of the request. `routes/items.py` calls
`ItemCreate.model_validate(request.get_json())` on the way in and
`ItemRead.model_validate(obj).model_dump()` (via `jsonify(...)`) on the
way out. `ItemRead` sets `model_config = ConfigDict(from_attributes=True)`
specifically so it can validate straight from an ORM object's attributes,
not just a dict — so `schemas.py` stays structurally identical to the
FastAPI template's, only the call sites differ.

## Database & ORM

Picking a `database` other than `none` adds a `models.py` and a
`core/db.py`, and swaps `routes/items.py` for a database-backed version.
The two `orm` choices produce genuinely different `core/db.py`
implementations, not just a different import:

=== "orm = flask-sqlalchemy"

    ```python
    from flask_sqlalchemy import SQLAlchemy

    db = SQLAlchemy()

    def init_db(app, *, testing=False): ...
    ```

    Models subclass `db.Model`:

    ```python
    class Item(db.Model):
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        description: Mapped[str | None] = mapped_column(default=None)
    ```

    Routes use `db.session` directly (`db.session.execute(db.select(Item))`,
    `db.session.add(item)`) — Flask-SQLAlchemy's scoped session, already
    bound to whichever app is currently active.

=== "orm = sqlalchemy (manual)"

    ```python
    SessionLocal = scoped_session(sessionmaker())

    def init_db(app, *, testing=False): ...
    def get_session() -> Session: ...
    ```

    Models subclass a plain `DeclarativeBase`:

    ```python
    class Base(DeclarativeBase):
        pass

    class Item(Base):
        __tablename__ = "items"
        ...
    ```

    Routes call `get_session()` explicitly to get a session bound to the
    current app context, then use it the same way
    (`session.execute(select(Item))`, `session.add(item)`).

Both are offered because they're both genuinely common ways real Flask
projects get built — Flask-SQLAlchemy is less boilerplate and gets
automatic Flask-Migrate integration; the manual path has no extension
magic and works the same whether or not `main.py` uses Flask's app
context. Picking only one would misrepresent how the ecosystem actually
looks.

**A SQLite quirk both `db.py` variants handle the same way**: a
`sqlite:///:memory:` database only exists for the lifetime of a single
DB-API connection. The default connection pool hands out a new connection
per checkout, silently losing every write between requests — so whenever
the resolved database URL contains `:memory:` (i.e. only in the test
suite), the engine is built with `poolclass=StaticPool` to keep one
connection alive for the app's lifetime. A real file-based SQLite database
never needs this.

**Another SQLite quirk, not a bug — just worth knowing**: the default
`DATABASE_URL` (`sqlite:///./app.db`) resolves relative to Flask's
*instance path*, not the process's working directory. For this
`src/`-layout package that lands the file at `src/instance/app.db`, not
`./app.db` at the project root. This is normal, documented Flask/
Flask-SQLAlchemy behavior — the instance folder is Flask's own designated
home for local, non-version-controlled files — and `.gitignore`'s
`*.db`/`instance/` entries already cover it.

## Migrations

Turning `migrations` on doesn't get you one fixed tool — it depends on
which `orm` you picked, and the two are genuinely not interchangeable:

| `orm` | Migration tool | Directory | Commands |
|---|---|---|---|
| `flask-sqlalchemy` | **Flask-Migrate** (wraps Alembic) | `migrations/` | `flask --app src/{package}/main.py db migrate -m "..."`, then `db upgrade` |
| `sqlalchemy` (manual) | **bare Alembic** | `alembic/` | `alembic revision --autogenerate -m "..."`, then `alembic upgrade head` |

Flask-Migrate is the natural pairing for `flask-sqlalchemy` — it wraps
Alembic and needs a Flask-SQLAlchemy `db` object to introspect. The manual
`sqlalchemy` ORM has no such `db` object to hand it, so there's nothing
for Flask-Migrate to wrap; it gets the direct equivalent of FastAPI's own
bare-Alembic layer instead, just sync.

The two flavors' `env.py` are **not** the same shape internally, even
though both are "Alembic" under the hood:

- **Flask-Migrate's `env.py`** gets the database and metadata from
  `current_app.extensions['migrate'].db` — the already-running Flask app,
  reached through the normal `FLASK_APP` app-loader. Because it never
  imports the app's models directly (it just asks the live app for its
  already-registered metadata), its `migrations/alembic.ini` does **not**
  need `prepend_sys_path`.
- **Bare Alembic's `env.py`** (the `sqlalchemy`/manual layer) imports
  `{package}.models` directly, so its `alembic.ini` **does** need
  `prepend_sys_path = src` — exactly like the FastAPI template's bare-
  Alembic layer — or `alembic revision --autogenerate` can't find the app's
  models at all.

!!! warning "The database is not auto-created when migrations are on"
    With `migrations=true`, nothing calls `create_all()`/`db.create_all()`
    against a real database — schema comes solely from running the
    migration. Skip that step and the app starts against an empty schema
    and every database-backed request fails.

    This is deliberate, not an oversight: earlier revisions of this
    template called `create_all()` unconditionally on every app boot,
    which made migrations decorative — by the time anyone ran `flask db
    migrate`, the tables already existed and matched the models exactly
    (created by the eager `create_all()`, not by any migration), so
    autogenerate reported "No changes in schema detected" instead of
    generating a real initial migration. Worse, on a genuinely fresh
    database, `flask db upgrade` would eventually try to create tables
    `create_all()` had already silently created outside migration
    history. Fixed by threading a `testing` parameter through `init_db()`:
    the schema is created directly from the models **only** for the
    isolated in-memory test database (which has no migration history to
    replay against); a real database always gets its schema from `flask db
    upgrade`/`alembic upgrade head`.

    First run after generating with `migrations=true`, always:

    ```bash
    uv run flask --app src/{package}/main.py db migrate -m "initial migration"
    uv run flask --app src/{package}/main.py db upgrade
    # or, for orm=sqlalchemy:
    uv run alembic revision --autogenerate -m "initial migration"
    uv run alembic upgrade head
    ```

## Background worker: Celery only

FastAPI's `rest-api` template offers a choice between Taskiq and Celery.
This template offers **Celery, or nothing** — Taskiq is deliberately
dropped, not an oversight. Taskiq is async-first; wiring it into a sync
WSGI app would mean wrapping every enqueue call in `asyncio.run()` (or
running an event loop alongside the WSGI server), which isn't how anyone
idiomatically uses Flask and would teach the wrong lesson as a scaffold.
Celery is the standard, idiomatic Flask background-worker choice, and
it's enough on its own to deliver the "background worker" head start.

Choosing `worker=celery` adds `worker.py` (the Celery app, branching on
`broker`) and a `tasks/` folder:

```python
# worker.py
celery_app = Celery("my_api", broker=settings.redis_url, backend=settings.redis_url)
# or, if broker == "rabbitmq":
# celery_app = Celery("my_api", broker=settings.rabbitmq_url, backend="rpc://")

# imported last, after celery_app exists — see the note below
from my_api.tasks import example  # noqa: E402,F401
```

```python
# tasks/example.py
from my_api.worker import celery_app

@celery_app.task
def add(a: int, b: int) -> int:
    return a + b
```

`main.py` also gets a demo endpoint wired up: `POST /tasks/add?a=1&b=2`
enqueues the task and returns `{"task_id": ...}`.

!!! note "Task modules are imported at the *bottom* of worker.py — on purpose"
    The Celery worker CLI only discovers `@celery_app.task`-decorated
    functions by importing the module that defines them. A bare
    `from my_api import tasks` (importing the package) doesn't auto-import
    its submodules — so every new file under `tasks/` needs its own
    explicit import line in `worker.py`, added *after* `celery_app` is
    defined (a task module needs to import `celery_app` back from
    `worker.py`, so importing tasks any earlier would be circular).
    Verified with a real worker boot: skip this and the startup banner's
    `[tasks]` list is empty, and enqueuing silently does nothing useful.

`broker=rabbitmq` needs no extra dependency: `kombu` (a `celery`
dependency) ships the pure-Python `pyamqp` transport by default, so
there's no `broker-rabbitmq/` layer the way there's a `redis/` layer —
RabbitMQ support is just a few `{% if broker == "rabbitmq" %}` branches in
`worker.py`/`config.py`/`.env`/`pyproject.toml`.

## Redis (caching)

`redis` is a separate, decoupled question from `worker`/`broker` — picking
Celery doesn't automatically mean you want Redis for caching, and picking
Redis as your broker shouldn't make Flint ask twice. The rule: `redis`
resolves to `true` automatically whenever `broker == redis` (no prompt);
otherwise it's asked as its own independent "add Redis for caching?"
question (default `false`), whether or not a worker is configured at all.

When it resolves true, `core/redis.py` is added:

```python
from redis import Redis
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
```

Import `redis_client` from `core.redis` in any route that needs caching —
nothing invalidates a cache entry on writes automatically; that's on you
to add.

## `--docker`

Adds a `Dockerfile` (`uv`-based, matching every other flint template) and
`.dockerignore`. The one Flask-specific detail: the container runs under
**gunicorn**, not the Flask dev server, and points it at the factory using
gunicorn's own factory-call syntax — one more place the
[application-factory pattern](#the-core-idea-create_app-not-app-flask__name__)
shows up:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "{package_name}.main:create_app()"]
```

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

Note the port: the containerized app listens on **8000** (gunicorn's
bind), while `flask run` locally defaults to **5000** — don't confuse the
two when switching between "running it directly" and "running it in
Docker."

## Test isolation

Regardless of which `database` you configured, the test suite never
touches it. `tests/conftest.py`'s `client` fixture calls the factory
directly with an isolated in-memory database:

```python
@pytest.fixture
def client():
    app = create_app(database_url="sqlite:///:memory:", testing=True)
    return app.test_client()
```

That's what `testing=True` is for: `init_db()` only creates tables
directly from the models (bypassing migrations) for this isolated
database — never for a real one. Combined with the
[application-factory pattern](#the-core-idea-create_app-not-app-flask__name__)
above, this is what makes it safe to run `uv run pytest` with your
configured production database completely stopped, whether that's SQLite
or PostgreSQL. Unlike FastAPI's SQLite driver (`aiosqlite`, a real PyPI
package that has to be an unconditional dev dependency because the test
suite always uses SQLite regardless of the configured database), Flask's
sync SQLite access goes through the **stdlib `sqlite3` module** — nothing
extra to install, for any `database` choice.

## `.agents/skills/`

Every generated project ships deeper, library-specific reference material
under `.agents/skills/` for exactly the stack it ended up using — see
[Agent Skills](../agent-skills.md) for the full mechanism. This template
always includes:

- `flask`
- `pydantic-settings`
- `pytest`

...plus, conditionally:

| Skill | Included when |
|---|---|
| `flask-sqlalchemy` | `orm == flask-sqlalchemy` |
| `sqlalchemy` | `orm == sqlalchemy` |
| `flask-migrate` | `orm == flask-sqlalchemy` and `migrations == true` |
| `alembic` | `orm == sqlalchemy` and `migrations == true` |
| `celery` | `worker == celery` |
| `redis` | `redis` resolves `true` |

## Next

- [Templates overview](index.md) — the shared layout philosophy and how
  layers/options/skills fit together
- [FastAPI · REST API](fastapi-rest-api.md) — the same template shape on
  FastAPI's async stack, for comparison
- [Agent Skills](../agent-skills.md) — how `.agents/skills/` is selected
  and what's in it
- [CLI Reference](../cli-reference.md) — every flag and what `-o key=value`
  accepts
