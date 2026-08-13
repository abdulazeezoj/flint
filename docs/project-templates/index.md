# Templates

Every project Flint generates comes from exactly one `<framework>/<template>`
pair, plus whatever options that template offers. Three distinct concepts,
picked in this order:

- **Framework** — the underlying library: `fastapi` or `flask`. Selected
  first.
- **Template** — a specific project shape built on that framework:
  `hello-world` or `rest-api`. Selected second, scoped to the framework you
  just picked.
- **Option** — a further, template-specific choice, declared by the template
  itself — not hardcoded in Flint. `hello-world` asks only whether to add
  `pydantic-settings` config; `rest-api` asks for a database, an ORM,
  whether to add migrations, a background worker, a message broker, and
  Redis. Flint's wizard has no built-in notion of "database" or "worker" —
  it just renders whatever the chosen template's `template.json` declares.

```text
flint new my-api --framework fastapi --template rest-api -o database=postgres
#                 ^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^
#                 framework           template             template option
```

This is what lets Flint grow in three independent directions — more
frameworks, more templates per framework, richer options per template —
without any one axis blocking the others.

## How a template is put together

You don't need to know this to use Flint, but it explains why the pages
below look the way they do. Each template directory bundles:

- **`files/`** — always rendered. The base project: entrypoint, tests,
  `pyproject.toml`, `README.md`, `AGENTS.md`, `.gitignore`.
- **Extra layers** — directories rendered *in addition to* `files/`, only
  when a condition matches (e.g. a `docker` layer that's added only when
  you pass `--docker`, or a `db-sqlmodel` layer added only when you pick
  SQLModel as the ORM). A later layer's file silently overwrites an
  earlier one at the same path — that's how choosing a database swaps in a
  DB-backed route file over the base in-memory one, without the shared
  file needing a maze of conditionals.
- **Options** — the template's own extra prompts (`-o key=value`), each
  optionally depending on an earlier option's value. Picking "no database"
  on `rest-api`, for instance, means the ORM and migrations questions
  aren't asked at all — they resolve to a documented default instead.
- **Skills** — a declarative list of which `.agents/skills/<id>/` entries
  to include, each optionally gated the same way layers are (e.g. the
  `sqlmodel` skill only ships when you picked SQLModel). See
  [Agent Skills](../agent-skills.md) for what these actually contain.

The Jinja mechanics behind rendering (how `{{package_name}}` path segments
and `*.jinja` files work) are contributor-facing detail — see
[Contributing](../contributing.md) if you're curious or adding a template.

## The four shipped templates

Two frameworks, two templates each, same shape on both — so switching
between FastAPI and Flask isn't a relearn.

| Framework | Template | What it is | Docs |
|---|---|---|---|
| FastAPI | Hello World | A minimal FastAPI app with a single Hello World endpoint, managed with uv. | [FastAPI · Hello World](fastapi-hello-world.md) |
| FastAPI | REST API | A layered FastAPI REST API with pydantic-settings, and your choice of database/ORM, migrations, background worker (Redis or RabbitMQ), and Redis caching. | [FastAPI · REST API](fastapi-rest-api.md) |
| Flask | Hello World | A minimal Flask app with a single Hello World endpoint, managed with uv. | [Flask · Hello World](flask-hello-world.md) |
| Flask | REST API | A layered Flask REST API with pydantic-settings, and your choice of database/ORM, migrations, and a Celery background worker (Redis or RabbitMQ) with optional Redis caching. | [Flask · REST API](flask-rest-api.md) |

!!! tip
    Not sure what's available or which options a template accepts? Run
    `flint list-templates` — it prints every framework/template pair,
    including anything still "coming soon," with no project generated. See
    [CLI Reference](../cli-reference.md).

## Next

- [Getting Started](../getting-started.md) — install Flint and generate
  your first project
- [Agent Skills](../agent-skills.md) — how `.agents/skills/` is selected
  and what's in it
