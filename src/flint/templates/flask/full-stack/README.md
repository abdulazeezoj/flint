# Template: flask / full-stack

Maintainer documentation for this template — not part of the generated
project (that's `files/README.md.jinja`).

## What it generates

A layered Flask app with the same opinionated, Next.js-inspired layout
as `rest-api` (PRODUCT_ARCH.md §4.4) — `main.py`/`worker.py` are fixed
entrypoints, `routes/`/`tasks/` are "one file per resource/job" folders,
`core/` holds shared infrastructure — but server-rendered instead of
JSON: a `todos` resource backed by a Jinja2 `templates/` tree and HTMX
partial swaps rather than a `schemas.py` request/response contract.
`pydantic-settings` config is always on. A single Todo list (`GET /`,
`POST /todos`, `POST /todos/<id>/toggle`, `DELETE /todos/<id>`, each
returning HTML or plain text — a full page for `/`, a fragment for
everything else, plain text for a 404) backed by an in-memory store by
default, or a real database if one is chosen. Shares every
non-presentation option with `rest-api` (database/ORM/migrations/
worker/broker/redis) so the two templates feel like siblings, not two
unrelated designs — and, in turn, with `fastapi/full-stack`, whose
`templates/`/`static/` content is copied byte-for-byte into this
template (see "Sharing with `fastapi/full-stack`" below).

## Options (`template.json`, resolved in this order)

The database/ORM/migrations/worker/broker/redis options are identical
to `rest-api`'s — see that template's `README.md` for the full table.
Kept in lockstep deliberately: same keys, same defaults, same
`when`/`skip_value` wiring. One option is unique to this template,
since it's about presentation, not the backend stack — same as
`fastapi/full-stack`'s:

| key | type | default | choices |
|---|---|---|---|
| `css` | select | `vanilla` | `vanilla` (hand-written CSS, no build step), `tailwind` (Tailwind CSS v4 via the standalone CLI) |

No `when`/`skip_value` — it's independent of every other option.

## Layout (of this template's directory, not the generated project)

```
template.json            options + layers (see below) — same shape as rest-api's
README.md                this file
files/                    always rendered — main.py, core/config.py,
                          routes/todos.py (in-memory), templates/base.html +
                          index.html + partials/ (vanilla-styled), tests/test_main.py,
                          env.jinja (renders to both .env and .env.example)
docker/                   iff --docker
db-flask-sqlalchemy/     iff orm == flask-sqlalchemy — overrides routes/todos.py,
                          adds core/db.py + top-level models.py
db-sqlalchemy/            iff orm == sqlalchemy — same shape, manual SQLAlchemy
migrations-flask-sqlalchemy/  iff migrations && orm == flask-sqlalchemy — Flask-Migrate
migrations-sqlalchemy/    iff migrations && orm == sqlalchemy — Alembic
worker-celery/            iff worker == celery — worker.py, tasks/example.py;
                          worker.py itself branches on `broker` (redis/rabbitmq)
redis/                    iff redis resolves true — core/redis.py client
css-vanilla/              iff css == vanilla (the default) — static/css/style.css,
                          the hand-written CSS `files/`'s templates are styled for
css-tailwind/             iff css == tailwind — static/css/input.css (Tailwind
                          source) + overrides templates/index.html and
                          templates/partials/{todo_item,empty_state}.html with
                          Tailwind utility classes instead
```

`docker/`, `worker-celery/`, `redis/`, `migrations-flask-sqlalchemy/`
(entirely), and `migrations-sqlalchemy/` (bar one import line — `Item`
→ `Todo` in `env.py`) are **copied verbatim from `rest-api`** — generic
infrastructure with no dependency on what the app actually renders.
Both `db-*` layers' `core/db.py` and `tests/conftest.py` are also
unchanged from `rest-api` — fully generic, no `Item`/`Todo` reference
in either. `docker/`'s `Dockerfile.jinja` has exactly one `css`-aware
line: a `RUN uv run tailwindcss ... --minify` build step, gated `{% if
css == "tailwind" %}`, so a container always ships current CSS
regardless of which variant was chosen.

The **generated project's** layout (what a developer actually sees) is:

```
src/{package_name}/
  main.py              Flask entrypoint — create_app(), fixed name/location
  worker.py            {worker} entrypoint — fixed name/location (iff a worker is chosen)
  routes/               one module per HTTP resource — returns HTML/text, not JSON
  templates/             Jinja2 templates: base.html, index.html, partials/
  static/css/            served at /static — style.css (iff css == vanilla),
                          or input.css (tracked) + style.css (git-ignored build
                          output, iff css == tailwind)
  core/                   shared infrastructure: config.py, db.py, redis.py
  models.py                {orm} models — iff a database is chosen
```

No `schemas.py`: unlike `rest-api`, there's no separate request/response
contract to declare — the in-memory layer's `Todo` is a plain
`@dataclass` defined right in `routes/todos.py` (nothing else uses it),
and the DB-backed layers use their `models.py` `Todo` directly as the
template context object.

Also no `core/templates.py` (fastapi/full-stack has one): Flask's
`render_template()` works as a bare module-level function using the
app's own `template_folder`/`static_folder` — both resolve automatically
from `Flask(__name__)`'s location (`main.py`, alongside `templates/` and
`static/`), no explicit `Jinja2Templates`-style setup object needed.

## Sharing with `fastapi/full-stack`

`files/src/{package_name}/templates/` (vanilla-styled) and both
`css-vanilla/`/`css-tailwind/` layers are **copied byte-for-byte** from
`fastapi/full-stack` — same HTML, same CSS, same `input.css` `@theme`
tokens, same HTMX attributes, same OOB-swap trick. This works because
both frameworks' template files contain only *runtime* Jinja2 syntax
(see gotcha #1 below) and reference exactly the same context variable
names (`app_name`, `todos`, `todo`) — the presentation layer doesn't
care which Python web framework is rendering it. If you change one
framework's `templates/`/`static/`/`css-*` content, copy the same
change to the other — don't let them drift; a Flask-only or
FastAPI-only UI tweak defeats the point of the two templates feeling
like siblings.

## Two gotchas specific to this template — don't regress them

See `rest-api`'s `README.md` for the gotchas it shares with this
template (the `flask-sqlalchemy` vs. manual-`sqlalchemy` `db.py`
divergence, the `worker.py` bottom-of-file task imports, the SQLite
`:memory:` `StaticPool` requirement — all apply here unchanged).
Specific to `full-stack`:

1. **Template files under `files/src/{package_name}/templates/` and
   `static/` have no `.jinja` suffix, unlike almost everything else in
   this codebase.** They contain Jinja2 syntax meant for Flask's *own*
   runtime template rendering (`{% block %}`, `{% for todo in todos %}`,
   `{{ todo.title }}`) — if they carried a `.jinja` suffix, flint's own
   generator (`generator.py`) would render them through *its* Jinja
   environment first, silently evaluating and stripping that syntax
   before it ever reached the generated project. `project_name`/
   `app_name`-style values that do need substituting are passed into
   `render_template(..., app_name=settings.app_name, ...)` from the
   route handler instead — resolved at request time by the generated
   app, not at generation time by flint.
2. **The empty-state `<li>` needs an explicit out-of-band removal** —
   same mechanism as `fastapi/full-stack`, since it's the exact same
   `templates/partials/todo_created.html`: a `<li id="empty-state"
   hx-swap-oob="delete">` alongside the new todo fragment, a no-op once
   the list already has items but correctly clears "Nothing to do yet"
   on the first todo. `DELETE /todos/<id>` mirrors this in the other
   direction, returning `partials/empty_state.html` instead of an empty
   response when the store is now empty.
3. **`tests/test_main.py.jinja` lives in `files/`, shared by every `css`
   variant — never assert against a CSS class name in it.** An earlier
   draft asserted `b'class="todo-item done"' in toggle_response.data` to
   check the toggle endpoint marks a todo done; that string is
   `css-vanilla`-only and doesn't exist in `css-tailwind`'s utility-class
   markup, so the shared test failed the instant `css=tailwind` was
   exercised end-to-end (caught by actually running `uv run pytest`
   against a generated `css=tailwind` project, not by `ast.parse()`).
   Fixed by asserting `b"checked" in toggle_response.data` instead — the
   checkbox's `checked` attribute is present in both variants' markup,
   so the test verifies the actual behavior (toggling `done`) without
   depending on how that state happens to be styled.

## Testing this template

`tests/test_generator.py` (or a dedicated block/module, same pattern as
`rest-api`) covers the same combinations: in-memory, SQLite+Flask-
SQLAlchemy+migrations, Postgres+manual SQLAlchemy, Celery+both brokers,
redis, "all features combined." Same caveat as `rest-api`: file-
existence/`ast.parse()`/`tomllib` checks catch template bugs, not
runtime ones. Before shipping a change here, manually verify at least
one combination end-to-end — `uv sync`, `uv run pytest`, then actually
load `/` in a browser (or `curl`) and exercise create/toggle/delete,
since the HTMX partial-swap/OOB behavior above is exactly the kind of
thing that looks fine in a unit test and is broken in a real browser.

## Adding a new option or layer

Same as `rest-api` — add an entry to `template.json`'s
`options`/`layers` arrays and the corresponding files, no code changes
needed elsewhere.

## Adding a new resource (e.g. beyond `todos`)

A new resource means a new `routes/<name>.py` (+ one
`app.register_blueprint(...)` line in `main.py`), a `templates/<name>/`
subtree (or reuse `partials/` if it's a similarly small fragment-swap
UI), and — if it needs background work — a new `tasks/<name>.py` (+ one
import line in `worker.py`). Keep returning HTML/plain-text fragments
from state-changing endpoints, not JSON — mixing the two within one
template would break the "every route is either a full page or an HTMX
target" convention this template is built around.
