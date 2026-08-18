# Brupy — Product Spec

**Status:** Draft for v0
**Owner:** Product
**Last updated:** 2026-08-18 (v0.20.0: CLAUDE.md/.claude/skills for generated projects, `install-skill`, update-check — see §8/§9/§11)

## 1. Vision

Brupy is `create-react-app` / `create-next-app` for Python backend frameworks.

One command, a short interactive wizard, and you have a running project —
scaffolded with modern tooling, sane defaults, and zero boilerplate to
hand-write.

```
uvx brupy
```

...and 60 seconds later you're looking at `Hello, World!` from a real,
runnable FastAPI app. Pick a richer template and the same wizard also
gets you a real database, migrations, and a background worker wired up —
whatever a project actually needs to stop being a toy on day one.

## 2. Problem

Every new FastAPI/Flask/etc. project starts with the same repetitive setup:
`pyproject.toml`, virtual env, src layout, a first endpoint, a test, a
`.gitignore`, a README nobody writes — and, past the toy stage, the same
recurring decisions: which database, which ORM, whether to bother with
migrations yet, whether background work needs a queue. Developers either
copy an old project (and drag its cruft along) or start from a blank
folder every time, re-deciding and re-wiring the same things.

The JS ecosystem solved the first part years ago (`create-react-app`,
`create-next-app`, `create-vite`) with a single interactive command that
gets you to running code immediately. Python has no equivalent with that
UX. The nearest tools (`cookiecutter`, `copier`, and a handful of
FastAPI-specific scaffolders) require finding and trusting a third-party
template repo, are template-authoring frameworks rather than finished
products, and either stay minimal (bare boilerplate) or go maximal (one
big configurable mega-template with a wall of flags) rather than letting
a project grow into what it needs. Brupy's answer is a small set of
distinct, opinionated templates, each of which can offer its own
follow-up choices — not one template trying to be everything.

## 3. Terminology: framework, template, option

Three distinct concepts in the wizard — don't conflate them:

- **Framework** — the underlying library, e.g. `fastapi`, `flask`.
  Selected first.
- **Template** — a specific project shape built on that framework, e.g.
  `hello-world`, `rest-api`, `full-stack`. Selected second, scoped to
  the chosen framework.
- **Option** — a further, template-specific choice, declared by the
  template itself (not hardcoded in Brupy). E.g. `rest-api` asks for a
  database, ORM, whether to add migrations, a background worker, and
  Redis; `hello-world` asks only whether to add `pydantic-settings`
  config. Different templates can declare entirely different options —
  Brupy's CLI/wizard code has no built-in knowledge of "database" or
  "worker," it just renders whatever a template's `template.json`
  declares (see `PRODUCT_ARCH.md` §4).

A generated project always comes from exactly one `<framework>/<template>`
pair (e.g. `fastapi/rest-api`) plus whatever options that template offers.
This is what lets the roadmap grow in three independent directions — more
frameworks, more templates per framework, and richer options per
template — without any axis blocking the others.

## 4. Goals — v0

1. Zero-arg interactive wizard: `brupy` (or `uvx brupy`) prompts for the
   handful of decisions that matter — including a template's own options
   — and generates a project.
2. The wizard produces a runnable "Hello World" FastAPI app in under 60
   seconds (excluding dependency download time), managed by `uv`.
3. A richer `rest-api` template offers real head-start choices — database
   (none/SQLite/PostgreSQL), ORM (SQLModel/SQLAlchemy), Alembic
   migrations, a background worker (Taskiq/Celery), and Redis — instead
   of forcing a from-scratch wiring job the moment a project needs more
   than a single endpoint.
4. A fully non-interactive mode via flags, including a generic
   `--option key=value` for template-specific choices, for scripting and
   CI.
5. The generated project includes: `src/` layout package, `uv`-managed
   `pyproject.toml`, a README with run instructions, `AGENTS.md` (context
   for AI coding agents), `.gitignore`, and a passing `pytest` test — with
   no manual edits required to run it, regardless of which options were
   chosen.
6. Optionally, a generated `Dockerfile`/`.dockerignore` via `--docker`.
7. Brupy ships as an installable, `pipx`/`uv tool`-friendly CLI.
8. Semantic-ish versioning scheme `v{release}.{feature}.{fixes}`, starting
   at `v0.1.0`, with `CHANGELOG.md` updated on every user-facing change.

## 5. Non-Goals — v0

Explicitly out of scope for the first release (candidates for later
`v0.x` releases — the architecture must not preclude them; several are
already stubbed as disabled/"coming soon" entries so the roadmap is
visible in the wizard):

- Frameworks other than FastAPI and Flask (both are enabled as of v0.8;
  no other framework is stubbed on the roadmap yet, see §11)
- Templates other than `hello-world`, `rest-api`, and `full-stack`
- A plugin system / third-party or remote templates
- Monorepo or multi-service scaffolding
- Auth scaffolding, Docker Compose, CI workflow templates
- A GUI or web-based wizard

Database/ORM/migrations/worker selection — a v0.1/v0.2 non-goal — is now
in scope as of v0.3, scoped specifically to the `rest-api` template. A
RabbitMQ broker choice — a v0.1–v0.6 non-goal — is in scope as of v0.7.
`.agents/skills/<framework>` — a v0.1–v0.8 non-goal — is in scope as of
v0.9 (§11). Docker Compose was briefly added and then deliberately removed within
v0.7 itself (see §11) — one Dockerfile per template is a reasonable
default, but a generated `docker-compose.yml` bakes in an
opinion about container topology (one service per app) that doesn't
hold for every project shape a generated app might end up living in
(e.g. a monorepo with its own compose setup already). A third template
beyond `hello-world`/`rest-api` — a v0.1–v0.14 non-goal — is in scope
as of v0.15: `full-stack`, a server-rendered (Jinja2 + HTMX) sibling of
`rest-api` reusing its exact option set (§11).

## 6. Personas

- **Solo/side-project developer** — wants to skip boilerplate and get to
  writing actual endpoints, with a real database wired up from the start
  if the project needs one.
- **Team lead standardizing scaffolding** — wants every new internal
  service to start from the same shape, scriptable in automation,
  including the team's preferred DB/ORM/worker stack.

## 7. User Stories

- As a developer, I run one command, answer a few short prompts, and get a
  working FastAPI app I can `uv run` immediately — no follow-up edits.
- As a developer starting a "real" service, I pick the `rest-api`
  template, choose PostgreSQL + SQLModel + migrations + a Celery worker,
  and get a project with all of that already wired and passing tests —
  not a blank slate I have to wire myself.
- As a developer working in CI/scripts, I run
  `brupy new my-api --framework fastapi --template rest-api -o database=postgres -o orm=sqlmodel --no-git --no-install --yes`
  and get the identical result with no prompts.
- As a developer deploying to a container, I pass `--docker` and get a
  working `Dockerfile` alongside the app, no Docker knowledge required.
- As a developer, after generation I see a clear "next steps" block (cd,
  run, open browser, plus migration/worker commands if relevant) so I
  never have to guess the run command.
- As a developer, if I mistype something — a bad project name, an
  unknown `--option` key, an invalid option value, a non-empty target
  directory — Brupy tells me clearly instead of silently doing the wrong
  thing or half-generating a project.

## 8. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | Interactive wizard order: project name → target directory check → framework → template within that framework → the chosen template's own options, in the order it declares them → add a Dockerfile? (default no) → initialize git repo? (default yes) → install dependencies now? (default yes) |
| FR2 | Validate project name: derive a valid Python package name (snake_case) and a filesystem-safe directory (kebab or snake); refuse to run into a non-empty existing directory without `--force`. In interactive mode, offer a confirmation prompt to overwrite instead of failing outright — declining aborts with no changes made; non-interactive runs are unaffected (`--force` or hard error, no prompt) |
| FR3 | Every prompt has an equivalent flag: `--framework`, `--template`, `--option key=value` (repeatable, for template-specific choices), `--docker/--no-docker`, `--git/--no-git`, `--install/--no-install`, `--yes` (accept all defaults, skip prompts) |
| FR4 | After generation: print a summary of the resolved options, what was created, and the exact next-step commands to run the app (run, migrate, start a worker, `docker build`/`docker run` — whichever apply) |
| FR5 | `brupy --version` prints the current version |
| FR6 | Exit codes: `0` success, `1` user/input error (e.g. bad name, existing dir, disabled framework/template, unknown/invalid `--option`), `2` unexpected/internal error |
| FR7 | `--docker` adds a `Dockerfile` and `.dockerignore`; if the chosen template doesn't support it yet, warn and continue rather than failing the whole generation |
| FR8 | Every generated project includes an `AGENTS.md` with run/test commands, layout, and conventions — no flag, always on |
| FR9 | A template's options can depend on each other (e.g. no ORM prompt when "no database" is chosen); an option whose dependency isn't satisfied resolves to a documented value automatically rather than being asked or left unset |
| FR10 | Regardless of which database a project is configured for, its test suite runs against an isolated, ephemeral database and never touches whatever `DATABASE_URL` points at — "just works" out of the box takes priority over exercising the real backend in tests |
| FR11 | After a successful generation, Brupy remembers the chosen framework, the chosen template per framework, and — per `<framework>/<template>` — the resolved options plus docker/git/install, in `~/.brupy/last.json`. The next run uses these as the new default (both for what the wizard preselects and what a flagless non-interactive run falls back to); an explicit flag or `--option` always overrides a remembered value, and a stale remembered value (no longer valid for the current template) is silently ignored in favor of the template's own default. `--remember/--no-remember` (default on) opts a single run out of reading and writing this file |
| FR12 | `brupy list-templates` prints every framework/template pair (label, description, whether it supports `--docker`), including disabled/"coming soon" entries — an introspection command, generates nothing |
| FR13 | Every generated project gets a one-line `CLAUDE.md` (`@AGENTS.md`, Claude Code's own file-import syntax) alongside `AGENTS.md`, and a `.claude/skills/<id>/` symlinked to each matched `.agents/skills/<id>/` — no flag, always on, best-effort for the symlink specifically (see NFR below) |
| FR14 | `brupy install-skill [--scope project\|user] [--force]` installs the portable `brupy` agent skill (how to invoke this CLI) into an arbitrary directory — the current one by default, or the user's home directory with `--scope user` — for a repo that wasn't scaffolded with brupy in the first place. Refuses to overwrite an existing install without `--force` |

## 9. Non-Functional Requirements

- Cross-platform: macOS, Linux, Windows (path handling via `pathlib`, no
  shell-specific assumptions). Symlink creation (the `.claude/skills/`
  mirror, both in generated projects and `install-skill`) is
  best-effort: a platform that refuses it without elevated privileges
  (Windows without Developer Mode) still gets the real
  `.agents/skills/` content, just not the Claude-specific alias —
  matches `~/.brupy/last.json`'s existing "never let a convenience
  feature break the primary one" precedent.
- No network access required by Brupy itself for generation; only
  `uv`'s own dependency resolution (when the user opts in to "install
  now") touches the network. One deliberate exception: an interactive
  run does a short, cached (once/day), silently-skipped-on-failure PyPI
  version check and prints a one-line "newer version available" notice
  if relevant — never blocks, never fails generation, skipped entirely
  for non-interactive/CI runs or with `BRUPY_NO_UPDATE_CHECK=1`. See
  PRODUCT_ARCH.md §5.1 for the mechanism.
- Rich, colorful terminal output where the terminal supports it, with a
  graceful non-interactive fallback: when stdin isn't a TTY, Brupy
  requires flags instead of hanging on a prompt.

## 10. Distribution & Naming

- CLI command: `brupy`
- PyPI distribution name: `brupy` — same as the command, no split
  needed this time (see `v0.19.0` below); `uvx brupy` and `uv tool
  install brupy` both work with no `--from`.

## 11. Release Process

- Versioning scheme: **`v{release}.{feature}.{fixes}`**
  - `release` — major epoch. We start at `0` (pre-1.0, finding product
    shape); bumps when the product's scope/promise materially changes.
  - `feature` — increments when a release adds new user-facing
    capability (e.g. a new framework, a new prompt).
  - `fixes` — increments for patches/bugfixes with no new capability.
- `v0.0.0` — empty repo (starting point).
- `v0.1.0` — interactive wizard + FastAPI hello-world template,
  non-interactive flags, docs.
- `v0.2.0` — framework/template split (`--framework`/`--template`
  replace the single `fastapi-hello-world` id), `--docker`, `AGENTS.md`
  in generated projects.
- `v0.3.0` — per-template options (`--option key=value`); `rest-api`
  template with database/ORM/migrations/worker/Redis choices;
  `hello-world` gains an optional `pydantic-settings` config; `ai`
  template removed (was a disabled stub, never shipped real content).
- `v0.4.0` — the generated project layout itself becomes opinionated,
  Next.js-style: `main.py`/`worker.py` as fixed entrypoints, `routes/`/
  `tasks/` as "one file per resource/job" folders, `core/` for shared
  infrastructure (config, db session, redis client) — applied
  consistently to both `rest-api` and `hello-world`'s optional config.
- `v0.5.0` — remembered preferences: `~/.flint/last.json` persists the
  last framework/template and per-template resolved options/docker/git/
  install, used as the new default for both the wizard and non-interactive
  runs; `--remember/--no-remember` opts out.
- `v0.6.0` — the `restapi` template is renamed to `rest-api`, matching
  the hyphenated id style `hello-world` already used.
- `v0.7.0` — the `django` stub is dropped from the roadmap entirely
  (Flask is the committed next framework, not Django); `rest-api` gains
  a `broker` choice (Redis/RabbitMQ) for the background worker, `redis`
  becomes an independent caching add-on rather than always implied by a
  worker; `.env.example` ships alongside `.env` wherever a template
  writes one. (Docker Compose generation was briefly added and then
  deliberately removed within this same release — see §5: one
  Dockerfile per template is a safe default, a generated
  `docker-compose.yml` bakes in a container-topology opinion that
  doesn't fit every project, e.g. a monorepo.)
- `v0.8.0` — Flask is enabled as a second framework, with `hello-world`
  and `rest-api` templates matching FastAPI's shape option-for-option
  (`rest-api`'s worker choice is Celery-only — Taskiq is async-first and
  doesn't fit Flask's sync/WSGI model). Each framework now declares its
  own dev-server `run_command` in `template.json`, so the "Next steps"
  summary prints the right command (`uv run flask --app
  src/{package}/main.py run` vs. `uv run fastapi dev
  src/{package}/main.py`) instead of always assuming FastAPI.
- `v0.8.1` — bugfix: `rest-api`'s `migrations` option was decorative in
  both frameworks (`create_all()`/`db.create_all()` ran unconditionally
  on every boot, so autogenerate never saw a real schema diff to
  capture). Fixed in both `fastapi/rest-api` and `flask/rest-api` — see
  PRODUCT_ARCH.md §7.1.
- `v0.9.0` — `.agents/skills/<id>/` catalog: eleven skills (`fastapi`,
  `flask`, `pydantic-settings`, `sqlmodel`, `sqlalchemy`,
  `flask-sqlalchemy`, `alembic`, `flask-migrate`, `taskiq`, `celery`,
  `redis`, `pytest`), each a `SKILL.md` + `references/` + `guides/`,
  shared across templates and included per generated project only for
  the libraries it actually uses (declarative `skills` list in
  `template.json`, same `when`-gating as layers) — plus a generated
  `.agents/skills/README.md` index and an `AGENTS.md` section pointing
  at whichever skills apply. See PRODUCT_ARCH.md §4.5.
- `v0.10.0` — closes out the remaining open items from §12: an
  interactive confirmation prompt before overwriting a non-empty target
  directory (FR2), a new `flint list-templates` introspection command
  (FR12), and the package-manager/template-distribution open questions
  are formally closed (uv-only, bundled-only) rather than left open.
- `v0.10.1` — CI/CD via GitHub Actions: `.github/workflows/ci.yml` runs
  the test suite on every push/PR; `.github/workflows/cd.yml` publishes
  to PyPI on a `v*` tag push, via Trusted Publishing (OIDC, no stored
  API token). No change to the `flint` CLI itself — release
  infrastructure only. See PRODUCT_ARCH.md §8.
- `v0.11.0` — a public docs site (MkDocs, Material theme, GitHub Pages
  via `.github/workflows/docs.yml`): install/getting-started, a full
  CLI reference, one page per template, `.agents/skills/` explained,
  remembered preferences, and a contributing guide. This document set
  (`PRODUCT_SPEC.md`/`PRODUCT_FLOW.md`/`PRODUCT_ARCH.md`) moved to
  `docs/_product/` — internal, excluded from the built site, still the
  source of truth for development direction. See PRODUCT_ARCH.md §4.6.
- `v0.12.0` — the project's name is finalized as **Conjure** (superseded
  one release later, see `v0.13.0`), confirmed available and unclaimed
  on PyPI before any release ever publishes under it; `pyproject.toml`'s
  `[project] name` and the console script were both plainly `conjure`,
  no `-cli` suffix. Two docs-site rendering bugs fixed: the homepage's
  card grid rendered as raw markdown for want of two MkDocs extensions
  (see PRODUCT_ARCH.md §4.6), and `mkdocs.yml`'s `repo_name` pointed at
  the wrong slug — both found and verified fixed via a Playwright visual
  pass across all 11 pages in both themes, not just `mkdocs build
  --strict` (which caught neither). Also an editorial pass tightening
  prose on every page.
- `v0.13.0` — the project is renamed a second time, to **Spindle**
  (superseded one release later, see `v0.14.0`). `conjure` passed a
  plain PyPI-availability check but was rejected outright by PyPI's
  actual project-creation flow: separate from "is it taken," PyPI blocks
  new names within edit-distance 2 of an existing project to deter
  typosquatting, and `conjure` is one character from `conjur` (CyberArk's
  published secrets-management package) — a check that only surfaces at
  real registration time, not from a plain availability lookup, so the
  original candidate sweep never caught it. `spindle` passed PyPI's
  actual registration flow cleanly at the time. Same scope as the
  `flint`→`conjure` rename, plus the GitHub repository itself
  (`abdulazeezoj/flint` → `abdulazeezoj/spindle`).
- `v0.14.0` — the project is renamed a third time, back to **Flint**,
  this time splitting the brand from the PyPI distribution name.
  `spindle` turned out to already be a real, unrelated, published PyPI
  package (a classical-magnetism library) — a plain collision, not a
  squat-guard block, that a direct availability check would have caught
  immediately (and should have, before committing to it). A ~300-candidate
  search across a dozen semantic domains — craft/tool words, birds,
  mythology, whimsical animals, food, invented syllables, 2–3 letter
  abbreviations — found almost nothing both short and genuinely
  unclaimed; PyPI's namespace for short, pronounceable English words is
  overwhelmingly pre-claimed. Rather than continue searching for an
  available bare word, this adopts the pattern real projects use in
  exactly this situation — e.g. GitHub's `spec-kit` ships on PyPI as
  `specify-cli` while the command is `specify`. Brand and CLI command
  are `flint` (reverting `v0.13.0`'s `spindle`→`flint` rename: package,
  command, `~/.spindle/last.json` → `~/.flint/last.json`,
  generated-project attribution, all docs); the PyPI distribution name
  is `flint-kit`, since plain `flint` and `flint-cli` are both real,
  unrelated, already-published packages. `uvx flint` alone no longer
  resolves correctly since distribution and command names differ — the
  ephemeral-run form is `uvx --from flint-kit flint` (`uv tool install
  flint-kit` needs no such adjustment). The GitHub repository is also
  renamed back, `abdulazeezoj/spindle` → `abdulazeezoj/flint` — closing
  out the naming saga with brand, command, and repository all aligned
  again, and only the PyPI distribution name carrying the `-kit` suffix.
  See PRODUCT_ARCH.md §2.
- `v0.14.1` — release tagging is automated (`.github/workflows/release.yml`):
  pushing a version bump to `main` now creates and pushes the `vX.Y.Z`
  tag on its own. Added after a manual `git tag && git push` from
  outside GitHub Actions hit a plain 403 — this repo's tag protection
  allows tag creation from CI but not from that external credential,
  even though the same credential could push ordinary branch commits
  fine. Its first design chained straight into `cd.yml` as a reusable
  workflow (`workflow_call`); that part turned out to break PyPI's
  Trusted Publishing verification and never actually published — see
  `v0.14.2`.
- `v0.14.2` — fixes `v0.14.1`'s publish step. PyPI's Trusted Publishing
  OIDC check verifies the *top-level* workflow that ran, not any
  reusable workflow it calls — `workflow_call`-ing `cd.yml` from
  `release.yml` made the certificate say `release.yml`, which never
  matches a Trusted Publisher registered for `cd.yml`. `cd.yml` now
  triggers on `workflow_run` (listening for `release.yml`'s completion)
  instead, so it always runs as its own top-level workflow; its
  original `push: tags: v*` trigger is unchanged, so a tag pushed by a
  human still works too. See PRODUCT_ARCH.md §8. No change to the
  `flint` CLI itself.
- `v0.15.0` — a portable Claude Code skill (`.claude/skills/flint/`) ships
  in the repo, teaching an agent how to *use* the `flint` CLI to
  scaffold a project — distinct from the `.agents/skills/` catalog
  flint generates *into* projects (§8/§9 elsewhere in this doc), which
  instead teaches an agent about the libraries a generated project
  itself uses. `.gitignore`'s blanket `.claude/` exclusion is narrowed
  to `.claude/*` with a `!.claude/skills/` re-include, since a
  directory-level ignore pattern stops git from even traversing into
  it, so a plain negation of a path underneath it has no effect.
- `v0.16.0` — a third template, `full-stack`, ships for both frameworks
  (`fastapi/full-stack`, `flask/full-stack`): the exact same
  database/ORM/migrations/worker/broker/redis options as `rest-api`,
  server-rendered instead of JSON — Jinja2 templates plus HTMX for
  add/toggle/delete on a Todo list, no client-side JS framework. Built
  by copying each framework's `rest-api` template wholesale and
  replacing only the presentation layer (`schemas.py`/`routes/items.py`
  → a `templates/`+`static/` tree and `routes/todos.py`); the
  docker/worker/redis/migrations layers are reused byte-for-byte (bar
  one `Item`→`Todo` import in each `migrations-*` layer's `env.py`),
  since they're generic infrastructure with no dependency on what the
  app renders. See `PRODUCT_ARCH.md` §4.7 for the mechanic that made
  this safe to build: `templates/`/`static/` files carry no `.jinja`
  suffix, specifically so flint's own generator copies them verbatim
  instead of rendering the *generated app's own* runtime Jinja2 syntax
  (`{% block %}`, `{{ todo.title }}`) through flint's generator and
  stripping it before the file ever reaches the project.
- `v0.17.0` — `full-stack` gains a `css` option (`vanilla`, the
  existing hand-written stylesheet, or `tailwind`): Tailwind CSS v4 via
  its standalone CLI, wrapped by the pip-installable `pytailwindcss` —
  no Node.js/npm anywhere in the generated project, matching the
  "everything through `uv`" story every other template already has.
  Modeled on `litestar-tailwind-cli`'s reference approach (source
  `input.css` in, built `style.css` out, the CLI binary downloaded and
  cached on first run). Implemented as two new layers,
  `css-vanilla`/`css-tailwind`, gated the same way `db-*`/`worker-*`
  already are — the base `files/` layer no longer ships
  `static/css/style.css` directly, since that file's *content* now
  depends on which `css` value was chosen. `--docker` gets one
  conditional `RUN uv run tailwindcss ... --minify` line so a container
  always ships current CSS. Caught during this release, not before
  shipping: `tests/test_main.py.jinja` (shared by every `css` variant)
  had a toggle-endpoint assertion hardcoded to `css-vanilla`'s
  `class="todo-item done"` string — passed under `ast.parse()` but
  failed the instant `uv run pytest` actually ran against a generated
  `css=tailwind` project, since that markup doesn't exist there. Fixed
  by asserting the `checked` attribute instead (present in both
  variants), and both templates' maintainer `README.md` now calls this
  out as a standing rule for `full-stack`'s shared test file. Motivated
  by wanting flint to meet developers where they already are rather
  than impose a single opinion — Tailwind is one of the two dominant
  real-world pairings with server-rendered Jinja2+HTMX Python apps (the
  other being a fully decoupled React/Next.js frontend, deliberately
  out of scope for this release — see §12).
- `v0.17.1` — the `flint` agent skill moves from `.claude/skills/flint/`
  to `.agents/skills/flint/`, a more tool-neutral convention;
  `.claude/skills/flint` becomes a symlink to it so Claude Code's own
  discovery path is unaffected. README rewritten dash-free with a new
  "Project structure" section, and the project description
  (`pyproject.toml`, `mkdocs.yml`) updated to match, dropping the
  `create-next-app` comparison entirely.
- `v0.18.0` — three new `.agents/skills/` catalog entries: `jinja2`,
  `htmx`, `tailwind`, researched against each library's current official
  docs (see PRODUCT_ARCH.md §4.5 for the catalog mechanism, §4.8 for
  `full-stack`'s `css` option this extends). `jinja2`/`htmx` are always
  included for `fastapi/full-stack` and `flask/full-stack`; `tailwind`
  only when `css=tailwind`. Fourteen skills now exist in the catalog.
  Also bumps `full-stack`'s bundled htmx from a stale `2.0.4` to
  `2.0.10` (discovered while researching the `htmx` skill), and fixes
  the `fastapi-full-stack`/`flask-full-stack` docs pages, which had
  claimed an "identical skill set" to `rest-api` — no longer true once
  `full-stack` carries its own presentation-layer skills.
- `v0.19.0` — the project is renamed a fourth time, from **Flint**
  (`flint-kit` on PyPI) to **Brupy**, unifying brand, CLI command, and
  PyPI distribution name under one word this time — unlike `v0.14.0`'s
  `flint`/`flint-kit` split, plain `brupy` came back clean on a direct
  PyPI availability check (no existing project, no edit-distance
  squat-guard collision), so no split was needed. Full sweep: the
  Python package (`src/flint/` → `src/brupy/`), the CLI entrypoint and
  `FlintError`/`FlintUserError` → `BrupyError`/`BrupyUserError`, the
  prefs file (`~/.flint/last.json` → `~/.brupy/last.json`), the
  `.agents/skills/flint/` agent skill (→ `.agents/skills/brupy/`, with
  `.claude/skills/brupy` re-symlinked) and its own now-obsolete
  package/command-mismatch caveat (removed — nothing to warn about once
  they're the same name), every template's `AGENTS.md`/`README.md`/
  `pyproject.toml`, both GitHub Actions workflows
  (`cd.yml`'s PyPI project URL), `mkdocs.yml`, and every doc. Historical
  release notes above (`v0.1.0`–`v0.18.0`) and `CHANGELOG.md` keep their
  original wording rather than being rewritten to say "Brupy"
  retroactively — they're an accurate record of what the project was
  actually called at each point in time, the same reasoning that kept
  `v0.12.0`–`v0.14.0`'s `Conjure`/`Spindle` mentions as-is through the
  previous two renames. Repository rename
  (`abdulazeezoj/flint` → `abdulazeezoj/brupy`) is the user's own
  action, not part of this commit.
- `v0.20.0` — three related additions, all closing the same gap (an
  agent working in a repo not scaffolded by brupy has nothing to go on):
  (1) every generated project gets `CLAUDE.md` (`@AGENTS.md`) and
  `.claude/skills/<id>/` symlinked to each `.agents/skills/<id>/`, so
  Claude Code needs no Claude-specific authoring anywhere (FR13);
  (2) `brupy install-skill` retrofits the portable `brupy` skill itself
  into an existing repo at project or user scope (FR14) — its content
  now ships inside the installed package (`src/brupy/agent_skill/`),
  with this repo's own `.agents/skills/brupy/` a symlink to that same
  directory so there's exactly one copy whether you're reading brupy's
  source or a `pip`/`uv`-installed wheel (see PRODUCT_ARCH.md §2);
  (3) an interactive run prints a one-line "newer version available"
  notice via a best-effort, cached PyPI check (new NFR carve-out, §9).
  Also confirms (no code change, `full-stack` already did this): `css=
  tailwind` uses the standalone Tailwind CLI via `pytailwindcss`, never
  the Tailwind Play CDN `<script>` tag — see §4.8 in PRODUCT_ARCH.md.
- `CHANGELOG.md` is updated in the same commit as any user-facing change,
  and the version is bumped accordingly.

## 12. Open Questions / Risks

- **Package manager choice**: closed as of v0.10 — staying `uv`-only by
  design, not left open. `uv` is fast, single-tool, and every template
  already assumes it end to end (`pyproject.toml`, `uv.lock`, `uv run`,
  `uv sync`); every generated file, README instruction, and `AGENTS.md`/
  skill snippet across both frameworks is written in terms of it.
  Supporting pip/poetry would mean a second (or third) rendering of
  every template's dependency file and install/run instructions, not a
  small addition. Revisit only if there's real demand, not speculatively.
- **Template distribution**: closed as of v0.10 — staying bundled-only
  by design. Templates ship inside the `brupy` package itself: simplest
  possible model, no network dependency to generate a project, and no
  supply-chain exposure from executing a fetched, unreviewed Jinja
  template against the local filesystem. `PRODUCT_ARCH.md` documents
  how the template system stays decoupled enough that a remote/pluggable
  source could be added later without changing `generator.render()`'s
  interface — but it's not planned work, just an option kept open.
- **`AGENTS.md` vs. `.agents/skills/<framework>`**: resolved in v0.9 —
  both ship, as complementary layers rather than a choice between them.
  `AGENTS.md` (since v0.2) stays the always-on, lightweight layer (run/
  test commands, layout, conventions). `.agents/skills/<id>/` (v0.9) is
  the deeper layer: a shared catalog of per-library reference material
  (`SKILL.md`/`references/`/`guides/`), included per project only for
  the libraries it actually uses, with `AGENTS.md` itself pointing at
  whichever apply. See `PRODUCT_ARCH.md` §4.5.
- **Message broker choice for the worker option**: resolved in v0.7 —
  `rest-api` now offers Redis or RabbitMQ as the broker for both Taskiq
  and Celery (`broker` option), decoupled from the standalone `redis`
  caching option. No other brokers are planned; this was specifically
  about not hardcoding Redis as the only option.
- **`ai` template**: removed in v0.3 (was a disabled stub with no
  content). Revisit once there's a clear, minimal shape for it —
  research (see PM/engineering discussion prior to v0.3) pointed at "one
  streaming completion endpoint + `pydantic-settings` for the
  key/model," deliberately smaller than the RAG/agent-framework
  templates common in the wild.
- **Decoupled frontend (React/Next.js + FastAPI/Flask API), deliberately
  deferred, not decided against**: research done ahead of v0.17
  confirmed this is the more common real-world "full-stack Python"
  pairing today than server-rendered Jinja2+HTMX (tiangolo's own
  official `full-stack-fastapi-template` ships exactly this shape:
  React+Vite+Tailwind+shadcn/ui frontend, FastAPI+SQLModel backend, an
  OpenAPI-generated TypeScript client, Docker Compose). v0.17 chose the
  narrower, bounded move instead — a `css` option on the existing
  `full-stack` template — specifically because a decoupled-frontend
  template is a different *project topology* (a `backend/`+`frontend/`
  monorepo, CORS wiring, a generated client), not a new layer on the
  existing one, and warrants its own scoping pass rather than riding
  along with a CSS-tooling change. Revisit as a dedicated effort if
  there's demand.
