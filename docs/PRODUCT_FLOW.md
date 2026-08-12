# Flint — Product Flow

**Status:** Draft for v0
**Last updated:** 2026-08-12

Companion to `PRODUCT_SPEC.md`. Describes exactly what happens when a user
runs Flint, in both interactive and non-interactive modes.

## 1. Entry points

| Command | Behavior |
|---|---|
| `uvx flint` / `flint` | No args → full interactive wizard, generates into a new directory named after the answered project name, in the current working directory. |
| `flint new [NAME]` | Same wizard; `NAME` pre-fills the project-name prompt (or skips it if `--yes`). |
| `flint new NAME --framework fastapi --git --install --yes` | Fully non-interactive; no prompts, generates immediately. |
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
     ❯ FastAPI — Hello World
       Flask — Hello World (coming soon)
       Django — Hello World (coming soon)
   - v0 ships FastAPI only. Other entries are shown but disabled/greyed
     to signal the roadmap (create-next-app does the same for future
     options) — selecting one prints "coming soon" and re-prompts.

4. Package manager
   ? Package manager? › uv (only option in v0, shown for consistency
     with future choices; not actually prompted in v0 — auto-selected
     and simply echoed: "Using uv to manage dependencies.")

5. Initialize a git repository?
   ? Initialize a git repository? (Y/n) ›
   - Default yes. If yes: `git init` + initial commit after files are
     written. If git is not installed/available, warn and continue
     (non-fatal).

6. Install dependencies now?
   ? Install dependencies with uv now? (Y/n) ›
   - Default yes. If yes: runs `uv sync` in the generated directory
     after writing files, with a spinner. If uv is unavailable or the
     install fails, the project is still left in a valid, runnable state
     (user can `uv sync` manually) — this never rolls back generation.

7. Generation
   - Renders the template to disk (see PRODUCT_ARCH.md for the
     mechanism). Shows a live-ish summary of files created.

8. Summary / next steps
   ✔ Created my-api/
     ✔ Initialized git repository
     ✔ Installed dependencies (uv sync)

   Next steps:
     cd my-api
     uv run fastapi dev src/my_api/main.py

   Then open http://127.0.0.1:8000 — you should see {"message": "Hello, World!"}.
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

- Every prompt above becomes: use the flag if given, else use the
  documented default, **never block on input**.
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
| `uv` not found, install requested | Warn, skip install step, still exit 0 — project is valid, just not installed. |
| `git` not found, git-init requested | Warn, skip git step, still exit 0. |
| Unexpected exception during generation | Roll back (delete partially-written target directory) and exit 2 with the error. Generation is all-or-nothing from the user's perspective. |

## 6. Post-generation experience

The generated project's own README (written by the template, not typed
by the user) always contains, at minimum:
1. The exact run command.
2. The exact test command.
3. A one-line description of the project layout.

This is the same information printed in the CLI summary, so the user
never has to re-discover it later.

## 7. Example transcript (interactive)

```
$ uvx flint
? What is your project named? my-api
? Which framework? FastAPI — Hello World
Using uv to manage dependencies.
? Initialize a git repository? Yes
? Install dependencies with uv now? Yes

Creating my-api/ from fastapi-hello-world...
  ✔ pyproject.toml
  ✔ README.md
  ✔ .gitignore
  ✔ src/my_api/__init__.py
  ✔ src/my_api/main.py
  ✔ tests/test_main.py
✔ Initialized git repository (initial commit)
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api

Next steps:
  cd my-api
  uv run fastapi dev src/my_api/main.py

Then open http://127.0.0.1:8000
```

## 8. Example transcript (non-interactive / CI)

```
$ flint new my-api --framework fastapi --git --install --yes
Creating my-api/ from fastapi-hello-world...
  ✔ pyproject.toml
  ✔ README.md
  ✔ .gitignore
  ✔ src/my_api/__init__.py
  ✔ src/my_api/main.py
  ✔ tests/test_main.py
✔ Initialized git repository (initial commit)
✔ Installed dependencies (uv sync)

Success! Created my-api at ./my-api
```
