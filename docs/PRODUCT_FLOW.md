# Flint — Product Flow

**Status:** Draft for v0
**Last updated:** 2026-08-12 (v0.4: opinionated generated-project layout)

Companion to `PRODUCT_SPEC.md`. Describes exactly what happens when a user
runs Flint, in both interactive and non-interactive modes. See
`PRODUCT_SPEC.md` §3 for the framework/template/option distinction this
flow depends on.

## 1. Entry points

| Command | Behavior |
|---|---|
| `uvx flint` / `flint` | No args → full interactive wizard, generates into a new directory named after the answered project name, in the current working directory. |
| `flint new [NAME]` | Same wizard; `NAME` pre-fills the project-name prompt (or skips it if `--yes`). |
| `flint new NAME --framework fastapi --template restapi -o database=postgres -o orm=sqlmodel --docker --git --install --yes` | Fully non-interactive; no prompts, generates immediately. `--option`/`-o key=value` is repeatable, one per template-declared option. |
| `flint --version` | Prints version, exits. |
| `flint --help` / `flint new --help` | Prints usage, exits. |

`flint` with no subcommand is an alias for `flint new` (matches the
`create-next-app` muscle memory of "just run the command").

## 2. Interactive wizard — step by step

The wizard is a short, linear sequence. Each step shows a default in
brackets; pressing Enter accepts it. Arrow-key select lists are used for
choices with more than 2 options; y/n confirms use inline `(Y/n)` prompts.

```
1. Project name
   ? What is your project named? › my-api
   - Free text input, default: "my-app" if invoked with no NAME arg.
   - Validated live: must produce a valid Python package name once
     slugified (see §3). Re-prompts on invalid input with a one-line
     reason, never a stack trace.

2. Target directory check
   - Derived as ./<slug> relative to cwd. Not an interactive prompt.
   - If it exists and is non-empty → hard stop with a clear error
     ("Directory 'my-api' already exists and is not empty.") and a
     pointer to --force. No silent overwrite, ever.

3. Framework
   ? Which framework? › (Use arrow keys)
     ❯ FastAPI
       Flask (coming soon)
       Django (coming soon)
   - v0 ships FastAPI only. Other entries are shown but disabled/greyed
     to signal the roadmap (create-next-app does the same for future
     options) — selecting one prints "coming soon" and re-prompts.

4. Template (scoped to the chosen framework)
   ? Which template? › (Use arrow keys)
     ❯ Hello World
       REST API
   - Same disabled-entry pattern as the framework step would apply to
     any future disabled template — both currently ship enabled. Each
     framework has its own template list — picking a different
     framework in step 3 changes what shows up here.

5. Template options — declared by the chosen template, asked in the
   order it declares them; entirely different per template (Flint's own
   code has no built-in knowledge of these — see PRODUCT_ARCH.md §4).
   Some options depend on an earlier one and are silently skipped
   (resolved to a documented value) rather than asked when their
   dependency isn't satisfied — e.g. restapi's ORM prompt never appears
   if "no database" was chosen.

   For restapi:
   ? Database? › None / SQLite / PostgreSQL           (default: SQLite)
   ? ORM? › SQLModel / SQLAlchemy                       (skipped if no DB; default: SQLModel)
   ? Add Alembic migrations? (Y/n)                      (skipped if no DB; default: yes)
   ? Background worker? › None / Taskiq / Celery         (default: None)
   ? Add Redis (caching)? (y/N)                          (skipped — forced yes — if a worker was chosen; default: no)

   For hello-world:
   ? Add configuration (pydantic-settings)? (y/N)        (default: no)

6. Package manager
   ? Package manager? › uv (only option in v0, shown for consistency
     with future choices; not actually prompted in v0 — auto-selected
     and simply echoed: "Using uv to manage dependencies.")

7. Add a Dockerfile?
   ? Add a Dockerfile? (y/N) ›
   - Default **no** (unlike git/install below, this one opts in rather
     than out — most quick scaffolds don't need a container). If yes,
     and the chosen framework/template doesn't have Docker support yet,
     Flint warns and continues without one rather than failing.

8. Initialize a git repository?
   ? Initialize a git repository? (Y/n) ›
   - Default yes. If yes: `git init` + initial commit after files are
     written. If git is not installed/available, warn and continue
     (non-fatal).

9. Install dependencies now?
   ? Install dependencies with uv now? (Y/n) ›
   - Default yes. If yes: runs `uv sync` in the generated directory
     after writing files, with a spinner. If uv is unavailable or the
     install fails, the project is still left in a valid, runnable state
     (user can `uv sync` manually) — this never rolls back generation.

10. Generation
   - Renders the template to disk (see PRODUCT_ARCH.md for the
     mechanism). Shows a live-ish summary of files created.

11. Summary / next steps
   Options: database=sqlite, orm=sqlmodel, migrations=True, worker=none, redis=False
   Creating my-api/ from fastapi/restapi...
     ✔ ...
   ✔ Initialized git repository
   ✔ Installed dependencies (uv sync)

   Next steps:
     cd my-api
     uv run fastapi dev src/my_api/main.py

   Then open http://127.0.0.1:8000 — plus a migrate command, a worker
   command, and/or Docker commands, whichever apply to what was chosen.
```

## 3. Validation rules (project name → package name)

- Input is slugified for the directory: lowercased, spaces/underscores →
  `-`, strip anything outside `[a-z0-9-]`.
- The importable package name is derived separately: same process but
  joined with `_` (valid Python identifier), and prefixed with `_` if it
  would otherwise start with a digit.
- Reserved/invalid results (empty string, Python keyword, stdlib module
  shadow like `test`/`types`) are rejected with a specific message and
  re-prompt — never silently mutated into something the user didn't see.

## 4. Non-interactive mode

Triggered by either passing `--yes`, or by Flint detecting stdin is not a
TTY (e.g. running in CI). In that mode:

- Every prompt above becomes: use the flag/`--option` if given, else use
  the documented default, **never block on input**.
- Framework defaults to the first enabled framework; template defaults to
  the first enabled template within it; each template option defaults to
  its own declared default (or its `skip_value`, if its dependency isn't
  satisfied — same rule as interactive mode, just without the prompt).
- If a required decision has no safe default and no flag was given (there
  are none in v0 — every prompt has a default), Flint would exit `1` with
  an actionable error rather than hang. This rule exists for future
  prompts that may not have a safe default.
- Output is the same summary block, without spinners/animations (falls
  back to plain log lines when not a TTY).

## 5. Error flows

| Situation | Behavior |
|---|---|
| Target directory exists, non-empty, no `--force` | Exit 1, no files written. |
| Target directory exists, non-empty, `--force` | Overwrite, but only after an explicit interactive confirmation (or the flag itself counts as confirmation in `--yes`/non-interactive mode). |
| Invalid project name | Re-prompt (interactive) or exit 1 with reason (non-interactive). |
| Unknown/disabled `--framework` or `--template` | Exit 1 with reason (non-interactive); interactive select lists disable the entry so it can't be chosen. |
| `--option key=value` with an unknown key for the chosen template | Exit 1 listing the unknown key(s). |
| `--option` with a value not among a select option's choices, or not a valid boolean for a confirm option | Exit 1 with the specific reason and (for select) the valid choices. |
| `--option` missing the `=` (e.g. `--option database`) | Exit 1: "must be in key=value form." |
| `--docker` requested but the chosen template has no Docker support | Warn, skip the Dockerfile, still exit 0 — never fails generation over an optional extra. |
| `uv` not found, install requested | Warn, skip install step, still exit 0 — project is valid, just not installed. |
| `git` not found, git-init requested | Warn, skip git step, still exit 0. |
| Unexpected exception during generation | Roll back (delete partially-written target directory) and exit 2 with the error. Generation is all-or-nothing from the user's perspective. |

## 6. Post-generation experience

The generated project's own README (written by the template, not typed
by the user) always contains, at minimum:
1. The exact run command.
2. The exact test command.
3. A one-line description of the project layout.
4. Whatever else the chosen options add: migration commands, worker
   commands, Docker commands — each only if that option was chosen.

The project also always includes `AGENTS.md` — context for AI coding
agents working in the repo (run/test commands, layout, conventions) —
regardless of which options were chosen. This is the same information
printed in the CLI summary, so the user never has to re-discover it
later.

## 7. Example transcript (interactive, restapi with a real stack)

```
$ uvx flint
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

Options: database=postgres, orm=sqlmodel, migrations=True, worker=taskiq, redis=True
Creating my-api/ from fastapi/restapi...
  ✔ .env
  ✔ .gitignore
  ✔ AGENTS.md
  ✔ README.md
  ✔ alembic.ini
  ✔ alembic/env.py
  ✔ alembic/script.py.mako
  ✔ alembic/versions/.gitkeep
  ✔ pyproject.toml
  ✔ src/my_api/__init__.py
  ✔ src/my_api/core/__init__.py
  ✔ src/my_api/core/config.py
  ✔ src/my_api/core/db.py
  ✔ src/my_api/core/redis.py
  ✔ src/my_api/main.py
  ✔ src/my_api/models.py
  ✔ src/my_api/routes/__init__.py
  ✔ src/my_api/routes/items.py
  ✔ src/my_api/schemas.py
  ✔ src/my_api/tasks/__init__.py
  ✔ src/my_api/tasks/example.py
  ✔ src/my_api/worker.py
  ✔ tests/conftest.py
  ✔ tests/test_main.py
✔ Initialized git repository
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run alembic upgrade head
  uv run fastapi dev src/my_api/main.py
  uv run taskiq worker my_api.worker:broker --app-dir src   # separate process

Then open http://127.0.0.1:8000
```

## 8. Example transcript (non-interactive / CI, hello-world)

```
$ flint new my-api --framework fastapi --template hello-world --git --install --yes
Options: config=False
Creating my-api/ from fastapi/hello-world...
  ✔ AGENTS.md
  ✔ README.md
  ✔ .gitignore
  ✔ pyproject.toml
  ✔ src/my_api/__init__.py
  ✔ src/my_api/main.py
  ✔ tests/test_main.py
✔ Initialized git repository
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api
```
