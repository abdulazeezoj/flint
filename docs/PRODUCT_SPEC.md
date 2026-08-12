# Flint — Product Spec

**Status:** Draft for v0
**Owner:** Product
**Last updated:** 2026-08-12 (v0.2: framework/template split, `--docker`, AGENTS.md)

## 1. Vision

Flint is `create-react-app` / `create-next-app` for Python backend frameworks.

One command, a short interactive wizard, and you have a running project —
scaffolded with modern tooling, sane defaults, and zero boilerplate to
hand-write.

```
uvx flint
```

...and 60 seconds later you're looking at `Hello, World!` from a real,
runnable FastAPI app.

## 2. Problem

Every new FastAPI/Flask/etc. project starts with the same repetitive setup:
`pyproject.toml`, virtual env, src layout, a first endpoint, a test, a
`.gitignore`, a README nobody writes. Developers either copy an old project
(and drag its cruft along) or start from a blank folder every time.

The JS ecosystem solved this years ago (`create-react-app`,
`create-next-app`, `create-vite`) with a single interactive command that
gets you to running code immediately. Python has no equivalent with that
UX. The nearest tools (`cookiecutter`, `copier`) require finding and
trusting a third-party template repo, are template-authoring frameworks
rather than finished products, and have no polished interactive prompt
flow out of the box.

## 3. Terminology: framework vs. template

Two distinct, nested choices in the wizard — don't conflate them:

- **Framework** — the underlying library, e.g. `fastapi`, `flask`,
  `django`. Selected first.
- **Template** — a specific project shape built on that framework, e.g.
  `hello-world`, `restapi`, `ai`. Selected second, scoped to the chosen
  framework.

A generated project always comes from exactly one `<framework>/<template>`
pair (e.g. `fastapi/hello-world`). This is what lets the roadmap grow in
two independent directions — more frameworks, and more templates per
framework — without either axis blocking the other.

## 4. Goals — v0

1. Zero-arg interactive wizard: `flint` (or `uvx flint`) prompts for the
   handful of decisions that matter and generates a project.
2. The wizard produces a runnable "Hello World" FastAPI app in under 60
   seconds (excluding dependency download time), managed by `uv`.
3. A fully non-interactive mode via flags, for scripting and CI.
4. The generated project includes: `src/` layout package, `uv`-managed
   `pyproject.toml`, a README with run instructions, `AGENTS.md` (context
   for AI coding agents), `.gitignore`, and a passing `pytest` test — with
   no manual edits required to run it.
5. Optionally, a generated `Dockerfile`/`.dockerignore` via `--docker`.
6. Flint ships as an installable, `pipx`/`uv tool`-friendly CLI.
7. Semantic-ish versioning scheme `v{release}.{feature}.{fixes}`, starting
   at `v0.1.0`, with `CHANGELOG.md` updated on every user-facing change.

## 5. Non-Goals — v0

Explicitly out of scope for the first release (candidates for later
`v0.x` releases — the architecture must not preclude them; several are
already stubbed as disabled/"coming soon" entries so the roadmap is
visible in the wizard):

- Frameworks other than FastAPI (Flask, Django are stubbed disabled)
- Templates other than `hello-world` (`restapi`, `ai` are stubbed
  disabled under `fastapi`)
- A plugin system / third-party or remote templates
- Monorepo or multi-service scaffolding
- Database/ORM selection, auth scaffolding, Docker Compose, CI workflow
  templates
- `.agents/skills/<framework>` — see §12 Open Questions
- A GUI or web-based wizard

## 6. Personas

- **Solo/side-project developer** — wants to skip boilerplate and get to
  writing actual endpoints.
- **Team lead standardizing scaffolding** — wants every new internal
  service to start from the same shape, scriptable in automation.

## 7. User Stories

- As a developer, I run one command, answer a few short prompts, and get a
  working FastAPI app I can `uv run` immediately — no follow-up edits.
- As a developer working in CI/scripts, I run
  `flint new my-api --framework fastapi --template hello-world --no-git --no-install --yes`
  and get the identical result with no prompts.
- As a developer deploying to a container, I pass `--docker` and get a
  working `Dockerfile` alongside the app, no Docker knowledge required.
- As a developer, after generation I see a clear "next steps" block (cd,
  run, open browser) so I never have to guess the run command.
- As a developer, if I mistype something or the target directory already
  has files in it, Flint tells me clearly instead of silently
  overwriting or half-generating a project.

## 8. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | Interactive wizard order: project name → target directory check → framework (v0: FastAPI enabled, others listed disabled) → template within that framework (v0: Hello World enabled, others listed disabled) → add a Dockerfile? (default no) → initialize git repo? (default yes) → install dependencies now? (default yes) |
| FR2 | Validate project name: derive a valid Python package name (snake_case) and a filesystem-safe directory (kebab or snake); refuse to run into a non-empty existing directory without `--force` |
| FR3 | Every prompt has an equivalent flag: `--framework`, `--template`, `--docker/--no-docker`, `--git/--no-git`, `--install/--no-install`, `--yes` (accept all defaults, skip prompts) |
| FR4 | After generation: print a summary of what was created and the exact next-step commands to run the app (and, if `--docker` was used, the `docker build`/`docker run` commands) |
| FR5 | `flint --version` prints the current version |
| FR6 | Exit codes: `0` success, `1` user/input error (e.g. bad name, existing dir, disabled framework/template), `2` unexpected/internal error |
| FR7 | `--docker` adds a `Dockerfile` and `.dockerignore`; if the chosen template doesn't support it yet, warn and continue rather than failing the whole generation |
| FR8 | Every generated project includes an `AGENTS.md` with run/test commands, layout, and conventions — no flag, always on |

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
  (v0.2) — it's a single Jinja file, same mechanism as the README, and
  gives any AI coding agent working in the generated project immediate
  context (run/test commands, layout, conventions). `.agents/skills/<framework>`
  — a directory of framework-specific, agent-consumable skills — is a
  larger bet: it needs real per-framework content (not just metadata),
  a decision on which skill format/consumers to target, and is more
  provable once there's more than one framework/template to
  differentiate against. Tracked as a roadmap item, not committed to a
  release yet.
