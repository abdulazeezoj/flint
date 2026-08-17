# Brupy — Product Flow

**Status:** Draft for v0
**Last updated:** 2026-08-13 (v0.10: interactive `--force` confirmation, `brupy list-templates`)

Companion to `PRODUCT_SPEC.md`. Describes exactly what happens when a user
runs Brupy, in both interactive and non-interactive modes. See
`PRODUCT_SPEC.md` §3 for the framework/template/option distinction this
flow depends on.

## 1. Entry points

| Command | Behavior |
|---|---|
| `uvx brupy` / `brupy` | No args → full interactive wizard, generates into a new directory named after the answered project name, in the current working directory. |
| `brupy new [NAME]` | Same wizard; `NAME` pre-fills the project-name prompt (or skips it if `--yes`). |
| `brupy new NAME --framework fastapi --template rest-api -o database=postgres -o orm=sqlmodel --docker --git --install --yes` | Fully non-interactive; no prompts, generates immediately. `--option`/`-o key=value` is repeatable, one per template-declared option. |
| `brupy new NAME --no-remember ...` | Same as above, but neither reads nor writes `~/.brupy/last.json` for this run (§6). |
| `brupy list-templates` | Prints a table of every framework/template pair (label, description, `--docker` support), including disabled/"coming soon" entries. Generates nothing — pure introspection. |
| `brupy --version` | Prints version, exits. |
| `brupy --help` / `brupy new --help` | Prints usage, exits. |

`brupy` with no subcommand is an alias for `brupy new` (matches the
`create-next-app` muscle memory of "just run the command").

## 2. Interactive wizard — step by step

The wizard is a short, linear sequence. Each step shows a default in
brackets; pressing Enter accepts it. Arrow-key select lists are used for
choices with more than 2 options; y/n confirms use inline `(Y/n)` prompts.

Where noted below, a step's default isn't always the template's own
hardcoded default — if `~/.brupy/last.json` remembers a value for that
step (from a previous successful run) and it's still valid, that
remembered value is preselected instead. See §6 for the full mechanism.
This never changes what gets *asked*, only what's pre-highlighted/
falls back to.

```
1. Project name
   ? What is your project named? › my-api
   - Free text input, default: "my-app" if invoked with no NAME arg.
   - Validated live: must produce a valid Python package name once
     slugified (see §3). Re-prompts on invalid input with a one-line
     reason, never a stack trace.

2. Target directory check
   - Derived as ./<slug> relative to cwd.
   - If it exists and is non-empty and --force wasn't passed:
     ? Directory 'my-api' already exists and is not empty. Overwrite? › (y/N)
     Interactive only — confirming proceeds exactly as --force would;
     declining hard-stops with a clear error ("Directory 'my-api'
     already exists and is not empty. Use --force to generate into it
     anyway.") and no files written. Non-interactive (--yes/piped
     stdin): no prompt, straight to the same hard error unless --force
     was already passed. No silent overwrite, ever.

3. Framework
   ? Which framework? › (Use arrow keys)
     ❯ FastAPI
       Flask
   - v0.8 ships both FastAPI and Flask, fully enabled. Any future
     framework ships the same way FastAPI/Flask did while unfinished:
     listed but disabled/greyed (create-next-app does the same for
     future options) — selecting a disabled entry prints "coming soon"
     and re-prompts.
   - Preselected entry: the remembered last framework (§6), if it's
     still enabled; otherwise the first enabled entry.

4. Template (scoped to the chosen framework)
   ? Which template? › (Use arrow keys)
     ❯ Hello World
       REST API
   - Same disabled-entry pattern as the framework step would apply to
     any future disabled template — both currently ship enabled. Each
     framework has its own template list — picking a different
     framework in step 3 changes what shows up here.
   - Preselected entry: the remembered last template *for the chosen
     framework* (§6), if still enabled; otherwise the first enabled
     entry.

5. Template options — declared by the chosen template, asked in the
   order it declares them; entirely different per template (Brupy's own
   code has no built-in knowledge of these — see PRODUCT_ARCH.md §4).
   Some options depend on an earlier one and are silently skipped
   (resolved to a documented value) rather than asked when their
   dependency isn't satisfied — e.g. rest-api's ORM prompt never appears
   if "no database" was chosen. Each option's default below is the
   template's own declared default; a remembered value for this
   `<framework>/<template>` (§6) is preselected instead when one exists
   and is still valid for that option (e.g. still among a select's
   choices).

   For rest-api:
   ? Database? › None / SQLite / PostgreSQL           (default: SQLite)
   ? ORM? › SQLModel / SQLAlchemy                       (skipped if no DB; default: SQLModel)
   ? Add Alembic migrations? (Y/n)                      (skipped if no DB; default: yes)
   ? Background worker? › None / Taskiq / Celery         (default: None)
   ? Message broker? › Redis / RabbitMQ                   (skipped — resolves to "none" — if no worker; default: Redis)
   ? Add Redis (caching)? (y/N)                          (skipped — forced yes — if broker is Redis; default: no)

   For hello-world:
   ? Add configuration (pydantic-settings)? (y/N)        (default: no)

6. Package manager
   ? Package manager? › uv (only option in v0, shown for consistency
     with future choices; not actually prompted in v0 — auto-selected
     and simply echoed: "Using uv to manage dependencies.")

7. Add a Dockerfile?
   ? Add a Dockerfile? (y/N) ›
   - Default **no** (unlike git/install below, this one opts in rather
     than out — most quick scaffolds don't need a container), unless
     this `<framework>/<template>` remembers a different value (§6). If
     yes, and the chosen framework/template doesn't have Docker support
     yet, Brupy warns and continues without one rather than failing.

8. Initialize a git repository?
   ? Initialize a git repository? (Y/n) ›
   - Default yes, unless remembered otherwise (§6). If yes: `git init` +
     initial commit after files are written. If git is not installed/
     available, warn and continue (non-fatal).

9. Install dependencies now?
   ? Install dependencies with uv now? (Y/n) ›
   - Default yes, unless remembered otherwise (§6). If yes: runs `uv
     sync` in the generated directory after writing files, with a
     spinner. If uv is unavailable or the install fails, the project is
     still left in a valid, runnable state (user can `uv sync`
     manually) — this never rolls back generation.

10. Generation
   - Renders the template to disk (see PRODUCT_ARCH.md for the
     mechanism). Shows a live-ish summary of files created.

11. Summary / next steps
   Options: database=sqlite, orm=sqlmodel, migrations=True, worker=none, broker=none, redis=False
   Creating my-api/ from fastapi/rest-api...
     ✔ ...
   ✔ Initialized git repository
   ✔ Installed dependencies (uv sync)

   Next steps:
     cd my-api
     uv run fastapi dev src/my_api/main.py

   Then open http://127.0.0.1:8000 — plus a migrate command, a worker
   command, and/or Docker commands, whichever apply to what was chosen.
```

   The run command on that "Next steps" line is framework-specific —
   each framework declares its own `run_command` in `template.json`
   (see PRODUCT_ARCH.md §4.1), so a Flask project prints `uv run flask
   --app src/my_api/main.py run` instead of the FastAPI command shown
   above.

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

Triggered by either passing `--yes`, or by Brupy detecting stdin is not a
TTY (e.g. running in CI). In that mode:

- Every prompt above becomes: use the flag/`--option` if given, else use
  the remembered value if one exists and is still valid (§6), else use
  the documented default — **never block on input**.
- Framework defaults to the first enabled framework; template defaults to
  the first enabled template within it; each template option defaults to
  its own declared default (or its `skip_value`, if its dependency isn't
  satisfied — same rule as interactive mode, just without the prompt) —
  each of these is superseded by a remembered value first, per the rule
  above.
- If a required decision has no safe default and no flag was given (there
  are none in v0 — every prompt has a default), Brupy would exit `1` with
  an actionable error rather than hang. This rule exists for future
  prompts that may not have a safe default.
- Output is the same summary block, without spinners/animations (falls
  back to plain log lines when not a TTY).

## 5. Error flows

| Situation | Behavior |
|---|---|
| Target directory exists, non-empty, no `--force`, non-interactive (`--yes`/piped stdin) | Exit 1, no files written — can't prompt without a TTY. |
| Target directory exists, non-empty, no `--force`, interactive | Prompts "Overwrite? (y/N)" before proceeding. Declining exits 1, no files written; confirming proceeds exactly as `--force` would have. |
| Target directory exists, non-empty, `--force` | Overwrites immediately, no prompt — the flag itself is the confirmation. |
| Invalid project name | Re-prompt (interactive) or exit 1 with reason (non-interactive). |
| Unknown/disabled `--framework` or `--template` | Exit 1 with reason (non-interactive); interactive select lists disable the entry so it can't be chosen. |
| `--option key=value` with an unknown key for the chosen template | Exit 1 listing the unknown key(s). |
| `--option` with a value not among a select option's choices, or not a valid boolean for a confirm option | Exit 1 with the specific reason and (for select) the valid choices. |
| `--option` missing the `=` (e.g. `--option database`) | Exit 1: "must be in key=value form." |
| `--docker` requested but the chosen template has no Docker support | Warn, skip the Dockerfile, still exit 0 — never fails generation over an optional extra. |
| `uv` not found, install requested | Warn, skip install step, still exit 0 — project is valid, just not installed. |
| `git` not found, git-init requested | Warn, skip git step, still exit 0. |
| Unexpected exception during generation | Roll back (delete partially-written target directory) and exit 2 with the error. Generation is all-or-nothing from the user's perspective. |

## 6. Remembered preferences (`~/.brupy/last.json`)

After a **successful** generation (files written; git/install steps can
still fail independently without affecting this), Brupy records:

- The chosen framework, as the new "last framework."
- The chosen template, as the new "last template" *for that framework*
  specifically (picking `fastapi` again later remembers `rest-api`
  independently of whatever's remembered for a future `flask`).
- For that exact `<framework>/<template>`: every resolved template
  option, plus whether `--docker`/`--git`/`--install` were used.

This is stored in `~/.brupy/last.json`. On the *next* run:

- The wizard preselects the remembered framework/template/options/docker/
  git/install wherever noted in §2 above, instead of the template's own
  hardcoded defaults.
- A flagless non-interactive run (§4) falls back to the same remembered
  values instead of the hardcoded defaults.
- An explicit flag or `--option` **always** wins over a remembered value,
  same as it always wins over a hardcoded default — remembering only
  changes what happens when nothing else specifies a value.
- A remembered value that's no longer valid (e.g. a select option whose
  choices changed, or a stale key from an older Brupy version) is
  silently ignored in favor of the template's own default — never an
  error, never a crash.

`--remember/--no-remember` (default **on**) controls this per run: with
`--no-remember`, Brupy neither reads nor writes `~/.brupy/last.json` for
that invocation, as if the file didn't exist.

Reading and writing this file is entirely best-effort: if it's missing,
unreadable, not valid JSON, or the directory can't be created/written to
(e.g. a read-only home directory), Brupy silently proceeds as if nothing
were remembered — this never fails or warns during generation. There is
no version/schema field; an entry from an older Brupy that no longer
makes sense for the current template just falls through the same
staleness handling as any other invalid remembered value.

## 7. Post-generation experience

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

Deeper than `AGENTS.md`: `.agents/skills/<id>/` — one directory per
library actually used (e.g. `fastapi`, `sqlmodel`, `alembic`, `pytest`),
each with a `SKILL.md`, `references/`, and `guides/` going into real
depth on that library *as this specific project uses it* — plus a
generated `.agents/skills/README.md` index. `AGENTS.md`'s own "Agent
skills" section links to whichever apply. See PRODUCT_ARCH.md §4.5 for
how a template decides which skills to include.

## 8. Example transcript (interactive, rest-api with a real stack)

```
$ uvx brupy
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
  ✔ .agents/skills/README.md
  ✔ .agents/skills/fastapi/... (+ pydantic-settings, sqlmodel, alembic, taskiq, pytest — one skill per line, omitted here for brevity)
  ✔ .env
  ✔ .env.example
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

## 9. Example transcript (non-interactive / CI, hello-world)

```
$ brupy new my-api --framework fastapi --template hello-world --git --install --yes
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
