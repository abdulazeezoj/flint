# Flask · Full-Stack

The server-rendered counterpart to [Flask · REST API](flask-rest-api.md),
and the Flask sibling of [FastAPI · Full-Stack](fastapi-full-stack.md).
Same options, same layered architecture, same `pydantic-settings`-backed
config, same `create_app()` application-factory pattern as `rest-api` —
the only thing that changes is what a route returns. Where `rest-api`
returns JSON via `jsonify(...)`, this template returns HTML: a Jinja2
page for `GET /`, and an HTML (or plain-text, for a 404) fragment for
every state-changing request, swapped into the page by
[HTMX](https://htmx.org) without a full reload and without any
client-side JavaScript framework.

It generates one example resource, a Todo list (`GET /`, `POST /todos`,
`POST /todos/<id>/toggle`, `DELETE /todos/<id>`), backed by an in-memory
store by default or a real database if you pick one — enough to see
every layer actually wired together, including the parts specific to a
server-rendered UI (partial swaps, an out-of-band DOM update), not just
a JSON contract.

## Options

Identical to `rest-api`'s — same keys, same defaults, same dependency
wiring, same Flask-SQLAlchemy/manual-SQLAlchemy split, same
Celery-only worker choice. See
[Flask · REST API → Options](flask-rest-api.md#options) for the full
table and the reasoning behind each of those; it's not repeated here
because it's genuinely the same logic, unmodified.

## `create_app()`, unchanged

This template uses the exact same application-factory pattern as
`rest-api`, for the exact same reason: a module-level `app =
Flask(__name__)` would open a database connection the instant `main.py`
is *imported* — by `pytest`, by `flask db ...`, by `alembic` — not just
when the app actually starts. See
[Flask · REST API → The core idea](flask-rest-api.md#the-core-idea-create_app-not-app-flask__name__)
for the full explanation, including the real failure it was written to
prevent (`uv run pytest` failing on import alone, before any test ran,
with the database stopped). Nothing about that reasoning changes here.

One thing that *is* simpler than FastAPI's equivalent: Flask resolves
`templates/` and `static/` automatically from wherever `Flask(__name__)`
is constructed — which is `main.py`, so both directories are found
without any extra configuration. FastAPI's `full-stack` template needs
an explicit `Jinja2Templates(directory=...)` and `app.mount("/static",
StaticFiles(...))`; this template needs neither.

## What gets generated

```text
src/{package_name}/
  main.py              Flask entrypoint — create_app() factory, no module-level app
  worker.py            Celery entrypoint (iff worker == celery)
  routes/               one module per HTTP resource — Flask Blueprints
    todos.py              returns HTML/fragments, not JSON
  templates/             Jinja2 templates — found automatically, no setup needed
    base.html              shell — HTMX script tag, stylesheet link
    index.html              the Todo page
    partials/               HTMX-swapped fragments
      todo_item.html          one <li>
      empty_state.html         the "nothing to do yet" message
      todo_created.html        todo_item.html + an out-of-band delete of empty_state
  static/               served at /static, same automatic resolution
    css/style.css          the whole UI — no build step, no framework
  core/                  shared infrastructure
    config.py              Settings (pydantic-settings, always)
    db.py                  engine/session setup (iff database != none)
    redis.py                Redis client (iff redis resolves true)
  tasks/                 one module per background job (iff worker == celery)
    example.py             the /tasks/add demo task
  models.py               {orm} models (iff database != none)
migrations/ or alembic/  iff migrations — directory name depends on orm, see rest-api's docs
tests/
AGENTS.md
Dockerfile                iff --docker
```

No `schemas.py`: unlike `rest-api`, there's no request/response contract
to validate manually via `.model_validate()`/`.model_dump()`. The
in-memory layer's `Todo` is a plain `@dataclass` defined right in
`routes/todos.py`; the DB-backed layers pass their `models.py` `Todo`
straight into `render_template(...)` as the context object.

## Why `templates/` and `static/` files have no `.jinja` suffix

Worth understanding before you touch these files — it's the opposite of
every other file flint ships, and the reasoning is identical to the
FastAPI template's (see
[FastAPI · Full-Stack](fastapi-full-stack.md#why-templates-and-static-files-have-no-jinja-suffix)
for the full explanation). Short version: `templates/index.html` and
friends contain Jinja2 syntax meant for **Flask's own** runtime
`render_template()` call (`{% block %}`, `{% for todo in todos %}`,
`{{ todo.title }}`), not for flint's generator. If they carried a
`.jinja` suffix, flint would render them at *generation* time, silently
stripping that syntax before the file ever reached the generated
project. They're copied byte-for-byte instead; the one flint-resolved
value they need (`app_name`) is passed in from the route handler at
request time via `render_template("index.html", app_name=settings.app_name,
...)`.

## The empty-state swap: an HTMX out-of-band update

Identical mechanism to the FastAPI template's, because it's the exact
same `partials/todo_created.html` file, copied byte-for-byte — see
[FastAPI · Full-Stack → The empty-state swap](fastapi-full-stack.md#the-empty-state-swap-an-htmx-out-of-band-update)
for the full explanation of the `hx-swap-oob="delete"` trick and how
`DELETE /todos/<id>` mirrors it in the other direction.

## A full example

```bash
flint new my-app \
  --framework flask --template full-stack \
  -o database=postgres -o orm=flask-sqlalchemy -o migrations=true \
  -o worker=celery -o broker=redis \
  --docker --git --install --yes
```

Once it's generated:

```bash
cd my-app

# migrations are on, so the schema isn't there yet — create and apply it:
uv run flask --app src/my_app/main.py db migrate -m "initial migration"
uv run flask --app src/my_app/main.py db upgrade

# start the app
uv run flask --app src/my_app/main.py run
```

Then open `http://127.0.0.1:5000` — a Todo list. Type into the input and
submit: the new item appears without a page reload. Check its box: it
gets a strikethrough, also without a reload. Delete it: it's removed,
and if it was the last one, "Nothing to do yet" reappears — all via
HTMX requests you can watch in your browser's network tab, each
returning a small HTML fragment instead of a full page or JSON.

Drop `--docker` and any `-o` flags you don't want; every one of them,
plus `--framework flask --template full-stack`, has an interactive
equivalent if you just run `flint new my-app` and answer the prompts
instead.

## Gotchas worth knowing before you edit the generated code

### Migrations, worker task discovery, isolated test databases

This template shares its database/ORM/migrations/worker/broker
machinery byte-for-byte with `rest-api` — the two-migration-tools split
by `orm`, the "database is not auto-created when migrations are on"
behavior, the SQLite `:memory:`/`StaticPool` handling, the Celery-only
worker choice, and the bottom-of-file `worker.py` task imports all apply
here identically. See
[Flask · REST API → Gotchas](flask-rest-api.md#migrations) and the
sections after it for the full write-ups — not repeated here since
nothing about them changes when the presentation layer is HTML instead
of JSON.

### A route that changes state returns a fragment, not the whole page

`routes/todos.py` never re-renders `index.html` from a `POST`/`DELETE`
view function — only `GET /` does. Every state-changing route returns
exactly the fragment that changed (`partials/todo_item.html`,
`partials/todo_created.html`, or `partials/empty_state.html`, or a
plain `"Todo not found", 404` for a missing id), and lets
`hx-target`/`hx-swap` on the triggering element decide where it lands.
If you add a new state-changing endpoint, give it its own fragment
template rather than reaching for `index.html`.

### 404s are plain text, not `jsonify(...)`

`rest-api`'s routes return `jsonify({"detail": "..."}), 404` for a
missing resource — this template's routes return a bare `"Todo not
found", 404` instead. Deliberate: this template's convention is "every
response is HTML or plain text, never JSON" (see `AGENTS.md`'s
Conventions section in the generated project), and a `jsonify(...)`
error response would be the one place that broke it.

## `.agents/skills/`

Every generated project ships an `AGENTS.md` plus a `.agents/skills/`
catalog scoped to exactly the stack your options produced — see
[Agent Skills](../agent-skills.md) for how the catalog itself works.
Identical skill set to `rest-api`'s (see
[Flask · REST API → `.agents/skills/`](flask-rest-api.md#agentsskills)) —
picking `full-stack` over `rest-api` doesn't change which library
skills you get, since the underlying stack choices are the same.

## `--docker`

Pass `--docker` and flint adds a `Dockerfile` (`uv`-based) plus
`.dockerignore` — identical to `rest-api`'s, including running under
**gunicorn** via its factory-call syntax
(`{package_name}.main:create_app()`), not the Flask dev server:

```bash
docker build -t my-app .
docker run -p 8000:8000 my-app
```

Same port note as `rest-api`: the containerized app listens on **8000**
(gunicorn's bind), while `flask run` locally defaults to **5000**.

## Next

- [Templates overview](index.md) — how `hello-world`, `rest-api`, and
  `full-stack` compare, for each framework
- [Flask · REST API](flask-rest-api.md) — the JSON counterpart this
  template shares almost all of its machinery with
- [FastAPI · Full-Stack](fastapi-full-stack.md) — the same Todo app,
  same `templates/`/`static/` content, on FastAPI's async stack
- [CLI Reference](../cli-reference.md) — every `-o` key this template
  accepts, and every top-level flag
