# Framework / template / option matrix

Every project comes from exactly one `<framework>/<template>` pair,
plus whatever options that template declares. Framework and template
are picked with `--framework`/`--template`; options with repeatable
`-o key=value`.

## The six shipped combinations

| Framework | Template | What it is |
|---|---|---|
| `fastapi` | `hello-world` | A minimal FastAPI app, one Hello World endpoint. |
| `fastapi` | `rest-api` | A layered FastAPI REST API: pydantic-settings, your choice of database/ORM, migrations, background worker (Taskiq or Celery), Redis caching. |
| `fastapi` | `full-stack` | Same options as `rest-api`, server-rendered instead of JSON — Jinja2 + HTMX, a Todo list, no client-side JS framework. |
| `flask` | `hello-world` | A minimal Flask app, one Hello World endpoint. |
| `flask` | `rest-api` | A layered Flask REST API: pydantic-settings, your choice of database/ORM, migrations, a Celery background worker, optional Redis caching. |
| `flask` | `full-stack` | Same options as `rest-api`, server-rendered instead of JSON — Jinja2 + HTMX, a Todo list, no client-side JS framework. |

Every template is deliberately the same shape across both frameworks —
same options, same conventions — so picking one framework over the
other for the same template isn't a relearn, and `full-stack` reuses
`rest-api`'s exact option set (only the presentation layer differs: HTML
fragments instead of JSON). Run `brupy list-templates` to check this
matrix is still current (a new framework/template could exist by the
time this is read).

## `hello-world` options (same for both frameworks)

| Flag | Values | Default | Effect |
|---|---|---|---|
| `-o config=<bool>` | `true` / `false` | `false` | Adds a `pydantic-settings`-based `core/config.py` module instead of hardcoded values. |

## `fastapi/rest-api` options

Resolved in this order — later options can depend on earlier ones:

| Option | Choices | Default | Depends on |
|---|---|---|---|
| `database` | `none` (in-memory), `sqlite`, `postgres` | `sqlite` | — |
| `orm` | `sqlmodel`, `sqlalchemy` | `sqlmodel` | only asked if `database != none`; resolves to `none` otherwise |
| `migrations` | yes/no | `true` | only asked if `database != none`; resolves to `false` otherwise |
| `worker` | `none`, `taskiq`, `celery` | `none` | — |
| `broker` | `redis`, `rabbitmq` | `redis` | only asked if `worker != none`; resolves to `none` otherwise |
| `redis` | yes/no | `false` | only asked if `broker` is `rabbitmq` or `none`; resolves to `true` if `broker == redis` |

The last row is easy to misread: **`redis` (the caching add-on)
depends on `broker`, not on `worker`.** Picking `broker=redis` for a
worker already implies Redis is in play, so the caching question is
skipped and resolves to `true`. Picking `broker=rabbitmq` (or no
worker at all) means Redis isn't already present, so the question is
actually asked.

## `flask/rest-api` options

| Key | Choices | Default | Depends on |
|---|---|---|---|
| `database` | `none`, `sqlite`, `postgres` | `sqlite` | — |
| `orm` | `flask-sqlalchemy`, `sqlalchemy` (manual) | `flask-sqlalchemy` | asked only if `database != none`; otherwise skipped, resolves to `none` |
| `migrations` | yes/no | `true` | asked only if `database != none`; otherwise skipped, resolves to `false` |
| `worker` | `none`, `celery` | `none` | — |
| `broker` | `redis`, `rabbitmq` | `redis` | asked only if `worker == celery`; otherwise skipped, resolves to `none` |
| `redis` | yes/no | `false` | asked only if `broker` is `rabbitmq` or `none`; if `broker == redis`, skipped and resolves to `true` |

Note Flask's `rest-api` has no `taskiq` worker choice — Taskiq is
async-first and doesn't fit Flask's sync/WSGI model, so Celery is the
only worker option.

## `full-stack` options (both frameworks)

`fastapi/full-stack` takes exactly the options listed above for
`fastapi/rest-api`; `flask/full-stack` takes exactly the options listed
above for `flask/rest-api` — same keys, same defaults, same dependency
wiring. Reach for `full-stack` instead of `rest-api` when the user wants
server-rendered pages (a Todo list, HTML fragments swapped in via HTMX)
rather than a JSON API; everything about the database/ORM/migrations/
worker/broker/redis choices is unchanged. `full-stack` has one extra
option neither `rest-api` nor `hello-world` has, since it's about
presentation, not the backend stack:

| Option | Choices | Default |
|---|---|---|
| `css` | `vanilla` (hand-written CSS, no build step), `tailwind` (Tailwind CSS v4, standalone CLI — no Node.js/npm) | `vanilla` |

Reach for `-o css=tailwind` whenever the user mentions Tailwind, wants a
more polished/production-ready look than a plain stylesheet, or is
already a Tailwind user — it's still zero extra tooling to install
beyond what `uv sync` already pulls in (`pytailwindcss` downloads the
platform binary itself). One thing to flag: a freshly generated
`css=tailwind` project has **no styling until the CSS is built once** —
`uv run tailwindcss -i src/<package>/static/css/input.css -o
src/<package>/static/css/style.css` (add `--watch` while iterating). If
`--docker` was also passed, the Dockerfile runs this automatically as
part of the image build, so that combination needs no extra step.

## Example commands

FastAPI, Postgres + SQLModel + migrations + a Taskiq worker over Redis:

```bash
brupy new my-api --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=redis --yes
```

Flask, SQLite + manual SQLAlchemy, no worker:

```bash
brupy new my-api --framework flask --template rest-api \
  -o database=sqlite -o orm=sqlalchemy --yes
```

Either `hello-world`, with the optional config module:

```bash
brupy new my-api --framework fastapi --template hello-world -o config=true --yes
```

FastAPI, server-rendered Todo list (HTMX) with SQLite + SQLModel:

```bash
brupy new my-app --framework fastapi --template full-stack \
  -o database=sqlite -o orm=sqlmodel --yes
```

Flask, server-rendered with Tailwind CSS instead of the vanilla stylesheet:

```bash
brupy new my-app --framework flask --template full-stack \
  -o database=sqlite -o css=tailwind --yes
```
