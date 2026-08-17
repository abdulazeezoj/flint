# Remembered Preferences

Brupy remembers what you picked last time and uses it as the new default —
so a project you generate often, or a CI job you run on repeat, needs fewer
and fewer flags each time. The interesting part isn't the remembering; it's
the forgetting — a stale value, a missing file, a corrupted one — none of it
is allowed to interrupt a run.

## What gets remembered

After a **successful** generation, Brupy saves three things to
`~/.brupy/last.json`:

- **The last framework** you picked (e.g. `fastapi`).
- **The last template you picked for that framework**, specifically.
  Framework and template are remembered independently, so picking
  `flask` today doesn't overwrite what's remembered for `fastapi` — next
  time you pick `fastapi` again, it still offers back whichever template
  you last used with it.
- **For that exact `<framework>/<template>` pair**: every resolved
  template option (`database`, `orm`, `migrations`, `worker`, `broker`,
  whatever that template defines), plus whether `--docker`, `--git`, and
  `--install` were used.

Options are bucketed per `<framework>/<template>` pair, not shared
globally — `fastapi/rest-api`'s remembered `database` choice never leaks
into `fastapi/hello-world`'s options, even though they share a framework.

## When it's written

Only after generation actually succeeds — the project's files have been
written to disk. A failed or cancelled run (invalid input, an existing
non-empty target directory you declined to overwrite, an unexpected
error) never touches `~/.brupy/last.json`; whatever was remembered before
stays exactly as it was.

The write happens *before* the optional git-init and dependency-install
steps, so if `--git` or `--install` fails or is skipped after generation,
that doesn't change what gets remembered — it reflects what you asked
for, not whether every post-generation nicety also succeeded.

## How it's used next time

Remembered values feed into prompt defaults in two different modes, not
just one:

- **Interactive wizard** — remembered choices become the preselected
  (arrow-key) default for each prompt: framework, template, every
  template option, and the Docker/git/install confirmations.
- **Flagless non-interactive runs** (`--yes`, or any run in CI where
  stdin isn't a TTY) — anything you didn't pass a flag for falls back to
  the remembered value instead of the template's own hardcoded default.

Both cases share the same lookup, so it's worth thinking of remembered
preferences as replacing the *hardcoded* defaults, not as a separate
interactive-only convenience.

## Precedence

An explicit flag or `-o key=value` **always** wins over a remembered
value — no exceptions. Remembering only changes what happens when nothing
else specifies a value; it never overrides something you actually typed.

## Staleness — never an error

If a remembered value no longer makes sense for the current template —
say you upgraded Brupy and a `select` option's choices changed, or an
option was renamed or removed entirely — Brupy doesn't error and doesn't
warn. It silently falls back to the template's own current default for
that one value, exactly as if nothing had been remembered for it. Every
other still-valid remembered value is unaffected.

There's no version or schema field in `last.json` for this — stale
entries just stop applying to the parts that no longer fit, quietly.

## Resilience

Reading and writing `~/.brupy/last.json` is entirely best-effort. If the
file is missing, unreadable, not valid JSON, or isn't even a JSON object
(e.g. hand-edited into something odd), Brupy treats it as empty and
proceeds with the template's normal defaults — this never crashes or
warns during generation. The same applies in reverse: if the file can't
be written (a read-only home directory, out of disk space, whatever),
the save is silently skipped and the generation you just ran is
unaffected.

## Opting out

Pass `--no-remember` to skip both reading *and* writing
`~/.brupy/last.json` for that one invocation — Brupy behaves as if the
file didn't exist, using template defaults on the way in and leaving the
file untouched on the way out. It's a per-run flag, not a persistent
setting: the next run without it goes back to reading and writing as
normal. See [CLI Reference](cli-reference.md) for the full
`--remember`/`--no-remember` flag details.

## Where the file lives

`~/.brupy/last.json` is a plain JSON file — nothing sensitive, nothing
binary. Shape looks like this:

```json
{
  "last_framework": "fastapi",
  "last_templates": { "fastapi": "rest-api" },
  "templates": {
    "fastapi/rest-api": {
      "options": { "database": "postgres", "orm": "sqlmodel" },
      "docker": true,
      "git_init": false,
      "install": true
    }
  }
}
```

!!! tip "Resetting to defaults"
    Since it's just a plain file with no other purpose, deleting it is a
    safe, complete reset: `rm ~/.brupy/last.json`. Brupy will recreate it
    on your next successful run, and until then every prompt goes back to
    the template's own hardcoded defaults.

## Example

Generate a project with an explicit stack:

```bash
brupy new my-api \
  --framework fastapi --template rest-api \
  -o database=postgres --docker
```

That run succeeds, so Brupy remembers `fastapi`, `rest-api`, `database=postgres`,
and `docker=true` (along with whatever defaults applied to the rest of the
`rest-api` options and to git/install). Run Brupy again with no arguments:

```bash
brupy
```

```text
? What is your project named?
? Which framework? › (Use arrow keys)
  ❯ FastAPI
    Flask
? Which template? › (Use arrow keys)
    Full-Stack
    Hello World
  ❯ REST API
? Database? › (Use arrow keys)
  ❯ PostgreSQL
    SQLite
...
? Add a Dockerfile? (Y/n)
```

FastAPI, REST API, PostgreSQL, and the Dockerfile prompt are all
preselected — nothing you didn't already decide once needs deciding
again. Add `-o database=sqlite` to that second run and it wins outright,
no matter what's remembered.

## Next

- [CLI Reference](cli-reference.md) — the `--remember`/`--no-remember`
  flag, non-interactive fallback order, and full flag table
- [Getting Started](getting-started.md) — the interactive wizard walkthrough
- [Templates](project-templates/index.md) — what each template's options
  actually are
