# brupy

[![CI](https://github.com/abdulazeezoj/brupy/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulazeezoj/brupy/actions/workflows/ci.yml)
[![Docs](https://github.com/abdulazeezoj/brupy/actions/workflows/docs.yml/badge.svg)](https://abdulazeezoj.github.io/brupy/)
[![PyPI](https://img.shields.io/pypi/v/brupy)](https://pypi.org/project/brupy/)

Strike a spark, get a running project. Instant scaffolding for popular
unopinionated Python web frameworks (FastAPI, Flask, and friends). One
command, a short interactive wizard, and you have a running project.
No hand-written boilerplate. Pick a richer template and the same
wizard wires up a real database, migrations, and a background worker
too.

```
uvx brupy
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

**📖 Full documentation: [abdulazeezoj.github.io/brupy](https://abdulazeezoj.github.io/brupy/)**.
Getting started, a full CLI reference, one page per template (options,
generated layout, gotchas), the `.agents/skills/` catalog, remembered
preferences, and how to contribute.

## Install

Persistent `brupy` on PATH:

```
uv tool install brupy
```

Or run it ephemerally, no install:

```
uvx brupy
```

## Usage

```
brupy                                     # interactive wizard
brupy new my-api                           # interactive, name pre-filled
brupy new my-api \
  --framework fastapi --template rest-api \
  -o database=sqlite -o orm=sqlmodel \
  --docker --git --install --yes            # fully non-interactive, for scripts/CI
brupy list-templates                       # what's available, without generating anything
brupy install-skill                        # add the brupy skill to an existing project
brupy --version
brupy --help
```

Every prompt has a matching flag, and Brupy remembers your last
choices in `~/.brupy/last.json` as the new default next time. See the
[CLI Reference](https://abdulazeezoj.github.io/brupy/cli-reference/)
and [Remembered Preferences](https://abdulazeezoj.github.io/brupy/preferences/)
docs for the full details.

Driving brupy from an AI coding agent? [`.agents/skills/brupy/`](.agents/skills/brupy/)
is a portable agent skill that teaches an agent how to invoke the CLI
to scaffold a project. It's symlinked at `.claude/skills/brupy/` for
Claude Code's own discovery path. Separate from the `.agents/skills/`
catalog described below, which covers using the *generated* project's
own stack. Every generated project gets it automatically; run `brupy
install-skill` (`--scope project`, the default, or `--scope user` for
every project at once) to add it to a repo that wasn't scaffolded with
brupy in the first place.

## What brupy ships

A project is always generated from a `<framework>/<template>` pair:
**FastAPI** and **Flask**, each with a **Hello World** starter, a fuller
**REST API** template offering real head-start choices (database, ORM,
migrations, a background worker, Redis), and a **Full-Stack** template
with the same choices rendered server-side with Jinja2 and HTMX instead
of JSON (optionally styled with Tailwind CSS). Every generated project
also gets `.agents/skills/`: deeper, library-specific reference
material for exactly the stack it uses. See the
[Templates](https://abdulazeezoj.github.io/brupy/project-templates/)
and [Agent Skills](https://abdulazeezoj.github.io/brupy/agent-skills/)
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
  .claude/skills/          same skills, symlinked for Claude Code's own discovery path
  AGENTS.md
  CLAUDE.md                one line, @AGENTS.md — Claude Code loads it automatically
  Dockerfile               (only if --docker)
```

`hello-world` is the same shape, minus the extras. `full-stack` swaps
`routes/` + `schemas.py` for `routes/` returning HTML fragments plus
`templates/` + `static/` (Jinja2 + HTMX, optionally Tailwind CSS). See
[Templates](https://abdulazeezoj.github.io/brupy/project-templates/)
for the exact generated layout of every framework and template
combination.

## Contributing

```
uv sync
uv run pytest       # also runs coverage; the suite fails under 100%
uv run brupy --help
```

Adding a framework, template, or skill is a content-only change. No
code edits needed. See the
[Contributing](https://abdulazeezoj.github.io/brupy/contributing/)
docs for the full local-setup, template/skill-authoring, and release
process, or [`CHANGELOG.md`](CHANGELOG.md) for release history.
