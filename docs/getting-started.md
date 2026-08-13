# Getting Started

## Install

```bash
uv tool install flint-cli   # persistent `flint` on PATH
```

Or run it without installing anything:

```bash
uvx flint
```

Flint needs [uv](https://docs.astral.sh/uv/) — every generated project is
`uv`-managed (`pyproject.toml` + `uv.lock`), and Flint uses it for the
optional "install dependencies now" step. If you don't have `uv` yet,
[install it first](https://docs.astral.sh/uv/getting-started/installation/).

## Your first project, interactively

Run `flint` (or `uvx flint`) with no arguments and answer the prompts:

```text
$ flint
? What is your project named? my-api
? Which framework? › (Use arrow keys)
  ❯ FastAPI
    Flask
? Which template? › (Use arrow keys)
  ❯ Hello World
    REST API
Using uv to manage dependencies.
? Add a Dockerfile? (y/N)
? Initialize a git repository? (Y/n)
? Install dependencies with uv now? (Y/n)
```

Every project is generated from a **framework** (the underlying library —
FastAPI or Flask) and a **template** (a project shape built on it — `hello-world`
or `rest-api`). Pick `rest-api` and the wizard keeps going: database, ORM,
migrations, background worker — each template declares its own follow-up
questions, so what you're asked depends entirely on what you picked. See
[Templates](project-templates/index.md) for exactly what each one asks and generates.

When it's done:

```text
Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run fastapi dev src/my_api/main.py

Then open http://127.0.0.1:8000
```

The exact next-step commands change based on what you chose — a migration
command if you added Alembic, a worker command if you added Taskiq/Celery,
Docker commands if you passed `--docker`. Nothing is left for you to guess.

## Skip the prompts

Every prompt has a matching flag, so the same generation is fully
scriptable:

```bash
flint new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=redis \
  --docker --git --install --yes
```

`--yes` accepts the default for anything you didn't pass a flag for — no
prompts, safe for CI. See [CLI Reference](cli-reference.md) for every flag
and what `-o key=value` accepts per template.

## It remembers your choices

After a successful run, Flint saves the framework/template you picked and
every resolved option to `~/.flint/last.json`, and uses them as the new
default next time — both for what the wizard preselects and what a flagless
`--yes` run falls back to. An explicit flag or `-o` always overrides a
remembered value. Pass `--no-remember` to opt a single run out of both
reading and writing that file.

## What you get, every time

Regardless of which framework, template, or options you chose, every
generated project includes:

- A `uv`-managed, `src/`-layout package with a passing `pytest` test
- A `README.md` with the exact run/test commands for what was actually generated
- An `AGENTS.md` with layout and conventions, for AI coding agents working in the project
- A `.agents/skills/` catalog — deeper reference material for exactly the
  libraries in use (see [Agent Skills](agent-skills.md))
- A `.gitignore` — and, if you didn't pass `--no-git`, an initialized git repo with an initial commit

No manual edits required to run it.

## Next

- [CLI Reference](cli-reference.md) — every flag, exit code, and what `--option` accepts
- [Templates](project-templates/index.md) — what each framework/template pair actually generates
