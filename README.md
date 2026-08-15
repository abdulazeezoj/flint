# flint

[![CI](https://github.com/abdulazeezoj/flint/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulazeezoj/flint/actions/workflows/ci.yml)
[![Docs](https://github.com/abdulazeezoj/flint/actions/workflows/docs.yml/badge.svg)](https://abdulazeezoj.github.io/flint/)
[![PyPI](https://img.shields.io/pypi/v/flint-kit)](https://pypi.org/project/flint-kit/)

Strike a spark, get a running project. Instant scaffolding for popular
unopinionated Python web frameworks (FastAPI, Flask, and friends). One
command, a short interactive wizard, and you have a running project.
No hand-written boilerplate. Pick a richer template and the same
wizard wires up a real database, migrations, and a background worker
too.

```
uvx --from flint-kit flint
```

```
? What is your project named? my-api
? Which framework? FastAPI
? Which template? REST API
? Database? PostgreSQL
? ORM? SQLModel
? Add Alembic migrations? Yes
? Background worker? Taskiq
Using uv to manage dependencies.
? Add a Dockerfile? No
? Initialize a git repository? Yes
? Install dependencies with uv now? Yes

Options: database=postgres, orm=sqlmodel, migrations=True, worker=taskiq, broker=redis, redis=True
Creating my-api/ from fastapi/rest-api...
  ✔ ...
✔ Initialized git repository
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run alembic upgrade head
  uv run fastapi dev src/my_api/main.py
  uv run taskiq worker my_api.worker:broker --app-dir src   # separate process
```

**📖 Full documentation: [abdulazeezoj.github.io/flint](https://abdulazeezoj.github.io/flint/)**.
Getting started, a full CLI reference, one page per template (options,
generated layout, gotchas), the `.agents/skills/` catalog, remembered
preferences, and how to contribute.

## Install

Persistent `flint` on PATH:

```
uv tool install flint-kit
```

Or run it ephemerally, no install:

```
uvx --from flint-kit flint
```

## Usage

```
flint                                     # interactive wizard
flint new my-api                           # interactive, name pre-filled
flint new my-api \
  --framework fastapi --template rest-api \
  -o database=sqlite -o orm=sqlmodel \
  --docker --git --install --yes            # fully non-interactive, for scripts/CI
flint list-templates                       # what's available, without generating anything
flint --version
flint --help
```

Every prompt has a matching flag, and Flint remembers your last
choices in `~/.flint/last.json` as the new default next time. See the
[CLI Reference](https://abdulazeezoj.github.io/flint/cli-reference/)
and [Remembered Preferences](https://abdulazeezoj.github.io/flint/preferences/)
docs for the full details.

Driving flint from an AI coding agent? [`.agents/skills/flint/`](.agents/skills/flint/)
is a portable agent skill that teaches an agent how to invoke the CLI
to scaffold a project. It's symlinked at `.claude/skills/flint/` for
Claude Code's own discovery path. Separate from the `.agents/skills/`
catalog described below, which covers using the *generated* project's
own stack.

## What flint ships

A project is always generated from a `<framework>/<template>` pair:
**FastAPI** and **Flask**, each with a **Hello World** starter, a fuller
**REST API** template offering real head-start choices (database, ORM,
migrations, a background worker, Redis), and a **Full-Stack** template
with the same choices rendered server-side with Jinja2 and HTMX instead
of JSON (optionally styled with Tailwind CSS). Every generated project
also gets `.agents/skills/`: deeper, library-specific reference
material for exactly the stack it uses. See the
[Templates](https://abdulazeezoj.github.io/flint/project-templates/)
and [Agent Skills](https://abdulazeezoj.github.io/flint/agent-skills/)
docs for what each one actually generates.

## Project structure

Every generated project follows the same opinionated layout, borrowed
from Next.js: fixed entrypoints, one file per resource, shared
infrastructure grouped under `core/`. Here's `fastapi/rest-api` with a
database, migrations, and a background worker:

```
my-api/
  src/my_api/
    main.py              FastAPI entrypoint: app, lifespan, mounted routers
    worker.py            worker entrypoint (only if a worker is chosen)
    routes/               one module per HTTP resource
      items.py
    tasks/                 one module per background job (only if a worker is chosen)
      example.py
    core/                   shared infrastructure
      config.py               settings (pydantic-settings)
      db.py                    async engine/session (only if a database is chosen)
      redis.py                 Redis client (only if redis resolves true)
    schemas.py             Pydantic request/response models
    models.py               ORM models (only if a database is chosen)
  tests/
  alembic/                 migrations (only if migrations is on)
  .agents/skills/          library-specific reference material for AI agents
  AGENTS.md
  Dockerfile               (only if --docker)
```

`hello-world` is the same shape, minus the extras. `full-stack` swaps
`routes/` + `schemas.py` for `routes/` returning HTML fragments plus
`templates/` + `static/` (Jinja2 + HTMX, optionally Tailwind CSS). See
[Templates](https://abdulazeezoj.github.io/flint/project-templates/)
for the exact generated layout of every framework and template
combination.

## Contributing

```
uv sync
uv run pytest       # also runs coverage; the suite fails under 100%
uv run flint --help
```

Adding a framework, template, or skill is a content-only change. No
code edits needed. See the
[Contributing](https://abdulazeezoj.github.io/flint/contributing/)
docs for the full local-setup, template/skill-authoring, and release
process, or [`CHANGELOG.md`](CHANGELOG.md) for release history.
