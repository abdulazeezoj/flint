# Agent Skills

Every generated project ships two layers of guidance for whoever works in
it next — human or AI coding agent:

- **`AGENTS.md`** — always-on and lightweight: layout, conventions, the
  run/test commands for what was actually generated. Short enough to read
  in full, every time.
- **`.agents/skills/<id>/`** — deeper, library-specific reference material,
  included *only* for the libraries this particular project actually uses.
  Not a replacement for `AGENTS.md` — the complementary layer you reach for
  when you're actually touching that library, not before.

Skills are the layer worth unpacking: what's actually inside one, how a
project ends up with exactly the set it has, and the full catalog on offer.

## What's inside one skill

Each skill is a directory, `.agents/skills/<id>/`, containing:

```text
.agents/skills/fastapi/
├── SKILL.md                        # overview, when to use, quick reference
├── references/
│   ├── routing-and-dependencies.md # deep API/behavior docs
│   └── gotchas.md
└── guides/
    ├── add-an-endpoint.md          # task-oriented how-to
    └── testing.md
```

- **`SKILL.md`** — the entry point: when to reach for this skill, a quick
  reference for this project's conventions, and links to the rest.
- **`references/*.md`** — deep-dive material: API surface, behavior,
  real gotchas.
- **`guides/*.md`** — task-oriented walkthroughs, like "add a new endpoint
  end to end."

This isn't generic library documentation — it's rendered with the same
templating engine as the rest of the project, so it reads like it was
written for *your* generated code. Here's the quick reference from a real
generated `fastapi` skill's `SKILL.md`, for a project named `my-api`:

```markdown
## Quick reference

- **App entrypoint**: `src/my_api/main.py`. The `FastAPI(...)`
  instance is built once, at module scope — importing this module is
  always safe (no I/O happens on import).
- **Routers**: one file per resource under `src/my_api/routes/`,
  each exporting an `APIRouter` named `router`, included in `main.py` via
  `app.include_router(...)`.
- **Run it**: `uv run fastapi dev src/my_api/main.py` — the
  `fastapi` CLI, not `uvicorn` directly.
```

And a real gotcha from that same skill's `references/gotchas.md`, folded
in from a bug flint's own templates hit while being built:

> **The database is *not* auto-created when migrations are on.** This
> project has `migrations=true`: `main.py` deliberately does **not** call
> `init_db()` at all — schema comes solely from `alembic upgrade head`. If
> you're seeing "table does not exist" errors, that's why: run the
> migration first, don't add a `create_all()` call back into `main.py`'s
> startup path to "fix" it.

That's not a hypothetical warning — it's the actual failure mode you'd
otherwise rediscover the hard way, written down once so nobody (human or
agent) hits it twice.

!!! tip
    Skill content is rendered, not static — it branches on the same
    resolved options your project does. The `sqlalchemy` skill, for
    example, shows async session patterns in a FastAPI project and sync
    patterns in a Flask one, because that's genuinely how this project
    uses the library.

## How selection works

A project only gets the skills for what it actually uses. Each
`template.json` declares a `"skills"` list — the same `id`/`when` shape a
template's own layers use, evaluated against your fully resolved answers.
No `when` means always included; a `when` means "only if these resolved
options match," exactly like a layer.

Here's the (trimmed) list from `fastapi/rest-api`'s `template.json`:

```json
"skills": [
  { "id": "fastapi" },
  { "id": "pydantic-settings" },
  { "id": "pytest" },
  { "id": "sqlmodel",  "when": { "orm": ["sqlmodel"] } },
  { "id": "sqlalchemy", "when": { "orm": ["sqlalchemy"] } },
  { "id": "alembic",   "when": { "migrations": [true] } },
  { "id": "taskiq",    "when": { "worker": ["taskiq"] } },
  { "id": "celery",    "when": { "worker": ["celery"] } },
  { "id": "redis",     "when": { "redis": [true] } }
]
```

`flask/rest-api` mirrors this with its own Flask-flavored equivalents —
`flask-sqlalchemy` and `flask-migrate` instead of `sqlmodel`/`alembic` when
`orm=flask-sqlalchemy`, or plain `alembic` when `orm=sqlalchemy` — and no
`taskiq`, since that worker is FastAPI/async-only in Flint today.

`fastapi/full-stack` and `flask/full-stack` take their framework's
`rest-api` list above and add two more, always: `jinja2` and `htmx` — the
templating and interactivity this template's server-rendered pages are
built on. `css=tailwind` adds a third, `tailwind`, covering the
`@theme`-based build step; `css=vanilla` (the default) doesn't need it.

So in practice:

- A bare `fastapi/hello-world` gets **`fastapi`** and **`pytest`** — and
  `pydantic-settings` too, if you said yes to config.
- A fully-loaded `fastapi/rest-api` with Postgres + SQLModel + migrations +
  Taskiq + Redis gets **`fastapi`**, **`pydantic-settings`**, **`pytest`**,
  **`sqlmodel`**, **`alembic`**, **`taskiq`**, **`redis`** — seven skills,
  each one directly relevant to a choice you actually made. Pick SQLite
  with no ORM instead and you get none of `sqlmodel`/`sqlalchemy`/
  `alembic`/`taskiq`/`redis` at all — there'd be nothing in the project
  for that reference material to describe.

## Why a separate catalog, not more template layers

A template layer (`db-sqlmodel`, `worker-taskiq`, …) is *project content* —
it's rendered into the app itself and naturally belongs to one template. A
skill is *reference material about a library*, and several libraries
(`pytest`, `redis`, `sqlalchemy`, `pydantic-settings`, `alembic`, `celery`)
are used identically-in-spirit by more than one template. Modeling skills
as template-scoped layers would mean either duplicating that content
across `fastapi/rest-api` and `flask/rest-api` — which drifts the moment
one copy gets a fix the other doesn't — or cross-linking between layer
trees, which nothing else in the template system does.

Instead, the catalog lives once, flat, at `src/flint/skills/<id>/` —
outside `templates/` entirely — and each template references catalog
entries by `id`. One `sqlalchemy` skill, referenced by both frameworks,
fixed once.

## The generated index

After rendering every matched skill, Flint also writes
`.agents/skills/README.md` — a plain index of exactly what's present, with
each skill's one-line description pulled from its `skill.json`. It's
generated, not authored: a `git status` or directory listing tells you
*that* something is there, this tells you *what it's for*, without opening
every folder.

## The full catalog

Fourteen skills exist today. Every generated project gets some subset of
these, per the `when` rules above — never one that doesn't apply to what
you picked.

| Skill | Applies to | Description |
| --- | --- | --- |
| `fastapi` | FastAPI | Routing, dependency injection, request/response models, lifespan, and testing conventions for this project's FastAPI app. |
| `flask` | Flask | App-factory, Blueprint, and manual-validation conventions for this project's Flask app, including the WSGI dev-server-vs-gunicorn split. |
| `pydantic-settings` | FastAPI + Flask, when config is enabled | Typed, validated environment-variable configuration via `BaseSettings` — how this project defines, loads, extends, and consumes its `Settings` class. |
| `sqlmodel` | FastAPI, `orm=sqlmodel` | Model definition, async session/query patterns, and Pydantic-vs-table-model conventions for this project's SQLModel data layer. |
| `sqlalchemy` | FastAPI or Flask, `orm=sqlalchemy` | Declarative models, session lifecycle, and query conventions for this project's SQLAlchemy data layer — async with FastAPI, sync with Flask. |
| `flask-sqlalchemy` | Flask, `orm=flask-sqlalchemy` | The `db = SQLAlchemy()` extension object, `init_app` wiring, `db.Model` definitions, and app-context-bound sessions for this project's Flask data layer. |
| `alembic` | FastAPI (any ORM) or Flask (`orm=sqlalchemy`), `migrations=true` | Autogenerating, reviewing, and applying database migrations for this project's SQLModel/SQLAlchemy models, and the src-layout + `create_all` gotchas that break it silently. |
| `flask-migrate` | Flask, `orm=flask-sqlalchemy`, `migrations=true` | The `flask db ...` CLI, the `Migrate`/`db` wiring in `core/db.py`, and the `create_all()`-vs-migrations gotcha for this project's Flask-SQLAlchemy app. |
| `taskiq` | FastAPI, `worker=taskiq` | Async task queue conventions for this project's Taskiq worker: broker setup, task discovery, and the `.kiq()` enqueue pattern. |
| `celery` | FastAPI or Flask, `worker=celery` | Task definition, enqueuing, and result-checking conventions for this project's Celery background worker. |
| `redis` | FastAPI or Flask, `redis=true` | Module-level Redis client setup and basic get/set/delete caching conventions for this project's Redis add-on. |
| `pytest` | FastAPI + Flask | Fixtures, async test setup, the isolated-test-database pattern, and parametrize — how this project's test suite is built and how to extend it. |
| `jinja2` | FastAPI + Flask, `full-stack` | Template inheritance, includes, autoescaping, and whitespace control — how this project's server-rendered pages use Jinja2. |
| `htmx` | FastAPI + Flask, `full-stack` | hx-post/hx-target/hx-swap/hx-trigger, out-of-band swaps, and the fragment-response contract — how this project's Todo list updates in place without a client-side JS framework. |
| `tailwind` | FastAPI + Flask, `full-stack` with `css=tailwind` | The `@theme` directive, utility classes, and the standalone-CLI build step — how this project's `css=tailwind` option styles pages without Node.js. |

## Why this exists

Generic library docs and an agent's own training knowledge both drift from
what a specific generated project actually does — a hallucinated import
path, an ORM pattern that doesn't match the template's conventions, a
"fix" that reintroduces a bug flint's own templates already hit once. The
skills catalog closes that gap: it's reference material about *this
project's* actual code, kept in sync with the templates it documents.

The gotchas folded into each skill's `references/gotchas.md` aren't
speculative either — they're bugs flint's own templates hit while being
built and verified, written down once so the next person (or agent)
doesn't rediscover them the hard way. A few examples: task-discovery
mistakes baked into the `taskiq` and `celery` skills, and the
`create_all()`-vs-real-migrations bug that shows up in `alembic`,
`flask-migrate`, `flask-sqlalchemy`, and `sqlalchemy` alike — run both and
Alembic permanently reports "No changes in schema detected" instead of
capturing the real schema.

## Next

- [Templates](project-templates/index.md) — how a template's `files/`,
  layers, options, and skills fit together
- [Getting Started](getting-started.md) — generate your first project
