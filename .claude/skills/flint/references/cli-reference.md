# Flint CLI reference

Every `flint` command, flag, and exit code.

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

`NAME` is a free-text project name, e.g. `my-api` — flint turns it into
a directory slug and an importable Python package name (see Name
validation below). Omit it and you're prompted interactively, or it
falls back to `my-app` in non-interactive mode.

### Flags

| Flag | Default | Description |
|---|---|---|
| `--framework TEXT` | *(prompted / first enabled)* | Framework to use, e.g. `fastapi`. |
| `--template TEXT` | *(prompted / first enabled)* | Template variant within the framework, e.g. `hello-world`. |
| `--option`, `-o KEY=VALUE` | *(repeatable)* | Set a template-specific option as `key=value`, e.g. `-o database=postgres -o orm=sqlmodel`. See `--option` / `-o` below. |
| `--docker` / `--no-docker` | `--no-docker` | Add a `Dockerfile` (and `.dockerignore`). |
| `--git` / `--no-git` | `--git` | Initialize a git repository. |
| `--install` / `--no-install` | `--install` | Install dependencies with `uv`. |
| `--yes`, `-y` | off | Accept defaults for anything not given as a flag — skips all prompts. Always pass this when generating on someone's behalf; you can't answer interactive prompts. |
| `--force` | off | Generate even if the target directory already exists and is non-empty. |
| `--remember` / `--no-remember` | `--remember` | Remember these choices in `~/.flint/last.json` as the default for next time. |

The "prompted" defaults above are the template's own hardcoded
defaults, but each one can instead resolve to a **remembered** value
from `~/.flint/last.json`, if one exists and is still valid. An
explicit flag or `-o` always wins regardless — see Remembered
preferences below.

Every flag mirrors an interactive prompt one-for-one, so passing all of
them (plus `--yes`) skips every prompt and produces a fully
deterministic, reviewable command.

### Non-interactive mode

Two things trigger non-interactive mode: passing `--yes`/`-y`, or flint
detecting that stdin isn't a TTY (e.g. running in CI, or piped input —
this includes most agent tool-call contexts).

Every prompt still resolves in that mode — it just never blocks on
input. Flint works down a fallback chain: the flag or `-o` value if you
gave one, the remembered value if it exists and is still valid,
otherwise the template's own documented default. Framework falls back
to the first enabled framework; template, to the first enabled one
within it.

### Name validation

The project name goes through two independent transforms:

- **Directory slug** — lowercased, spaces/underscores become `-`, and
  anything outside `[a-z0-9-]` is stripped (e.g. `My Api!` → `my-api`).
- **Package name** — the same slug with hyphens turned into underscores
  (a valid Python identifier), prefixed with `_` if it would otherwise
  start with a digit (e.g. `my-api` → `my_api`).

Flint rejects a name outright — with a specific reason, never a silent
mutation or a stack trace — if it normalizes to an empty string, can't
form a valid Python identifier, is a Python keyword/soft keyword
(`class`, `match`, ...), or shadows a standard-library module name
(`test`, `types`, `os`, `json`, ...). Non-interactively this is an
exit-1 error.

### Overwriting an existing directory

If the target directory (`./<slug>`) already exists and is
**non-empty**, flint refuses to touch it unless `--force` is passed —
non-interactively (which is how you should be running it), no `--force`
means a straight exit-1 error, no prompt, no files written. An empty or
non-existent target directory never triggers this.

### `--option` / `-o key=value`

Templates declare their own options (database, ORM, migrations,
worker, broker, and so on) — flint's core has no built-in knowledge of
what any given template accepts. Use `-o key=value` to set one, and
repeat the flag for each option you want to set:

```bash
flint new my-api --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=celery -o broker=redis \
  --yes
```

Flint validates each value against the chosen template's own declared
options and exits 1 with a specific message on: an unknown key, an
invalid select value (not among that option's valid choices), an
invalid boolean (confirm-type options accept `true`/`false`/`1`/`0`/
`yes`/`no`/`y`/`n`, case-insensitive), or a missing `=`.

Some options depend on an earlier one, and when that dependency isn't
satisfied, flint resolves them silently to a documented value — never
asked, never left unset, never an error. For example, `rest-api`'s
`orm` option is skipped entirely (and resolves to its documented
default) if `database=none`. See `references/templates.md` for the
exact option keys, choices, and dependency rules per template.

## `flint list-templates`

```bash
flint list-templates
```

Prints a table of every framework/template combination flint knows
about — including any disabled/"coming soon" entries — with each
template's label, description, and whether it supports `--docker`.
Pure introspection: generates nothing, no matter what. Useful to run
first if unsure what's available, rather than guessing at framework/
template names.

## `flint --version`

Prints the installed version and exits.

## Exit codes

| Code | Meaning | Triggers |
|---|---|---|
| `0` | Success | Project generated. Docker/git/install steps failing independently (e.g. `uv`/`git` not found) does **not** change this — generation itself is what's graded. |
| `1` | User/input error | Invalid project name; non-empty target dir with no `--force`; unknown or disabled `--framework`/`--template`; unknown `-o` key; invalid `-o` value; `-o` missing `=`. |
| `2` | Unexpected/internal error | Anything not caught as a user error. Flint rolls back — deletes the partially-written target directory — before exiting, so a failed run never leaves a half-generated project behind. |

A few situations look like errors but exit `0` and just warn, because
they're optional extras rather than the point of the run: `--docker`
requested but the template doesn't support Docker yet; `uv`/`git` not
found when an install/git-init was requested. A `0` exit code always
means a complete, runnable project is on disk.

## Remembered preferences

After a successful generation, flint saves the framework, template,
and every resolved option (plus `--docker`/`--git`/`--install`) to
`~/.flint/last.json`, and uses them as the new default next time. An
explicit flag or `-o` always overrides a remembered value. Pass
`--remember`/`--no-remember` to control whether a given run reads or
writes this file at all (default: on) — pass `--no-remember` for a
one-off generation that shouldn't affect future runs' defaults.

## Full non-interactive examples

A minimal `hello-world` scaffold:

```bash
flint new my-api --framework fastapi --template hello-world --yes
```

`rest-api` with an explicit stack, no git, no install (e.g. a
generate-only step):

```bash
flint new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=rabbitmq \
  --docker --no-git --no-install --yes
```

Forcing into an existing (non-empty) directory, opting out of
remembering/reading `~/.flint/last.json`:

```bash
flint new my-api \
  --framework flask --template rest-api \
  -o database=sqlite -o orm=sqlalchemy \
  --force --no-remember --yes
```
