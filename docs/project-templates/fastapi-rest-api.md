# FastAPI · REST API

The richest template Brupy ships. Where `hello-world` gets you a single
endpoint, `rest-api` gets you a layered FastAPI project with a real
database, an ORM, Alembic migrations, a background worker, and Redis —
each independently optional, wired together correctly when combined, and
skipped cleanly when you don't need them. `pydantic-settings`-backed
config is always on: this template exists to show the shape of a project
past "hello world," not to stay minimal.

It generates one example resource, `items` (`GET/POST /items/`,
`GET/DELETE /items/{id}`), backed by an in-memory store by default or a
real database if you pick one — enough to see every layer actually wired
together, not just declared.

## Options

Options are resolved in this order — later options can depend on earlier
ones:

| Option | Prompt | Choices | Default | Depends on |
|---|---|---|---|---|
| `database` | Database? | `none` (in-memory), `sqlite`, `postgres` | `sqlite` | — |
| `orm` | ORM? | `sqlmodel`, `sqlalchemy` | `sqlmodel` | only asked if `database != none`; resolves to `none` otherwise |
| `migrations` | Add Alembic migrations? | yes/no | `true` | only asked if `database != none`; resolves to `false` otherwise |
| `worker` | Background worker? | `none`, `taskiq`, `celery` | `none` | — |
| `broker` | Message broker? | `redis`, `rabbitmq` | `redis` | only asked if `worker != none`; resolves to `none` otherwise |
| `redis` | Add Redis (caching)? | yes/no | `false` | only asked if `broker` is `rabbitmq` or `none`; resolves to `true` otherwise |

The last row is the one worth reading twice: **`redis` depends on
`broker`, not on `worker`.** If you picked `broker=redis` for your
worker, a Redis instance already exists, so the caching question is
skipped and silently implied `true` — asking again would be pointless.
But `broker=rabbitmq` doesn't touch Redis at all, and neither does
skipping the worker entirely, so in both of those cases you're asked the
caching question fresh, independent of whatever the worker is doing.

!!! note "Why this isn't gated on `worker`"
    An earlier version of this template asked about Redis whenever
    `worker == "none"`, which quietly broke the moment RabbitMQ became a
    second broker choice — picking a Taskiq+RabbitMQ combination would
    have skipped the question and implied Redis anyway, for no reason.
    Gating on the resolved `broker` value instead of `worker` keeps
    `redis` meaning exactly one thing: *is there a Redis instance this
    app can reach*, however that came to be true. It also means
    `--option broker=redis --option redis=false` is a legal (if
    self-contradictory) combination if you pass both explicitly —
    explicit `--option` values always win over the prompt logic, with no
    cross-option consistency check.

Every option has a matching `-o key=value` flag for non-interactive use
— see [Getting Started](../getting-started.md#skip-the-prompts) and
[CLI Reference](../cli-reference.md).

## What gets generated

```
src/{{ package_name }}/
  main.py              FastAPI entrypoint — app, lifespan, mounted routers
  worker.py            worker entrypoint (iff a worker is chosen)
  routes/               one module per HTTP resource
    items.py
  tasks/                 one module per background job (iff a worker is chosen)
    example.py
  core/                   shared infrastructure
    config.py               settings (pydantic-settings) — always
    db.py                    async engine/session (iff a database is chosen)
    redis.py                 Redis client (iff redis resolves true)
  schemas.py              Pydantic request/response models
  models.py                {orm} models (iff a database is chosen)
tests/
alembic/                 migrations (iff migrations is on)
AGENTS.md
Dockerfile               (iff --docker)
```

This layout borrows a specific idea from Next.js's `app/`/`pages/`
convention, applied literally rather than loosely: **only routing is
strictly located; everything else is a sensible default, not an
enforced rule.**

- **Strictly opinionated** — Brupy always uses this exact name and
  location, and every generated project agrees: `main.py` (never
  renamed, never moved), `worker.py` (same, when present), `routes/`
  (one module per resource — routers are individually imported and
  mounted in `main.py`, so this is the one place with real load-bearing
  significance), `tasks/` (one module per job, mirroring `routes/`), and
  `core/` for shared infrastructure every route or task might reasonably
  depend on.
- **A default, not a rule** — `schemas.py` and `models.py` stay
  single top-level files for now, because this template only ships one
  resource. They're natural candidates to become `schemas/`/`models/`
  folders the moment your project grows a second resource — Brupy just
  doesn't make that call for you.

Notice `models.py` and the engine/session setup in `db.py` live outside
`core/`, not inside it. That's deliberate: `core/` is config plus
cross-cutting infrastructure, while models are domain content that
scales with how many resources you add — putting `Item` inside `core/`
would mean every future resource's model lands in the one folder meant
to stay small and stable.

## A full example

```bash
brupy new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=rabbitmq -o redis=true \
  --docker --git --install --yes
```

This gives you PostgreSQL + SQLModel with Alembic migrations, a Taskiq
worker running over RabbitMQ, and a Redis client for caching on top —
every option this template has, combined. `--yes` accepts the default
for anything you didn't set explicitly, so this is safe to drop into CI
verbatim.

Once it's generated:

```bash
cd my-api

# migrations are on, so the schema doesn't exist until you run this
uv run alembic upgrade head

# start the API
uv run fastapi dev src/my_api/main.py

# in a separate process, start the worker
uv run taskiq worker my_api.worker:broker --app-dir src
```

Open `http://127.0.0.1:8000` — `/docs` has interactive Swagger UI for
the `items` resource, and `POST /tasks/add?a=1&b=2` enqueues a demo
background task and returns its id. The worker needs RabbitMQ reachable
at `RABBITMQ_URL` (see `.env`); the Redis client (`redis_client`,
exported from `core/redis.py`) needs Redis reachable at `REDIS_URL`.

Drop `--docker` and any `-o` flags you don't want; every one of them,
plus `--framework fastapi --template rest-api`, has an interactive
equivalent if you just run `brupy new my-api` and answer the prompts
instead.

## Gotchas worth knowing before you edit the generated code

### Migrations replace auto-create — they don't coexist with it

!!! warning "With `migrations=true`, the database is not created on startup"
    If you chose Alembic migrations, `main.py` never calls `init_db()`
    on startup — the schema comes **solely** from running the migration.
    Start the app against a fresh database without migrating first and
    every query will fail against empty tables.

    ```bash
    uv run alembic revision --autogenerate -m "describe your change"
    uv run alembic upgrade head
    ```

    Run both commands once before the first `fastapi dev`/`fastapi run`,
    and again (with a new message) every time you change a model in
    `models.py`. Always review an autogenerated migration before
    applying it.

    Without migrations (`migrations=false`), it's the opposite: the
    database and its tables **are** created automatically on startup,
    straight from your models — there's no migration history at all.

This split exists because the two behaviors actively conflict if left
both on. An earlier version of this template called `create_all()`
unconditionally, regardless of whether migrations were enabled — so by
the time anyone ran `alembic revision --autogenerate`, the tables
already existed (created by the eager `create_all()`, not by any
migration) and Alembic reported "No changes in schema detected" instead
of generating a real initial migration. On a genuinely fresh database
it's worse than a no-op: `alembic upgrade head` would go on to try
creating tables that already existed outside migration history, since
`alembic_version` was never stamped. `uv sync && pytest` never caught it
— the test fixtures build their own schema directly, bypassing
`init_db()` entirely — it only surfaced by actually running
`alembic revision --autogenerate` against a real, fresh database.

### Tests always use an isolated SQLite database, no matter what you configured

`tests/conftest.py` points every test at its own isolated SQLite
database, regardless of the `database` option you picked for
production. Choosing `database=postgres` does not mean you need a
reachable Postgres instance to run `uv run pytest` — the suite never
touches `DATABASE_URL`. One consequence worth knowing if you're reading
`pyproject.toml`: `aiosqlite` is an **unconditional** dev-dependency
regardless of your database choice, precisely so a `postgres`-only
project's own test suite can still run.

### Taskiq is async-only; Celery is the one Flask shares

Taskiq requires `async def` task functions and only integrates with
async frameworks — that's why it's on offer here but not for Flask's
equivalent template. Celery works with either, so it's the one worker
choice both FastAPI's and Flask's `rest-api` templates share.

### Task modules need an explicit import in `worker.py`

`worker.py` imports each `tasks/*.py` module by name at the **bottom**
of the file, after `broker` (Taskiq) or `celery_app` (Celery) is
defined:

```python
# worker.py, Taskiq version — same shape for Celery
...
broker = ListQueueBroker(url=settings.redis_url)

# Imported last, after `broker` exists: every module in tasks/ needs
# `broker` to register its `@broker.task`-decorated functions, and the
# worker process only discovers those tasks by importing the module
# that defines them — so every new tasks/ module goes on a line here too.
from my_api.tasks import example  # noqa: E402,F401
```

Pointing the worker CLI at `worker.py` doesn't transitively pull in
`tasks/example.py` on its own, and a bare `tasks/__init__.py` doesn't
help either — importing a package doesn't auto-import its submodules.
If you add a new job module under `tasks/`, add its own import line here
too, or the worker will boot cleanly and report zero known tasks with no
error to tell you why. This only shows up by actually starting a worker
process — the code imports and type-checks fine either way, so
`pytest` won't catch a missing line.

### `broker == "redis"` doesn't add a `broker-rabbitmq/`-style layer

There's no dedicated RabbitMQ layer the way there is a `redis/` layer
for the Redis client. RabbitMQ needs no app-level client the way Redis
does for caching — it's purely internal to `worker.py`, via
`taskiq-aio-pika` or Celery's built-in AMQP transport — so the only
RabbitMQ-specific content is a handful of `{% if broker == "rabbitmq" %}`
branches inside `worker.py`, `core/config.py`, `.env`, and
`pyproject.toml`.

## `.agents/skills/`

Every generated project ships an `AGENTS.md` plus a `.agents/skills/`
catalog scoped to exactly the stack your options produced — see
[Agent Skills](../agent-skills.md) for how the catalog itself works.
For this template, the skills you get depend on what you chose:

| Skill | Included when |
|---|---|
| `fastapi` | always |
| `pydantic-settings` | always |
| `pytest` | always |
| `sqlmodel` | `orm=sqlmodel` |
| `sqlalchemy` | `orm=sqlalchemy` |
| `alembic` | `migrations=true` |
| `taskiq` | `worker=taskiq` |
| `celery` | `worker=celery` |
| `redis` | `redis` resolves `true` |

A minimal run (`database=none`, `worker=none`) gets just the always-on
three; the full example above pulls in `fastapi`, `pydantic-settings`,
`pytest`, `sqlmodel`, `alembic`, `taskiq`, and `redis`.

## Docker

Pass `--docker` and Brupy adds a `Dockerfile` (plus a matching
`.dockerignore`) to the project root, alongside a `Docker` section in the
generated `README.md` with the exact build/run commands:

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

Without `--docker`, no Dockerfile is generated at all — nothing to
delete if you don't need it.

## Next

- [Templates overview](index.md) — how `hello-world` and `rest-api`
  compare, for each framework
- [CLI Reference](../cli-reference.md) — every `-o` key this template
  accepts, and every top-level flag
- [Agent Skills](../agent-skills.md) — what's actually inside each
  `.agents/skills/<id>/` entry
