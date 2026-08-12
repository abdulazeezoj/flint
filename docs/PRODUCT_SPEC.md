# Flint — Product Spec

**Status:** Draft for v0
**Owner:** Product
**Last updated:** 2026-08-12 (v0.8: Flask enabled — `hello-world` + `rest-api`)

## 1. Vision

Flint is `create-react-app` / `create-next-app` for Python backend frameworks.

One command, a short interactive wizard, and you have a running project —
scaffolded with modern tooling, sane defaults, and zero boilerplate to
hand-write.

```
uvx flint
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
a project grow into what it needs. Flint's answer is a small set of
distinct, opinionated templates, each of which can offer its own
follow-up choices — not one template trying to be everything.

## 3. Terminology: framework, template, option

Three distinct concepts in the wizard — don't conflate them:

- **Framework** — the underlying library, e.g. `fastapi`, `flask`.
  Selected first.
- **Template** — a specific project shape built on that framework, e.g.
  `hello-world`, `rest-api`. Selected second, scoped to the chosen
  framework.
- **Option** — a further, template-specific choice, declared by the
  template itself (not hardcoded in Flint). E.g. `rest-api` asks for a
  database, ORM, whether to add migrations, a background worker, and
  Redis; `hello-world` asks only whether to add `pydantic-settings`
  config. Different templates can declare entirely different options —
  Flint's CLI/wizard code has no built-in knowledge of "database" or
  "worker," it just renders whatever a template's `template.json`
  declares (see `PRODUCT_ARCH.md` §4).

A generated project always comes from exactly one `<framework>/<template>`
pair (e.g. `fastapi/rest-api`) plus whatever options that template offers.
This is what lets the roadmap grow in three independent directions — more
frameworks, more templates per framework, and richer options per
template — without any axis blocking the others.

## 4. Goals — v0

1. Zero-arg interactive wizard: `flint` (or `uvx flint`) prompts for the
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
7. Flint ships as an installable, `pipx`/`uv tool`-friendly CLI.
8. Semantic-ish versioning scheme `v{release}.{feature}.{fixes}`, starting
   at `v0.1.0`, with `CHANGELOG.md` updated on every user-facing change.

## 5. Non-Goals — v0

Explicitly out of scope for the first release (candidates for later
`v0.x` releases — the architecture must not preclude them; several are
already stubbed as disabled/"coming soon" entries so the roadmap is
visible in the wizard):

- Frameworks other than FastAPI and Flask (both are enabled as of v0.8;
  no other framework is stubbed on the roadmap yet, see §11)
- Templates other than `hello-world` and `rest-api`
- A plugin system / third-party or remote templates
- Monorepo or multi-service scaffolding
- Auth scaffolding, Docker Compose, CI workflow templates
- `.agents/skills/<framework>` — see §12 Open Questions
- A GUI or web-based wizard

Database/ORM/migrations/worker selection — a v0.1/v0.2 non-goal — is now
in scope as of v0.3, scoped specifically to the `rest-api` template. A
RabbitMQ broker choice — a v0.1–v0.6 non-goal — is in scope as of v0.7.
Docker Compose was briefly added and then deliberately removed within
v0.7 itself (see §11) — one Dockerfile per template is a reasonable
default, but a generated `docker-compose.yml` bakes in an
opinion about container topology (one service per app) that doesn't
hold for every project shape a generated app might end up living in
(e.g. a monorepo with its own compose setup already).

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
  `flint new my-api --framework fastapi --template rest-api -o database=postgres -o orm=sqlmodel --no-git --no-install --yes`
  and get the identical result with no prompts.
- As a developer deploying to a container, I pass `--docker` and get a
  working `Dockerfile` alongside the app, no Docker knowledge required.
- As a developer, after generation I see a clear "next steps" block (cd,
  run, open browser, plus migration/worker commands if relevant) so I
  never have to guess the run command.
- As a developer, if I mistype something — a bad project name, an
  unknown `--option` key, an invalid option value, a non-empty target
  directory — Flint tells me clearly instead of silently doing the wrong
  thing or half-generating a project.

## 8. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | Interactive wizard order: project name → target directory check → framework → template within that framework → the chosen template's own options, in the order it declares them → add a Dockerfile? (default no) → initialize git repo? (default yes) → install dependencies now? (default yes) |
| FR2 | Validate project name: derive a valid Python package name (snake_case) and a filesystem-safe directory (kebab or snake); refuse to run into a non-empty existing directory without `--force` |
| FR3 | Every prompt has an equivalent flag: `--framework`, `--template`, `--option key=value` (repeatable, for template-specific choices), `--docker/--no-docker`, `--git/--no-git`, `--install/--no-install`, `--yes` (accept all defaults, skip prompts) |
| FR4 | After generation: print a summary of the resolved options, what was created, and the exact next-step commands to run the app (run, migrate, start a worker, `docker build`/`docker run` — whichever apply) |
| FR5 | `flint --version` prints the current version |
| FR6 | Exit codes: `0` success, `1` user/input error (e.g. bad name, existing dir, disabled framework/template, unknown/invalid `--option`), `2` unexpected/internal error |
| FR7 | `--docker` adds a `Dockerfile` and `.dockerignore`; if the chosen template doesn't support it yet, warn and continue rather than failing the whole generation |
| FR8 | Every generated project includes an `AGENTS.md` with run/test commands, layout, and conventions — no flag, always on |
| FR9 | A template's options can depend on each other (e.g. no ORM prompt when "no database" is chosen); an option whose dependency isn't satisfied resolves to a documented value automatically rather than being asked or left unset |
| FR10 | Regardless of which database a project is configured for, its test suite runs against an isolated, ephemeral database and never touches whatever `DATABASE_URL` points at — "just works" out of the box takes priority over exercising the real backend in tests |
| FR11 | After a successful generation, Flint remembers the chosen framework, the chosen template per framework, and — per `<framework>/<template>` — the resolved options plus docker/git/install, in `~/.flint/last.json`. The next run uses these as the new default (both for what the wizard preselects and what a flagless non-interactive run falls back to); an explicit flag or `--option` always overrides a remembered value, and a stale remembered value (no longer valid for the current template) is silently ignored in favor of the template's own default. `--remember/--no-remember` (default on) opts a single run out of reading and writing this file |

## 9. Non-Functional Requirements

- Cross-platform: macOS, Linux, Windows (path handling via `pathlib`, no
  shell-specific assumptions).
- No network access required by Flint itself; only `uv`'s own dependency
  resolution (when the user opts in to "install now") touches the
  network.
- Rich, colorful terminal output where the terminal supports it, with a
  graceful non-interactive fallback: when stdin isn't a TTY, Flint
  requires flags instead of hanging on a prompt.

## 10. Distribution & Naming

- CLI command: `flint`
- PyPI distribution name: `flint-cli` (the plain `flint` name is used by
  an unrelated existing package on PyPI); the installed console script is
  still `flint`, so end-user usage (`uvx flint`, `flint new ...`) is
  unaffected by the distribution name.

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
- `CHANGELOG.md` is updated in the same commit as any user-facing change,
  and the version is bumped accordingly.

## 12. Open Questions / Risks

- **Package manager choice**: v0 hardcodes `uv` rather than letting users
  pick pip/poetry, to keep scope small. Revisit post-v0 if requested.
- **Template distribution**: templates ship bundled inside the `flint`
  package for v0 (simplest, no network dependency). Externalizing to a
  registry/remote-template model is a plausible v0.x/v1 direction, see
  `PRODUCT_ARCH.md` for how the template system is kept decoupled to
  allow this later.
- **`AGENTS.md` vs. `.agents/skills/<framework>`**: `AGENTS.md` ships now
  (since v0.2) — it's a single Jinja file, same mechanism as the README,
  and gives any AI coding agent working in the generated project
  immediate context (run/test commands, layout, conventions).
  `.agents/skills/<framework>` — a directory of framework-specific,
  agent-consumable skills — is a larger bet: it needs real per-framework
  content (not just metadata), a decision on which skill format/consumers
  to target, and is more provable now that `rest-api` gives more surface
  to differentiate against. Tracked as a roadmap item, not committed to
  a release yet.
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
