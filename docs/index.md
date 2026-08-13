# Flint

`create-next-app`, for Python. One command, a short interactive wizard, and
you have a running project — no hand-written boilerplate. Pick a richer
template and the same wizard wires up a real database, migrations, and a
background worker too.

```bash
uvx --from flint-kit flint
```

```text
? What is your project named? my-api
? Which framework? FastAPI
? Which template? REST API
? Database? PostgreSQL
? ORM? SQLModel
? Add Alembic migrations? Yes
? Background worker? Taskiq
? Message broker? RabbitMQ
? Add Redis (caching)? No
Using uv to manage dependencies.
? Add a Dockerfile? No
? Initialize a git repository? Yes
? Install dependencies with uv now? Yes

Options: database=postgres, orm=sqlmodel, migrations=True, worker=taskiq, broker=rabbitmq, redis=False
Creating my-api/ from fastapi/rest-api...
  ✔ ...

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run alembic upgrade head
  uv run fastapi dev src/my_api/main.py
  uv run taskiq worker my_api.worker:broker --app-dir src   # separate process

Then open http://127.0.0.1:8000
```

## Why Flint

Strike it and it throws a spark — that's the whole idea: one command,
and a real project catches. Every new FastAPI or Flask project starts
with the same repetitive setup —
`pyproject.toml`, a `src/` layout, a first endpoint, a test, a `.gitignore`,
a README nobody gets around to writing — and, past the toy stage, the same
recurring decisions: which database, which ORM, whether to bother with
migrations yet, whether background work needs a queue. Flint answers the
short list of decisions that actually matter and generates a project that's
already wired for them, instead of a blank slate you have to wire yourself.

- **Zero to running in under a minute.** No install, no config file — run
  `uvx --from flint-kit flint` and you have a project you can `uv run` immediately.
- **Real head-start choices, not just a skeleton.** The `rest-api` template
  offers a database (SQLite/PostgreSQL), an ORM, Alembic migrations, a
  background worker (Taskiq/Celery), and Redis — pick what you need, skip
  what you don't.
- **Fully scriptable.** Every interactive prompt has a matching flag, so
  `flint new` works identically in CI with zero prompts.
- **Two frameworks today, more later.** FastAPI and Flask ship with
  matching template shapes — same options, same conventions, same
  generated layout philosophy — so switching between them isn't a
  relearn.
- **Agent-ready by default.** Every generated project ships an `AGENTS.md`
  plus a `.agents/skills/` catalog scoped to exactly the stack it generated
  — see [Agent Skills](agent-skills.md).

## Where to go next

<div class="grid cards" markdown>

- **[Getting Started](getting-started.md)**
  Install Flint and generate your first project, interactively or
  non-interactively.

- **[CLI Reference](cli-reference.md)**
  Every command, flag, and exit code.

- **[Templates](project-templates/index.md)**
  What `hello-world` and `rest-api` actually generate, for each framework.

- **[Agent Skills](agent-skills.md)**
  How `.agents/skills/` is selected and what's in it.

</div>

## Install

```bash
uv tool install flint-kit   # persistent `flint` on PATH
# or run it ephemerally, no install:
uvx --from flint-kit flint
```

Flint is a CLI, not a library: installing it puts a `flint` command on
your `PATH`. The PyPI distribution is named `flint-kit` rather than
plain `flint` — the bare name was already taken by an unrelated
package — but the command itself, everything in these docs, and every
generated project's attribution all just say `flint`.
