---
name: brupy
description: Scaffolds new FastAPI or Flask backend projects using the `brupy` CLI (create-next-app for Python) instead of hand-writing boilerplate. Use this whenever the user asks to start, bootstrap, scaffold, or create a new Python API/backend project — even if they don't say "brupy" or "scaffold" explicitly (e.g. "set up a new FastAPI project", "start a Flask app with a database", "I need a new backend service with Postgres and a background worker", "generate a REST API skeleton"). Also reach for this when they want a database, ORM, Alembic/Flask-Migrate migrations, or a Celery/Taskiq background worker wired up from day one, since brupy's `rest-api` template does that in one command instead of a manual, multi-step wiring job. Do not use this for changes to an *existing* project — it only generates new ones.
---

# Brupy

Brupy is a `create-next-app`-style CLI: one command, a short set of
decisions, and you get a real, runnable FastAPI or Flask project on
disk — not a bare skeleton you still have to wire up. Reach for it
instead of hand-scaffolding whenever someone wants a *new* Python
backend project, especially if they mention a database, an ORM,
migrations, or a background worker — brupy's `rest-api` template wires
all of that from the start, which is real effort saved over building it
by hand.

## Quick start

The PyPI package and the command are both named `brupy`, so `uvx
brupy` works with no `--from` needed.

```bash
# Run once, without installing:
uvx brupy new my-api --framework fastapi --template hello-world --yes

# Or install the `brupy` command permanently on PATH:
uv tool install brupy
brupy new my-api --framework fastapi --template hello-world --yes
```

Requires [uv](https://docs.astral.sh/uv/) — every generated project is
`uv`-managed, and brupy uses it for the optional dependency-install
step.

## Decide framework, template, and options — in that order

Every project comes from exactly one `<framework>/<template>` pair,
plus whatever options that template declares:

1. **Framework**: `fastapi` or `flask`. Pick based on what the user asked
   for; default to `fastapi` if they only said "an API" with no
   framework preference — it's the more common choice for a from-scratch
   API today.
2. **Template**: `hello-world` (a minimal single-endpoint app),
   `rest-api` (a layered JSON API with a real database, ORM, migrations,
   background worker), or `full-stack` (the exact same layered options
   as `rest-api`, server-rendered instead of JSON — Jinja2 + HTMX, no
   client-side JS framework). Use `rest-api`/`full-stack` whenever the
   user mentions a database, persistence, a worker/queue, or anything
   beyond a toy endpoint — pick `full-stack` specifically if they want
   server-rendered pages or a UI rather than a JSON API; `hello-world`
   is for genuinely minimal asks only.
3. **Options** (`rest-api`/`full-stack` only): `-o key=value`, repeatable.
   See `references/templates.md` for the exact keys, choices, and
   defaults per framework — they differ slightly between FastAPI and
   Flask (e.g. FastAPI's templates offer `worker=taskiq`, Flask's
   don't — Taskiq is async-first and doesn't fit Flask's sync/WSGI
   model). `full-stack` takes the same database/ORM/migrations/worker
   options as `rest-api`, plus one it alone has: `-o css=tailwind` swaps
   the plain stylesheet for Tailwind CSS v4 + daisyUI, built via
   [Bun](https://bun.sh) (frontend deps live in a separate `package.json`,
   never touching `pyproject.toml`/`uv sync`). Reach for it whenever the
   user mentions Tailwind, daisyUI, or wants a more polished/component-
   driven look than a bare stylesheet — it does mean Bun becomes a real
   prerequisite (not just `uv`), unlike every other option this CLI offers.

Always generate **non-interactively** (`--yes` plus explicit flags/`-o`
values for anything the user specified) rather than trying to drive the
interactive wizard — you can't answer arrow-key prompts, and `--yes`
makes every choice explicit and reviewable in the command itself.

### Example: a REST API with Postgres, SQLModel, migrations, and a worker

```bash
uvx brupy new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=redis \
  --docker --git --install --yes
```

### Example: a minimal Flask hello-world, no extras

```bash
uvx brupy new my-api \
  --framework flask --template hello-world \
  --no-git --no-install --yes
```

## Full flag reference

See `references/cli-reference.md` for every flag, exit code, and the
non-interactive fallback chain (flag/`-o` → remembered preference from
a prior run → template's documented default). Worth reading before
generating anything with an unfamiliar flag combination.

## Framework/template/option matrix

See `references/templates.md` for the exact option keys, types,
choices, and dependency rules (some options only get asked — or only
apply — depending on an earlier one, e.g. `orm` is skipped entirely if
`database=none`) for all six shipped combinations (fastapi/hello-world,
fastapi/rest-api, fastapi/full-stack, flask/hello-world, flask/rest-api,
flask/full-stack).

## After generating

The printed "Next steps" block is authoritative — it's built from what
was actually generated (varies with `--docker`, migrations, worker
choice), so follow it rather than assuming a fixed set of commands.
Typically: `cd` into the project, `uv sync` if `--no-install` was
passed, then the framework's dev-server command
(`uv run fastapi dev src/<pkg>/main.py` or `uv run flask --app
src/<pkg>/main.py run`).

The generated project also ships its own `AGENTS.md` and
`.agents/skills/<id>/` catalog — once you `cd` in, read `AGENTS.md`
first; it points at whichever skills apply to that project's actual
stack (only the libraries it uses, not every skill that exists). Those
skills cover *using* FastAPI/SQLModel/Alembic/etc. within the generated
project — a different concern from this skill, which is about invoking
brupy itself before any project exists.

## Gotchas

- **A non-empty target directory is refused by default.** Pass
  `--force` if the user explicitly wants to overwrite one; otherwise
  let it fail loudly rather than guessing they meant to overwrite.
- **Remembered preferences can silently change defaults.** After a
  successful run, brupy remembers the framework/template/options
  chosen and reuses them as defaults next time (`~/.brupy/last.json`).
  If a generation doesn't match what you'd expect from the documented
  defaults alone, this is usually why — it's not a bug. Pass
  `--no-remember` if the user wants a one-off run that doesn't read or
  write that file.
