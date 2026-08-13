# flint

[![CI](https://github.com/abdulazeezoj/flint/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulazeezoj/flint/actions/workflows/ci.yml)
[![Docs](https://github.com/abdulazeezoj/flint/actions/workflows/docs.yml/badge.svg)](https://abdulazeezoj.github.io/flint/)
[![PyPI](https://img.shields.io/pypi/v/flint-kit)](https://pypi.org/project/flint-kit/)

`create-next-app`, for Python. One command, a short interactive wizard,
and you have a running project — no hand-written boilerplate. Pick a
richer template and the same wizard wires up a real database,
migrations, and a background worker too.

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

**📖 Full documentation: [abdulazeezoj.github.io/flint](https://abdulazeezoj.github.io/flint/)**
— getting started, a full CLI reference, one page per template
(options, generated layout, gotchas), the `.agents/skills/` catalog,
remembered preferences, and how to contribute.

## Install

```
uv tool install flint-kit   # persistent `flint` on PATH
# or run it ephemerally, no install:
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

## What flint ships

A project is always generated from a `<framework>/<template>` pair —
**FastAPI** and **Flask**, each with a **Hello World** and a fuller
**REST API** template offering real head-start choices (database, ORM,
migrations, a background worker, Redis). Every generated project also
gets `.agents/skills/` — deeper, library-specific reference material
for exactly the stack it uses. See the
[Templates](https://abdulazeezoj.github.io/flint/project-templates/)
and [Agent Skills](https://abdulazeezoj.github.io/flint/agent-skills/)
docs for what each one actually generates.

## Contributing

```
uv sync
uv run pytest       # also runs coverage — the suite fails under 100%
uv run flint --help
```

Adding a framework, template, or skill is a content-only change — no
code edits needed. See the
[Contributing](https://abdulazeezoj.github.io/flint/contributing/)
docs for the full local-setup, template/skill-authoring, and release
process, or [`CHANGELOG.md`](CHANGELOG.md) for release history.
