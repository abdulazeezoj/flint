# Changelog

All notable changes to Brupy are documented here. (Named Flint through
`v0.18.0`; entries below from that era keep their original wording
rather than being rewritten retroactively — see `v0.19.0`.)

Versions follow `v{release}.{feature}.{fixes}` (see
`docs/_product/PRODUCT_SPEC.md` §11): `release` is the major epoch
(starting at `0`), `feature` bumps for new user-facing capability,
`fixes` bumps for patches with no new capability.

## v0.19.0 — 2026-08-17

### Changed

- **Renamed the project from Flint to Brupy** — brand, CLI command
  (`flint` → `brupy`), and PyPI distribution name are now all the same
  word (`flint-kit`'s brand/distribution split is gone; plain `brupy`
  came back available on PyPI with no conflict). `uvx brupy` and `uv
  tool install brupy` both work directly, no `--from` needed. Full
  sweep: the Python package (`src/flint/` → `src/brupy/`),
  `FlintError`/`FlintUserError` → `BrupyError`/`BrupyUserError`, the
  remembered-preferences file (`~/.flint/last.json` →
  `~/.brupy/last.json`), the portable `.agents/skills/flint/` agent
  skill (→ `.agents/skills/brupy/`, `.claude/skills/brupy`
  re-symlinked), every generated template's `AGENTS.md`/`README.md`/
  `pyproject.toml`, both GitHub Actions workflows, `mkdocs.yml`, and
  every doc page. See `docs/_product/PRODUCT_SPEC.md` §10/§11 for the
  full naming history (this is the fourth rename — `Flint` → `Conjure`
  → `Spindle` → `Flint`/`flint-kit` → `Brupy`) and why no PyPI-name
  split was needed this time. Entries below this one keep the name that
  was actually current at each release, not rewritten to say "Brupy."
- GitHub repository rename (`abdulazeezoj/flint` → `abdulazeezoj/brupy`)
  is a separate, user-driven action — not part of this change.

## v0.18.0 — 2026-08-15

### Added

- **Three new `.agents/skills/` catalog entries: `jinja2`, `htmx`,
  `tailwind`** — researched against each library's current official docs
  and grounded in exactly how `full-stack`'s templates use them, not
  generic library reference material. `jinja2` and `htmx` are always
  included for `fastapi/full-stack` and `flask/full-stack` (template
  inheritance/includes/autoescaping/whitespace for the former;
  hx-target/hx-swap/hx-trigger and the `hx-swap-oob` empty-state trick
  for the latter, including the fact that this project's 4xx/5xx
  responses aren't swapped by htmx's own default). `tailwind` is added
  only when `css=tailwind`, covering the `@theme` CSS-first config and
  the standalone-CLI build step. Fourteen skills now exist in the
  catalog; see the [Agent Skills](https://abdulazeezoj.github.io/flint/agent-skills/)
  docs for the full table.

### Changed

- **`full-stack`'s bundled htmx bumped from 2.0.4 to 2.0.10**
  (`templates/base.html`'s `<script>` tag), and its CDN switched from
  `unpkg.com` to `cdn.jsdelivr.net/npm/htmx.org@.../dist/htmx.min.js` —
  the version had drifted stale since the template first shipped, and
  the new `htmx` skill documents the exact URL to bump it at next time.
- The `fastapi-full-stack`/`flask-full-stack` docs pages' `.agents/skills/`
  section no longer claims an "identical skill set" to `rest-api` — that
  stopped being true the moment `jinja2`/`htmx` (and conditionally
  `tailwind`) were added; it now lists the two/three skills `full-stack`
  adds on top of `rest-api`'s set.

## v0.17.1 — 2026-08-15

### Changed

- **The `flint` agent skill moves from `.claude/skills/flint/` to
  `.agents/skills/flint/`, with `.claude/skills/flint` kept as a
  symlink** (`.claude/skills/flint -> ../../.agents/skills/flint`) so
  Claude Code's own discovery path still finds it. `.agents/skills/` is
  the more tool-neutral convention, and the symlink means both paths
  resolve to the same content with nothing to keep in sync by hand.
  Content unchanged.
- **README rewritten**: no more em/en dashes, and the opening tagline
  now matches the project description used everywhere else ("Strike a
  spark, get a running project. Instant scaffolding for popular
  unopinionated Python web frameworks..."), dropping the earlier
  `create-next-app` comparison entirely. Also adds a new "Project
  structure" section showing the generated layout directly in the
  README, not just linked out to the docs site.
- `pyproject.toml`'s `description` and `mkdocs.yml`'s `site_description`
  updated to the same tagline, also dash-free.

## v0.17.0 — 2026-08-14

### Added

- **`full-stack` gains a `css` option: `vanilla` (the existing
  hand-written stylesheet, unchanged, still the default) or `tailwind`
  — Tailwind CSS v4 via its standalone CLI, wrapped by the
  pip-installable `pytailwindcss`.** No Node.js or npm anywhere in the
  generated project, matching every other template's "everything
  through `uv`" story. `css=tailwind` ships `static/css/input.css`
  (the source, tracked — a few lines: `@import "tailwindcss"` plus an
  `@theme` block for the accent color, Tailwind v4's CSS-first config)
  and rewrites `templates/index.html` and
  `templates/partials/{todo_item,empty_state}.html` to use Tailwind
  utility classes; `static/css/style.css` becomes a git-ignored build
  artifact, produced by `uv run tailwindcss -i .../input.css -o
  .../style.css` (documented in the generated `README.md`'s new
  "Styling" section — a freshly generated `css=tailwind` project has no
  styling until that command runs once, the same "one required setup
  step" shape `migrations=true` already has). `--docker` runs the build
  automatically as part of the image. Implemented as two new peer
  layers, `css-vanilla`/`css-tailwind`, replacing what used to be a
  fixed `static/css/style.css` in the base `files/` layer. See
  `docs/_product/PRODUCT_ARCH.md` §4.8 for the full design writeup,
  including a real bug this release caught: a shared test file had a
  toggle-endpoint assertion hardcoded to `css-vanilla`'s CSS class name,
  which only failed when actually run against a generated
  `css=tailwind` project — fixed to assert behavior (`checked`), not
  presentation.

## v0.16.0 — 2026-08-14

### Added

- **A third template: `full-stack`, for both FastAPI and Flask.** Same
  layered options as `rest-api` (database, ORM, migrations, background
  worker, broker, Redis caching) — the only thing that changes is what
  a route returns. `rest-api` returns JSON; `full-stack` returns
  server-rendered HTML: a Jinja2 page for `GET /`, and an HTML fragment
  (swapped in via [HTMX](https://htmx.org), no page reload, no
  client-side JS framework) for every state-changing request. Ships
  with a Todo list — add, toggle, delete — as the example resource,
  including an out-of-band HTMX swap that clears/restores the
  "nothing to do yet" message at the right moments.
  `docker`/`worker-*`/`redis`/`migrations-*` layers are reused
  byte-for-byte from `rest-api`, since they're generic infrastructure
  with no dependency on what the app renders. `templates/*.html` and
  `static/css/style.css` deliberately carry no `.jinja` suffix — they
  hold Jinja2 syntax meant for the *generated app's own* runtime
  template engine, and a `.jinja` suffix would make flint's own
  generator render (and silently strip) that syntax at generation time
  instead. See `docs/_product/PRODUCT_ARCH.md` §4.7 for the full
  mechanic, and the new `docs/project-templates/fastapi-full-stack.md`
  / `flask-full-stack.md` pages for usage.

## v0.15.0 — 2026-08-14

### Added

- **A Claude Code skill teaching an agent how to *use* flint itself**
  (`.claude/skills/flint/`). Separate from — and unrelated to — the
  `.agents/skills/` catalog flint bundles into *generated* projects
  (which teaches an agent about the libraries a generated project uses,
  like FastAPI or SQLModel); this new skill instead covers invoking the
  `flint` CLI to scaffold a project in the first place: the
  `uvx --from flint-kit flint ...` gotcha, the framework/template/option
  decision process, and a full CLI/options reference split into
  `references/cli-reference.md` and `references/templates.md`. Every
  example command in it was live-verified, including against the real
  published `flint-kit` PyPI package.
- `.gitignore` now carves out `.claude/skills/` from the otherwise-blanket
  `.claude/` ignore rule, so this shared skill can actually be committed
  and distributed with the repo (everything else under `.claude/` — local
  tool state, agent worktrees — stays ignored).

## v0.14.3 — 2026-08-13

### Changed

- **The flint → spark → fire metaphor now runs through the project's
  descriptions.** `pyproject.toml`'s `description` (shown on the PyPI
  listing), `mkdocs.yml`'s `site_description`, `README.md`'s opening
  line, and the `flint --help` header all now lead with "strike a
  spark" / "throws a spark" framing, echoing `docs/index.md`'s "Why
  Flint" section. Copy only — no behavior change.

## v0.14.2 — 2026-08-13

### Fixed

- **`v0.14.1`'s release automation tagged correctly but never actually
  published** — PyPI rejected the upload with `400 Invalid attestations
  supplied during upload`. Root cause: `release.yml` called `cd.yml`
  directly via `workflow_call`, and PyPI's Trusted Publishing OIDC
  verification checks the *top-level* workflow that actually ran, not
  any reusable workflow it calls — so the certificate said `release.yml`
  while the registered Trusted Publisher expects `cd.yml`, and PyPI
  correctly refused the mismatch. Fixed by switching `cd.yml` from
  `workflow_call` to a `workflow_run` trigger (`workflows: ["Release"]`)
  instead: `cd.yml` now runs as its own genuinely top-level workflow
  when `release.yml` finishes, matching what's registered on PyPI.
  Since there's no `workflow_call` `ref` input to rely on anymore, the
  "does this commit's tag match `pyproject.toml`" safety check now uses
  `git describe --tags --exact-match HEAD` (with `fetch-depth: 0` so the
  tag is actually present locally) instead of parsing the triggering
  ref — this works identically whether `cd.yml` was triggered by a
  direct tag push or by `release.yml` finishing.

## v0.14.1 — 2026-08-13

### Added

- **`.github/workflows/release.yml`: tags releases automatically**
  (its `workflow_call` chaining into `cd.yml` turned out to break PyPI's
  Trusted Publishing verification — never actually published under this
  version; fixed in `v0.14.2`). Fires
  on any push to `main` that touches `pyproject.toml`; reads the version,
  and — if `vX.Y.Z` doesn't already exist as a tag — creates and pushes
  it using the workflow's own `GITHUB_TOKEN`. Exists because a plain
  `git tag && git push` from outside GitHub Actions can hit a 403: this
  repo's tag-protection rule only allows tag creation from a context
  with the right permissions, which an external git credential may not
  have even when it can push ordinary branch commits fine. Chains
  straight into `cd.yml` as a reusable workflow (`workflow_call`, not a
  second tag-push event) rather than relying on the tag push to
  re-trigger `cd.yml` — GitHub explicitly suppresses new workflow runs
  triggered by the default `GITHUB_TOKEN`, so a plain tag push from this
  workflow would silently never fire the publish job. `cd.yml` gained a
  `workflow_call` trigger and an optional `ref` input so both entry
  points (a real tag push, and this workflow's direct call) share the
  same test-then-publish logic. End state: merging a version-bump PR is
  now the only manual step in a release — tagging and publishing happen
  on their own. No change to the `flint` CLI itself.

## v0.14.0 — 2026-08-13

### Changed

- **Project renamed a third time — back to `flint`, this time with a
  split brand/distribution name.** `spindle` (see `v0.13.0`) turned out
  to already be a published, unrelated PyPI package (a classical-magnetism
  library) — a real collision the plain-availability check couldn't have
  caught any earlier, since it's a straightforward already-taken name,
  not a similarity/squat-guard block. A ~300-candidate sweep across a
  dozen semantic domains (craft/tool words, birds, mythology, whimsical
  animals, food, invented syllables, 2–3 letter abbreviations) turned up
  essentially nothing both short and clean: PyPI's namespace for
  short, pronounceable English words is almost entirely pre-claimed.
  Rather than keep hunting for an available bare word, this settles the
  question with the pattern real projects actually use when the bare
  name isn't available — e.g. GitHub's own `spec-kit` ships on PyPI as
  `specify-cli` while the command is `specify`; the web framework Sillo
  ships as `sillo-framework` while the brand and command are `sillo`.
  Same here: **brand and command are `flint`** (reverting the
  `spindle`→`flint` half of `v0.13.0`'s rename — package, CLI,
  `~/.spindle/last.json` → `~/.flint/last.json`, generated-project
  attribution, all docs), while **the PyPI distribution name is
  `flint-kit`**, since plain `flint` is a real, unrelated, already-
  published package (a Fortran analysis tool) and `flint-cli` also
  turned out to be taken (an unrelated data-connector CLI). Because the
  distribution and command names now differ, `uvx flint` alone won't
  resolve correctly — the ephemeral-run form is `uvx --from flint-kit
  flint`, same shape as `uvx --from httpie http`. `uv tool install
  flint-kit` needs no such adjustment; it installs the `flint` console
  script under its own name regardless of the distribution name. The
  GitHub repository is also renamed back, `abdulazeezoj/spindle` →
  `abdulazeezoj/flint` — the third rename of that slug this project has
  been through in one day.

## v0.13.0 — 2026-08-13

### Changed

- **Project renamed again, to `spindle`.** `conjure` cleared a plain
  availability check but PyPI's project-creation flow rejected it
  outright — separate from "is it taken," PyPI blocks new names within
  edit-distance 2 of an existing project to deter typosquatting, and
  `conjure` is one character from `conjur` (CyberArk's published
  secrets-management package). That block only surfaces when actually
  registering a name (via the trusted-publisher form), not from a plain
  `pypi.org/pypi/<name>/json` check, so the original ~80-candidate sweep
  never caught it. `spindle` passed PyPI's real registration flow
  cleanly and has no similar near-miss. Same scope as the `flint`→
  `conjure` rename: package, CLI, `~/.conjure/last.json` →
  `~/.spindle/last.json`, generated-project attribution, all docs, and
  this time the GitHub repository itself too
  (`abdulazeezoj/flint` → `abdulazeezoj/spindle`). (Superseded one
  release later — see `v0.14.0`: `spindle` turned out to already be a
  real, unrelated published package, a plain collision the earlier
  check should have — and, in hindsight, easily could have — caught.)

## v0.12.0 — 2026-08-13

### Changed

- **Project name finalized as `conjure`.** Confirmed available and
  unclaimed on PyPI, pronounceable, and free of collisions with
  established tools — locked in before any release ever publishes under
  it. The PyPI distribution name and the `conjure` console script are
  the same string; no `-cli` suffix, no alias to remember. (Superseded
  one release later — see v0.13.0.)
- **Two docs-site rendering bugs, fixed and verified visually.** The
  homepage's "Where to go next" card grid was rendering as raw,
  unprocessed markdown — `mkdocs.yml` was missing the `attr_list` and
  `md_in_html` extensions Material's grid-cards recipe requires (see
  PRODUCT_ARCH.md §4.6). Separately, `mkdocs.yml`'s `repo_name` pointed
  at the wrong slug. Neither broke `mkdocs build --strict`, which checks
  structure, not rendered output — both were only caught by an actual
  Playwright visual pass across all 11 pages in both light and dark
  themes, which is now how this site gets QA'd, not just build-checked.
- **Editorial pass across all 11 docs pages** — tightened flat/listy
  prose, fixed passive voice, and sharpened section openings for rhythm
  and directness, without changing any code block, table, link, or
  heading.

## v0.11.0 — 2026-08-13

### Added

- **A public documentation site** at
  [abdulazeezoj.github.io/spindle](https://abdulazeezoj.github.io/spindle/)
  (MkDocs, Material theme, deployed via `.github/workflows/docs.yml`
  on every push to `main` that touches `docs/**`): a Getting Started
  guide, a full CLI reference, one page per template (options,
  generated layout, real gotchas), the `.agents/skills/` catalog
  explained, remembered preferences, and a contributing guide.
  Requires a one-time repo setting (Settings → Pages → Source: "GitHub
  Actions") to go live.

### Changed

- **The internal product-decision docs moved to `docs/_product/`.**
  `docs/PRODUCT_SPEC.md`/`PRODUCT_FLOW.md`/`PRODUCT_ARCH.md` — which
  guide development direction, not end users — are now under
  `docs/_product/`, fully excluded from the built docs site
  (`mkdocs.yml`'s `exclude_docs`, not just unlisted from nav) while
  staying in the same repo tree next to the code they describe. Fixed
  the resulting links in `README.md`/`CHANGELOG.md` (only the actual
  markdown links and current-state prose — historical CHANGELOG
  entries and bare-filename citations in code docstrings are left
  as-is, since those remain valid regardless of which folder the file
  lives in).
- **`README.md` is trimmed back to a front door** — install, a quick
  example, and links out to the new docs site — now that the detailed
  per-template options/CLI-flag/contributing content lives there
  instead, with real depth a README isn't the right place for.

## v0.10.1 — 2026-08-13

### Added

- **CI/CD via GitHub Actions.** `.github/workflows/ci.yml` runs on every
  push to `main` and every PR: `uv sync --locked`, the full test suite
  (`uv run pytest`, same 100%-coverage gate as local development), and
  a smoke check that the installed console script runs. `.github/
  workflows/cd.yml` fires on pushing a `v*` tag: re-runs the same test
  gate, verifies the tag's version matches `pyproject.toml` (refuses to
  publish on a mismatch), builds via `uv build`, and publishes to PyPI
  using Trusted Publishing (OIDC) — no API token stored as a repo
  secret. Publishing requires a one-time PyPI-side setup (see
  PRODUCT_ARCH.md §8 for exactly what to register). No change to the
  `flint` CLI itself — this is release infrastructure only.

## v0.10.0 — 2026-08-13

### Added

- **Interactive `--force` overwrite confirmation.** Running into a
  non-empty target directory without `--force` used to hard-error
  unconditionally. Now, in interactive mode, Flint asks "Directory 'x'
  already exists and is not empty. Overwrite?" instead of failing
  outright — confirming proceeds exactly as `--force` would have,
  declining aborts cleanly with no files written. Non-interactive runs
  (`--yes`/piped stdin/CI) are unchanged: no prompt, same hard error
  unless `--force` was already passed.
- **`flint list-templates`**: a new introspection command listing every
  framework/template pair — label, description, whether it supports
  `--docker` — including disabled/"coming soon" entries, so the roadmap
  stays visible outside the wizard too. Generates nothing.

### Changed

- **Package manager and template distribution are formally closed, not
  left open.** Both were long-standing "Open Questions" in
  PRODUCT_SPEC.md §12 with no code changes attached. Flint stays
  `uv`-only (every template's `pyproject.toml`/README/`AGENTS.md`/skill
  already assumes it end to end — supporting pip/poetry would mean a
  second rendering of every template, not a small addition) and
  bundled-templates-only (no remote/git-based sources — simplest model,
  no network dependency, no supply-chain exposure from executing a
  fetched Jinja template). Neither is a capability change; this just
  documents that they were decided, not forgotten.

## v0.9.0 — 2026-08-13

### Added

- **`.agents/skills/<id>/` — a shared, opt-in catalog of deeper agent
  reference material.** Beyond the always-on, lightweight `AGENTS.md`,
  every generated project now also gets `.agents/skills/<id>/` for
  each library it actually uses — a `SKILL.md`, `references/*.md`, and
  `guides/*.md` per library, plus a generated `.agents/skills/README.md`
  index and an `AGENTS.md` section pointing at whichever skills apply.
  Eleven skills ship: `fastapi`, `flask`, `pydantic-settings`,
  `sqlmodel`, `sqlalchemy` (covers both FastAPI's async and Flask's
  sync usage), `flask-sqlalchemy`, `alembic`, `flask-migrate`,
  `taskiq`, `celery`, `redis`, `pytest`. Selection is declarative — a
  new `skills` list in `template.json`, gated by the exact same `id`/
  `when` shape `layers` already use — and the catalog lives once, flat,
  at `src/flint/skills/<id>/`, decoupled from any one framework/
  template so a skill used by both (e.g. `pytest`, `redis`) isn't
  duplicated. Rendered through the same Jinja mechanism as everything
  else, so skill content gets real `{{ package_name }}` substitution
  and can branch on resolved options (e.g. the shared `sqlalchemy`
  skill reads async-first for a FastAPI project, sync-first for a
  Flask one). Every real gotcha already recorded in `PRODUCT_ARCH.md`
  §7.1 is folded into the relevant skill's `references/gotchas.md`
  (task-discovery for taskiq/celery, `create_all()`-vs-migrations for
  alembic/flask-migrate/flask-sqlalchemy/sqlalchemy, the
  app-factory-avoids-import-time-DB-connection bug for flask).
  Live-verified end-to-end across both frameworks and a range of
  option combinations: correct skill selection, correct `.env`-style
  `package_name` substitution, no leftover template syntax, and a real
  `uv sync && uv run pytest` pass on the generated output.

## v0.8.1 — 2026-08-12

### Fixed

- **`rest-api`: migrations were decorative in both frameworks.**
  `init_db()`/`create_app()` called `create_all()` on every app boot
  regardless of the `migrations` option, so by the time `alembic
  revision --autogenerate`/`flask db migrate` ran, the tables already
  existed (created outside migration history) and matched the models
  exactly — autogenerate always reported "No changes in schema
  detected" instead of generating a real migration. Fixed by making the
  eager `create_all()` conditional on `migrations`: FastAPI's `rest-api`
  no longer calls `init_db()` at all when `migrations` is enabled
  (schema comes solely from `alembic upgrade head`); Flask's `rest-api`
  only auto-creates the schema for the isolated in-memory test database.
  Verified live end-to-end: `alembic revision --autogenerate`/`flask db
  migrate` now correctly detects and generates the initial `item`/
  `items` table for all four database/ORM combinations (FastAPI
  SQLModel + SQLAlchemy, Flask Flask-SQLAlchemy + SQLAlchemy), and
  `alembic upgrade head`/`flask db upgrade` applies cleanly against a
  real on-disk SQLite database. Both frameworks' generated README.md now
  correctly say the database is **not** auto-created on startup when
  migrations are enabled. This bug predates Flask — it was present in
  `fastapi/rest-api` since migrations shipped in `v0.3.0` — and is fixed
  in both places by this release.

## v0.8.0 — 2026-08-12

### Added

- **Flask is enabled as a second framework**, with both templates
  live-verified end-to-end:
  - **`flask/hello-world`** — the same shape as `fastapi/hello-world`,
    on a WSGI `Flask(__name__)` app. `-o config=true` and `--docker`
    behave identically.
  - **`flask/rest-api`** — the sync counterpart to `fastapi/rest-api`:
    `database` (none/sqlite/postgres), `orm`
    (flask-sqlalchemy/sqlalchemy), `migrations` (Flask-Migrate for
    flask-sqlalchemy, bare Alembic for sqlalchemy), `worker`
    (none/celery — Taskiq is async-first and doesn't fit Flask's sync
    model, so it's FastAPI-exclusive), `broker` (redis/rabbitmq), and
    `redis` (caching, independent of `broker` — same decoupling as
    `fastapi/rest-api`). Built on an application-factory pattern
    (`create_app()`, never instantiated at module scope), so importing
    the app module — which `pytest`/`flask db ...`/`alembic` all do —
    never opens a connection to the configured production database.
- **Per-framework `run_command`**: each framework's `template.json` now
  declares its own dev-server command, so the generated project's "Next
  steps" line prints the right one (`uv run flask --app
  src/{package}/main.py run` vs. `uv run fastapi dev
  src/{package}/main.py`) instead of always assuming FastAPI.

## v0.7.0 — 2026-08-12

### Added

- **`rest-api`: RabbitMQ as a message broker choice.** New `broker`
  option (`redis`/`rabbitmq`, default `redis`), asked whenever a worker
  is chosen. `redis` (the caching add-on) is now a fully independent
  question — previously it was always implied the moment *any* worker
  was picked, which conflated "a worker exists" with "the worker uses
  Redis." Now it's implied only when `broker == "redis"`; picking
  RabbitMQ leaves the standalone Redis-for-caching question open.
  Verified live end-to-end: real Taskiq (`taskiq-aio-pika`) and real
  Celery (built-in AMQP transport + `rpc://` result backend) against a
  real RabbitMQ broker, enqueue → execute round trip on both.
- **`.env.example`**: wherever a template writes a `.env` (`rest-api`
  always; `hello-world` with `-o config=true`), a `.env.example` with
  identical content is written alongside it — `.env` stays git-ignored,
  `.env.example` is the checked-in reference of what vars exist.

### Changed

- **Breaking (pre-1.0):** the `django` framework stub is removed from
  the roadmap entirely (it was always a disabled "coming soon" stub with
  no content). Flask remains the next committed framework — this isn't
  a scope increase, just dropping a placeholder that was never going to
  ship.

## v0.6.0 — 2026-08-12

### Changed

- **Breaking (pre-1.0):** the `restapi` template is renamed to
  `rest-api`, to match the hyphenated id style used elsewhere (e.g.
  `hello-world`) instead of being the odd one out. `--template restapi`
  is no longer recognized — use `--template rest-api`. Anything already
  remembered in `~/.flint/last.json` under the old `fastapi/restapi` key
  (§ v0.5.0) is simply never looked up again under the new id and falls
  back to the template's own defaults, same as any other stale entry —
  no manual migration needed.

## v0.5.0 — 2026-08-12

### Added

- **Remembered preferences** (`~/.flint/last.json`): after a successful
  generation, Flint saves the last framework, the last template picked
  per framework, and — per `<framework>/<template>` — the resolved
  options plus `docker`/`git`/`install`. The next run uses these as the
  new default: the interactive wizard preselects them, and a flagless
  `--yes`/non-TTY run falls back to them instead of the template's own
  hardcoded defaults. An explicit flag or `--option` always wins
  regardless of what's remembered, and a stale remembered value (a
  choice no longer valid for the current template) is silently ignored
  in favor of the template's own default rather than erroring.
- `--remember/--no-remember` flag (default on) to opt a single run out
  of both reading and writing `~/.flint/last.json` — for anyone who
  wants a fully stateless run.

### Changed

- Reading/writing `~/.flint/last.json` is entirely best-effort: a
  missing, corrupt, or unwritable prefs file never fails or warns during
  generation — it's silently treated as "nothing remembered yet."

## v0.4.0 — 2026-08-12

### Changed

**Breaking (pre-1.0):** the `restapi` template's generated project
layout is now opinionated, borrowed from how Next.js only enforces
structure for routing and leaves everything else as convention:

- `main.py` / `worker.py` — fixed-name entrypoints (unchanged in
  spirit, now documented as load-bearing rather than incidental).
- `routes/` / `tasks/` — "one module per resource/job" folders. Worker
  tasks moved from a single `tasks.py` to a `tasks/` package
  (`tasks/example.py` for the demo task) so a project can grow the same
  way `routes/` already does.
- `core/` — shared infrastructure, now including the database
  session/engine: `core/db.py` (was `db/session.py`). `core/config.py`
  and `core/redis.py` already lived here and are unchanged.
- `models.py` — ORM models moved to a top-level file (was
  `db/models.py`); deliberately **not** under `core/`, since domain
  models aren't cross-cutting infrastructure the way config/db-session/
  redis-client are — see `docs/PRODUCT_ARCH.md` §4.4 for the full
  reasoning. `schemas.py` (already top-level) is unaffected.
- `hello-world`'s optional `config` option follows suit:
  `core/config.py` instead of a top-level `config.py`, for consistency
  across templates.

No CLI-facing behavior changed — same flags, same `--option` keys, same
prompts. Only the shape of what gets generated.

### Fixed

- Re-verified live end-to-end after the restructure (real Alembic
  migrations against SQLite and PostgreSQL, real Taskiq and Celery
  workers against real Redis) and caught a template gap along the way:
  the Celery worker layer was missing its actual task file
  (`tasks/example.py`) — present for Taskiq, not for Celery. Fixed.

## v0.3.0 — 2026-08-12

### Added

- **Per-template options**: a template can now declare its own
  interactive prompts in `template.json` (`select`/`confirm`, with
  dependency-aware `when`/`skip_value` gating), resolved by
  `prompts.prompt_template_options` and surfaced non-interactively via
  a new repeatable `--option`/`-o key=value` flag. `generator.py`'s
  layer mechanism (previously hardcoded to `--docker`) is now equally
  data-driven — `--docker` is one gated layer among others.
- **`fastapi/restapi` template** — no longer a disabled stub. A layered
  REST API with `pydantic-settings` config always on, plus:
  - `database`: none (in-memory) / SQLite / PostgreSQL
  - `orm`: SQLModel / SQLAlchemy (skipped, no DB → no ORM prompt)
  - `migrations`: Alembic, async, autogenerate-ready (skipped without a DB)
  - `worker`: none / Taskiq / Celery, with a demo `/tasks/add` endpoint
  - `redis`: async client; implied automatically the moment a worker is chosen
  - Tests always run against an isolated, ephemeral SQLite database
    regardless of the configured production database — no external
    service needed to run `pytest`.
  - Verified live end-to-end: real PostgreSQL migrations and CRUD, real
    Taskiq and Celery workers against real Redis (enqueue → execute),
    and a working `docker build`/`docker run`.
- **`fastapi/hello-world` gains an optional `config` option**
  (`-o config=true` or the wizard prompt, default off): adds
  `pydantic-settings`-based configuration (`config.py`, `.env`) without
  changing the template's default zero-config shape.

### Changed

- **Breaking (pre-1.0):** the `ai` template (a disabled stub with no
  content) is removed. Revisit later with a deliberately small shape —
  one streaming completion endpoint + `pydantic-settings` for the
  provider key/model — rather than the RAG/agent-framework scope common
  in comparable tools.
- `generator._env` now sets `trim_blocks=True, lstrip_blocks=True`,
  simplifying every template's conditional blocks (no more manual
  `{%- -%}` trimming) — fixes whitespace bugs this surfaced in
  `hello-world`'s existing templates along the way.

### Fixed

Bugs caught only by actually running the generated tooling (not by
`uv sync && pytest` alone) — see `docs/PRODUCT_ARCH.md` §6.1 for the
full write-up of why each was invisible to lighter checks:

- restapi's `files/` layer was missing the top-level package
  `__init__.py`, which broke `fastapi dev`/`fastapi run`'s own
  directory-detection (namespace packages masked it for plain imports
  and pytest, but not for `fastapi_cli`).
- Alembic's `prepend_sys_path` needed to be `src`, not the default `.`,
  for a `src/`-layout project — otherwise `alembic revision
  --autogenerate` can't import the app's models.
- Taskiq/Celery workers pointed at `worker.py` never discovered tasks
  registered in `tasks.py` unless something imported it — fixed by
  importing `tasks` at the bottom of `worker.py`.
- `aiosqlite` was only a production dependency when `database ==
  "sqlite"`, but restapi's tests always use SQLite for isolation
  regardless of the configured database — a `database=postgres` project
  couldn't run its own test suite until `aiosqlite` became an
  unconditional dev dependency whenever a database is configured.

## v0.2.1 — 2026-08-12

### Fixed

- `generator.render` now rolls back a partially-written target directory
  when a `FlintError` (not just any other exception) is raised mid-render
  — previously that branch re-raised without cleaning up, breaking the
  documented all-or-nothing generation guarantee. Currently unreachable
  via any real input, but would have mattered the moment a future layer
  hook raised one.

### Changed

- Test suite now enforces 100% statement + branch coverage
  (`--cov-fail-under=100` in `pyproject.toml`, branch coverage on) —
  every module in `src/flint/` is fully covered, including the
  `python -m flint` entry points, `git`/`uv` subprocess failure paths,
  and every prompt cancellation branch.

## v0.2.0 — 2026-08-12

### Added

- `--docker/--no-docker` flag (and matching wizard prompt, default off):
  adds a `Dockerfile` and `.dockerignore` to the generated project. The
  `fastapi/hello-world` template's generated README gains a Docker
  section when used; the CLI summary prints `docker build`/`docker run`
  next steps.
- Every generated project now includes `AGENTS.md` — run/test commands,
  layout, and conventions for AI coding agents working in the repo.
  Always on, no flag.
- `templates/fastapi/hello-world/README.md` — maintainer docs for the
  template itself (not shipped to generated projects).

### Changed

- **Breaking (pre-1.0):** templates are now addressed as
  `--framework <id> --template <id>` (e.g. `--framework fastapi
  --template hello-world`) instead of a single combined
  `--framework fastapi-hello-world`. The wizard now asks framework and
  template as two separate steps. `restapi` and `ai` are listed as
  disabled ("coming soon") templates under `fastapi`; `flask` and
  `django` are listed as disabled frameworks — signaling the template
  roadmap the same way disabled frameworks already did.

## v0.1.0 — 2026-08-12

First release. `flint` scaffolds a runnable project from a short
interactive wizard, in the spirit of `create-react-app`/`create-next-app`.

### Added

- `flint` / `flint new [NAME]` — interactive wizard: project name,
  framework, git init, dependency install.
- Fully non-interactive mode via `--framework`, `--git/--no-git`,
  `--install/--no-install`, `--yes`, and `--force`; auto-detected when
  stdin isn't a TTY.
- `fastapi-hello-world` template: a `uv`-managed, `src/`-layout FastAPI
  project with a passing `pytest` test, ready to run with
  `uv run fastapi dev src/<package>/main.py`.
- `flint --version`.
- Project name validation: derives a filesystem-safe slug and a valid,
  importable Python package name; rejects empty/keyword/stdlib-shadowing
  names instead of silently mutating them.
- All-or-nothing generation: a failure mid-render rolls back any
  partially-written target directory.
- `docs/PRODUCT_SPEC.md`, `docs/PRODUCT_FLOW.md`, `docs/PRODUCT_ARCH.md`.
