# Template: fastapi / full-stack

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A layered FastAPI app with the same opinionated, Next.js-inspired
layout as `rest-api` (PRODUCT_ARCH.md §4.4) — `main.py`/`worker.py` are
fixed entrypoints, `routes/`/`tasks/` are "one file per resource/job"
folders, `core/` holds shared infrastructure — but server-rendered
instead of JSON: a `todos` resource backed by a Jinja2 `templates/` tree
and HTMX partial swaps rather than a `schemas.py` request/response
contract. `pydantic-settings` config is always on. A single Todo list
(`GET /`, `POST /todos`, `POST /todos/{id}/toggle`, `DELETE
/todos/{id}`, each returning HTML — a full page for `/`, a fragment for
everything else) backed by an in-memory store by default, or a real
database if one is chosen. Shares every non-presentation option with
`rest-api` (database/ORM/migrations/worker/broker/redis) so the two
templates feel like siblings, not two unrelated designs.

## Options (`template.json`, resolved in this order)

Identical to `rest-api`'s — see that template's `README.md` for the
full table. Kept in lockstep deliberately: same keys, same defaults,
same `when`/`skip_value` wiring.

## Layout (of this template's directory, not the generated project)

```
template.json            options + layers (see below) — same shape as rest-api's
README.md                this file
files/                    always rendered — main.py, core/config.py,
                          core/templates.py (shared Jinja2Templates instance),
                          routes/todos.py (in-memory), templates/, static/css/style.css,
                          tests/test_main.py, env.jinja (renders to both .env and .env.example)
docker/                   iff --docker
db-sqlmodel/              iff orm == sqlmodel — overrides routes/todos.py,
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

`docker/`, `worker-taskiq/`, `worker-celery/`, `redis/`, and both
`migrations-*/` layers (bar one import line — `Item` → `Todo` in
`env.py`) are **copied verbatim from `rest-api`** — they're generic
infrastructure with no dependency on what the app actually renders.
Only the presentation layer (`files/` and the `routes/todos.py` in each
`db-*` layer) is genuinely new content. `db-sqlmodel`/`db-sqlalchemy`'s
`core/db.py` and `tests/conftest.py` are also unchanged from `rest-api`
— fully generic, no `Item`/`Todo` reference in either.

The **generated project's** layout (what a developer actually sees) is:

```
src/{package_name}/
  main.py              FastAPI entrypoint — fixed name/location, mounts /static
  worker.py            {worker} entrypoint — fixed name/location (iff a worker is chosen)
  routes/               one module per HTTP resource — returns HTML, not JSON
  templates/             Jinja2 templates: base.html, index.html, partials/
  static/css/            the UI (style.css) — served at /static
  tasks/                 one module per background job (iff a worker is chosen)
  core/                   shared infrastructure: config.py, templates.py, db.py, redis.py
  models.py                {orm} models — iff a database is chosen
```

No `schemas.py`: unlike `rest-api`, there's no separate request/response
contract to declare — the in-memory layer's `Todo` is a plain
`@dataclass` defined right in `routes/todos.py` (nothing else uses it),
and the DB-backed layers use their `models.py` `Todo` directly as the
template context object. Adding one back is a reasonable next step if a
future resource needs input validation beyond "a required `title`
field," but it would be dead weight for what this template ships today.

## Two gotchas specific to this template — don't regress them

See `rest-api`'s `README.md` for the four gotchas it shares with this
template (the `__init__.py.jinja` requirement, `alembic.ini`'s
`prepend_sys_path`, `worker.py`'s bottom-of-file task imports, and the
`db-*` layers' `core/db.py` + top-level `models.py` split — all apply
here unchanged). Specific to `full-stack`:

1. **Template files under `files/src/{package_name}/templates/` and
   `static/` have no `.jinja` suffix, unlike almost everything else in
   this codebase.** They contain Jinja2 syntax meant for the *generated
   app's own* runtime `Jinja2Templates` instance (`{% block %}`,
   `{% for todo in todos %}`, `{{ todo.title }}`) — if they carried a
   `.jinja` suffix, flint's own generator (`generator.py`) would render
   them through *its* Jinja environment first, silently evaluating and
   stripping that syntax before it ever reached the generated project.
   `project_name`/`app_name`-style values that do need substituting are
   passed into the runtime template context from the route handler
   (`{"app_name": settings.app_name, ...}`) instead — resolved at
   request time by the generated app, not at generation time by flint.
2. **The empty-state `<li>` needs an explicit out-of-band removal.**
   `templates/partials/todo_created.html` (what `POST /todos` returns)
   includes the new `todo_item.html` fragment *and* a
   `<li id="empty-state" hx-swap-oob="delete">` — HTMX only removes an
   OOB element if one with that `id` is currently in the DOM, so this is
   a no-op once the list already has items, but correctly clears
   "Nothing to do yet" on the very first todo. `DELETE /todos/{id}`
   mirrors this in the other direction: it checks whether the store is
   now empty and returns `partials/empty_state.html` (swapped in over
   the deleted `<li>`) instead of an empty response, so the message
   comes back when the last todo goes.

## Testing this template

`tests/test_generator.py` (or a dedicated block/module, same pattern as
`rest-api`) covers the same combinations: in-memory, SQLite+SQLModel+
migrations, Postgres+SQLAlchemy, workers, brokers, redis, "all features
combined." Same caveat as `rest-api`: file-existence/`ast.parse()`/
`tomllib` checks catch template bugs, not runtime ones. Before shipping
a change here, manually verify at least one combination end-to-end —
`uv sync`, `uv run pytest`, then actually load `/` in a browser (or
`curl`) and exercise create/toggle/delete, since the HTMX
partial-swap/OOB behavior above is exactly the kind of thing that looks
fine in a unit test and is broken in a real browser.

## Adding a new option or layer

Same as `rest-api` — add an entry to `template.json`'s
`options`/`layers` arrays and the corresponding files, no code changes
needed elsewhere.

## Adding a new resource (e.g. beyond `todos`)

A new resource means a new `routes/<name>.py` (+ one
`app.include_router(...)` line in `main.py`), a `templates/<name>/`
subtree (or reuse `partials/` if it's a similarly small fragment-swap
UI), and — if it needs background work — a new `tasks/<name>.py` (+ one
import line in `worker.py`). Keep returning HTML fragments from
state-changing endpoints, not JSON — mixing the two within one template
would break the "every route is either a full page or an HTMX target"
convention this template is built around.
