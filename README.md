# spindle

[![CI](https://github.com/abdulazeezoj/spindle/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulazeezoj/spindle/actions/workflows/ci.yml)
[![Docs](https://github.com/abdulazeezoj/spindle/actions/workflows/docs.yml/badge.svg)](https://abdulazeezoj.github.io/spindle/)
[![PyPI](https://img.shields.io/pypi/v/spindle)](https://pypi.org/project/spindle/)

`create-next-app`, for Python. One command, a short interactive wizard,
and you have a running project — no hand-written boilerplate. Pick a
richer template and the same wizard wires up a real database,
migrations, and a background worker too.

```
uvx spindle
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

**📖 Full documentation: [abdulazeezoj.github.io/spindle](https://abdulazeezoj.github.io/spindle/)**
— getting started, a full CLI reference, one page per template
(options, generated layout, gotchas), the `.agents/skills/` catalog,
remembered preferences, and how to contribute.

## Install

```
uv tool install spindle   # persistent `spindle` on PATH
# or run it ephemerally, no install:
uvx spindle
```

## Usage

```
spindle                                     # interactive wizard
spindle new my-api                           # interactive, name pre-filled
spindle new my-api \
  --framework fastapi --template rest-api \
  -o database=sqlite -o orm=sqlmodel \
  --docker --git --install --yes            # fully non-interactive, for scripts/CI
spindle list-templates                       # what's available, without generating anything
spindle --version
spindle --help
```

Every prompt has a matching flag, and Spindle remembers your last
choices in `~/.spindle/last.json` as the new default next time. See the
[CLI Reference](https://abdulazeezoj.github.io/spindle/cli-reference/)
and [Remembered Preferences](https://abdulazeezoj.github.io/spindle/preferences/)
docs for the full details.

## What spindle ships

A project is always generated from a `<framework>/<template>` pair —
**FastAPI** and **Flask**, each with a **Hello World** and a fuller
**REST API** template offering real head-start choices (database, ORM,
migrations, a background worker, Redis). Every generated project also
gets `.agents/skills/` — deeper, library-specific reference material
for exactly the stack it uses. See the
[Templates](https://abdulazeezoj.github.io/spindle/project-templates/)
and [Agent Skills](https://abdulazeezoj.github.io/spindle/agent-skills/)
docs for what each one actually generates.

## Contributing

```
uv sync
uv run pytest       # also runs coverage — the suite fails under 100%
uv run spindle --help
```

Adding a framework, template, or skill is a content-only change — no
code edits needed. See the
[Contributing](https://abdulazeezoj.github.io/spindle/contributing/)
docs for the full local-setup, template/skill-authoring, and release
process, or [`CHANGELOG.md`](CHANGELOG.md) for release history.
