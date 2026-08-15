# CLI Reference

Every `flint` command, flag, and exit code. If you just want the fast
path, see [Getting Started](getting-started.md) — this page is the
reference to flip back to.

## Commands

| Command | What it does |
|---|---|
| `flint` | Alias for `flint new` with no name — full interactive wizard. |
| `flint new [NAME]` | Generate a new project. `NAME` pre-fills the project-name prompt (or is used directly with `--yes`/non-interactive). |
| `flint list-templates` | Print every framework/template pair. Generates nothing. |
| `flint --version` | Print the installed version and exit. |
| `flint --help` / `flint new --help` | Print usage and exit. |

`flint` with no subcommand behaves exactly like `flint new` — the same
`create-next-app` muscle memory of "just run the command" applies.

## `flint new [NAME]`

```bash
flint new [NAME] [OPTIONS]
```

`NAME` is a free-text project name, e.g. `my-api` — Flint turns it into
a directory slug and an importable Python package name (see
[Name validation](#name-validation) below). Omit it and you're prompted
interactively, or it falls back to `my-app` in non-interactive mode.

### Flags

| Flag | Default | Description |
|---|---|---|
| `--framework TEXT` | *(prompted / first enabled)* | Framework to use, e.g. `fastapi`. |
| `--template TEXT` | *(prompted / first enabled)* | Template variant within the framework, e.g. `hello-world`. |
| `--option`, `-o KEY=VALUE` | *(repeatable)* | Set a template-specific option as `key=value`, e.g. `-o database=postgres -o orm=sqlmodel`. See [`--option` / `-o`](#-option-o-keyvalue) below. |
| `--docker` / `--no-docker` | `--no-docker` | Add a `Dockerfile` (and `.dockerignore`). |
| `--git` / `--no-git` | `--git` | Initialize a git repository. |
| `--install` / `--no-install` | `--install` | Install dependencies with `uv`. |
| `--yes`, `-y` | off | Accept defaults for anything not given as a flag — skips all prompts. |
| `--force` | off | Generate even if the target directory already exists and is non-empty. |
| `--remember` / `--no-remember` | `--remember` | Remember these choices in `~/.flint/last.json` as the default for next time. |

!!! note "Defaults above are the template's own hardcoded defaults"
    Every flag's "prompted" default can instead resolve to a **remembered**
    value from `~/.flint/last.json`, if one exists and is still valid. An
    explicit flag or `-o` always wins regardless. See
    [Remembered preferences](#remembered-preferences).

Every flag mirrors an interactive prompt one-for-one, so any combination
of flags you pass is simply skipped in the wizard — pass all of them and
nothing is asked at all.

### Non-interactive mode

Two things trigger non-interactive mode:

- passing `--yes` / `-y`, or
- Flint detecting that stdin isn't a TTY (e.g. running in CI, or piped
  input).

Every prompt still resolves in that mode — it just never blocks on input.
Flint works down a fallback chain: the flag or `-o` value if you gave
one, the remembered value if it exists and is still valid, otherwise the
template's own documented default. Framework falls back to the first
enabled framework; template, to the first enabled one within it.

### Name validation

Your project name goes through two independent transforms:

- **Directory slug** — lowercased, spaces/underscores become `-`, and
  anything outside `[a-z0-9-]` is stripped (e.g. `My Api!` → `my-api`).
- **Package name** — the same slug with hyphens turned into underscores
  (a valid Python identifier), prefixed with `_` if it would otherwise
  start with a digit (e.g. `my-api` → `my_api`).

Flint rejects a name outright — with a specific reason, never a silent
mutation or a stack trace — if it:

- normalizes to an empty string (no letters or numbers at all),
- can't form a valid Python identifier,
- is a Python keyword or soft keyword (`class`, `match`, ...), or
- shadows a standard-library module name (`test`, `types`, `os`, `json`,
  ...).

Interactively, an invalid name just re-prompts with the reason shown.
Non-interactively, it's an exit-1 error.

### Overwriting an existing directory

If the target directory (`./<slug>`) already exists and is **non-empty**,
Flint refuses to touch it by default:

- **Interactive**, no `--force`: you're asked
  `Directory '<slug>' already exists and is not empty. Overwrite?` (default
  no). Confirming proceeds exactly as `--force` would — same run, same
  result. Declining exits 1 with no files written.
- **Non-interactive** (`--yes` or piped stdin), no `--force`: no prompt —
  straight to the same exit-1 error, since there's no TTY to ask on.
- **`--force` passed**: overwrites immediately, no prompt at all — the
  flag itself is the confirmation.

An empty or non-existent target directory never triggers any of this.

### `--option` / `-o key=value`

Templates declare their own options (database, ORM, migrations, worker,
broker, and so on) — Flint's core has no built-in knowledge of what any
given template accepts. Use `-o key=value` to set one, and repeat the
flag for each option you want to set:

```bash
flint new my-api --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=celery -o broker=redis \
  --yes
```

```bash
flint new my-api --framework fastapi --template hello-world \
  -o config=true --yes
```

Flint validates each value against the chosen template's own declared
options:

- **Unknown key** — `--option key=value` where `key` isn't one this
  template declares: exit 1, listing the unknown key(s).
- **Invalid select value** — a value not among that option's valid
  choices: exit 1, e.g. `'mysql' is not a valid value for --option
  database. Available: none, postgres, sqlite.`
- **Invalid boolean** — a confirm-type option (like `migrations` or
  `config`) needs `true`/`false` (also accepts `1`/`0`/`yes`/`no`/`y`/`n`,
  case-insensitive): exit 1, e.g. `'maybe' is not a valid boolean for
  --option migrations (use true/false).`
- **Missing `=`** — `--option database` with no value: exit 1, `--option
  'database' must be in key=value form.`

Some options depend on an earlier one, and when that dependency isn't
satisfied, Flint resolves them silently to a documented value — never
asked, never left unset. For example, `rest-api`'s `orm` option is
skipped entirely (and resolves to its documented value) if
`database=none`. That holds whether the dependency was set via `-o`, a
remembered value, or a prompt answer.

See [Templates](project-templates/index.md) for the exact option keys,
types, and choices each framework/template pair declares.

## `flint list-templates`

```bash
flint list-templates
```

Prints a table of every framework/template combination Flint knows
about — including any disabled/"coming soon" entries — with each
template's label, description, and whether it supports `--docker`:

```text
┏━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Framework ┃ Template    ┃ Description                       ┃ Docker ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ FastAPI   │ Full-Stack  │ A layered FastAPI full-stack...   │   ✓    │
│ FastAPI   │ Hello World │ A minimal FastAPI app with a...   │   ✓    │
│ FastAPI   │ REST API    │ A layered FastAPI REST API...     │   ✓    │
│ Flask     │ Full-Stack  │ A layered Flask full-stack...     │   ✓    │
│ Flask     │ Hello World │ A minimal Flask app with a...     │   ✓    │
│ Flask     │ REST API    │ A layered Flask REST API...       │   ✓    │
└──────────┴─────────────┴───────────────────────────────────┴────────┘

Pass a pair with e.g. flint new my-api --framework fastapi --template rest-api.
Templates with their own choices (database, ORM, ...) take -o key=value —
see the wizard or each template's README for available keys.
```

(Descriptions truncated above for width — the real table prints each in
full. See [Templates](project-templates/index.md) for the complete text.)

This is pure introspection — it generates nothing, no matter what.

## `flint --version`

Prints the installed version and exits, e.g.:

```text
$ flint --version
flint 0.10.0
```

## `flint --help`

Prints top-level usage (and `flint new --help` for the `new` subcommand's
own flags), then exits — standard Typer/Click help output.

## Exit codes

| Code | Meaning | Triggers |
|---|---|---|
| `0` | Success | Project generated. Docker/git/install steps failing independently (e.g. `uv`/`git` not found) does **not** change this — generation itself is what's graded. |
| `1` | User/input error | Invalid project name; non-empty target dir with no `--force` and no interactive confirmation; unknown or disabled `--framework`/`--template`; unknown `-o` key; invalid `-o` value (bad select choice or non-boolean); `-o` missing `=`; cancelling an interactive prompt (Ctrl-C). |
| `2` | Unexpected/internal error | Anything not caught as a user error. Flint rolls back — deletes the partially-written target directory — before exiting, so a failed run never leaves a half-generated project behind. |

A few situations look like errors but are **not** — they warn and still
exit `0`, because they're optional extras rather than the point of the
run:

| Situation | Behavior |
|---|---|
| `--docker` requested but the template doesn't support Docker yet | Warns, skips the Dockerfile, generation continues. |
| `uv` not found, install requested | Warns, skips the install step — project is still valid, just not installed. |
| `git` not found, git-init requested | Warns, skips git init. |

!!! tip
    Because a partially-failed generation (exit 2) is rolled back
    entirely, and every optional post-generation step degrades to a
    warning instead of a failure, a `0` exit code always means you have a
    complete, runnable project on disk.

## Remembered preferences

After a successful generation, Flint saves the framework, template, and
every resolved option (plus `--docker`/`--git`/`--install`) to
`~/.flint/last.json`, and uses them as the new default next time — both
for what the wizard preselects and what a flagless `--yes` run falls back
to. An explicit flag or `-o` always overrides a remembered value, and
Flint quietly ignores anything stale or invalid. Pass
`--remember`/`--no-remember` to control whether a given run reads or
writes this file at all (default: on). See
[Remembered Preferences](preferences.md) for the full mechanism.

## Full non-interactive examples

A minimal `hello-world` scaffold in CI:

```bash
flint new my-api --framework fastapi --template hello-world --yes
```

`rest-api` with an explicit stack, no git, no install (e.g. a
generate-only CI step):

```bash
flint new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=rabbitmq \
  --docker --no-git --no-install --yes
```

Same, but forcing into an existing (non-empty) directory and opting this
one run out of remembering/reading `~/.flint/last.json`:

```bash
flint new my-api \
  --framework flask --template rest-api \
  -o database=sqlite -o orm=sqlalchemy \
  --force --no-remember --yes
```

`--yes` accepts the documented (or remembered) default for anything you
didn't pass a flag for — no prompts, safe for CI. See
[Templates](project-templates/index.md) for what each framework/template
pair actually generates, and [Getting Started](getting-started.md) for the
interactive walkthrough.
