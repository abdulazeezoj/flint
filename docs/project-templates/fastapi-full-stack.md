# FastAPI · Full-Stack

The server-rendered counterpart to [FastAPI · REST API](fastapi-rest-api.md).
Same options, same layered architecture, same `pydantic-settings`-backed
config — the only thing that changes is what a route returns. Where
`rest-api` returns JSON, this template returns HTML: a Jinja2 page for
`GET /`, and an HTML fragment for every state-changing request, swapped
into the page by [HTMX](https://htmx.org) without a full reload and
without any client-side JavaScript framework.

It generates one example resource, a Todo list (`GET /`, `POST /todos`,
`POST /todos/{id}/toggle`, `DELETE /todos/{id}`), backed by an in-memory
store by default or a real database if you pick one — enough to see
every layer actually wired together, including the parts specific to a
server-rendered UI (partial swaps, an out-of-band DOM update), not just
a JSON contract.

## Options

The database/ORM/migrations/worker/broker/redis options are identical
to `rest-api`'s — same keys, same defaults, same dependency wiring. See
[FastAPI · REST API → Options](fastapi-rest-api.md#options) for the
full table and the `redis`/`broker` decoupling explanation; it's not
repeated here because it's genuinely the same logic, unmodified. One
option is unique to this template, since it's about presentation, not
the backend stack:

| Option | Choices | Default |
|---|---|---|
| `css` | `vanilla` (hand-written CSS, no build step), `tailwind` (Tailwind CSS v4, standalone CLI) | `vanilla` |

See [Styling](#styling-cssvanilla-vs-csstailwind) below.

## What gets generated

```text
src/{{ package_name }}/
  main.py              FastAPI entrypoint — app, lifespan, mounted routers, /static mount
  worker.py            worker entrypoint (iff a worker is chosen)
  routes/               one module per HTTP resource
    todos.py              returns HTML/fragments, not JSON
  templates/             Jinja2 templates, rendered via core/templates.py
    base.html              shell — HTMX script tag, stylesheet link
    index.html              the Todo page
    partials/               HTMX-swapped fragments
      todo_item.html          one <li>
      empty_state.html         the "nothing to do yet" message
      todo_created.html        todo_item.html + an out-of-band delete of empty_state
  static/               served at /static
    css/style.css          the whole UI (css=vanilla), or...
    css/input.css          ...the Tailwind source, style.css built + git-ignored (css=tailwind)
  tasks/                 one module per background job (iff a worker is chosen)
    example.py
  core/                   shared infrastructure
    config.py               settings (pydantic-settings) — always
    templates.py             the shared Jinja2Templates instance — always
    db.py                    async engine/session (iff a database is chosen)
    redis.py                 Redis client (iff redis resolves true)
  models.py               {orm} models (iff a database is chosen)
tests/
alembic/                 migrations (iff migrations is on)
AGENTS.md
Dockerfile               (iff --docker)
```

No `schemas.py`: there's no separate request/response contract to
declare the way `rest-api` needs one for its JSON payloads. The
in-memory layer's `Todo` is a plain `@dataclass` defined right in
`routes/todos.py`; the DB-backed layers pass their `models.py` `Todo`
straight into the template as the render context. One fewer file, one
fewer thing to keep in sync, because this template genuinely has no use
for it.

## Why `templates/` and `static/` files have no `.jinja` suffix

This is the one mechanic worth understanding before you touch these
files, because it's the opposite of every other file flint ships.

Every `.jinja` file elsewhere in a flint template is rendered through
**flint's own** Jinja2 environment at generation time — that's how
`{{ package_name }}` in a Python file becomes `my_api`. But
`templates/index.html`, `templates/partials/todo_item.html`, and the
rest contain Jinja2 syntax meant for the **generated app's own**
runtime `Jinja2Templates` instance: `{% block %}`, `{% for todo in
todos %}`, `{{ todo.title }}`. If these files carried a `.jinja` suffix,
flint's generator would render them **first**, at generation time,
silently evaluating and stripping that syntax — `{% for todo in todos
%}` would just vanish, since flint's own context has no `todos`
variable, and the page would ship broken.

So they carry no suffix at all, and flint's generator copies them
byte-for-byte, untouched. The one flint-level value these templates do
need — `app_name`, i.e. `{{ project_name }}` — is passed in from the
**route handler** instead, at request time:

```python
return templates.TemplateResponse(
    request, "index.html", {"app_name": settings.app_name, "todos": todos}
)
```

`settings.app_name` was itself resolved by flint at generation time (via
`core/config.py`'s `Settings`), so the value still ultimately traces
back to what you typed as the project name — it's just threaded through
at runtime instead of substituted directly into the HTML.

## The empty-state swap: an HTMX out-of-band update

`partials/todo_created.html` — what `POST /todos` returns — is two
elements, not one:

```html
{% include "partials/todo_item.html" %}
<li id="empty-state" hx-swap-oob="delete"></li>
```

The first is the new todo, appended to `#todo-list` via the form's
`hx-target="#todo-list" hx-swap="beforeend"`. The second is an
[out-of-band swap](https://htmx.org/docs/#oob_swaps): HTMX scans *any*
response for elements carrying `hx-swap-oob`, and if one with a
matching `id` already exists in the DOM, it applies that swap
independently of the main target — here, `hx-swap-oob="delete"` means
"remove the element with this id if it's there." On the very first
todo, `#empty-state`'s "Nothing to do yet" message is in the DOM and
gets removed; on every todo after the first, no element with that id
exists, so it's a silent no-op. `DELETE /todos/{id}` mirrors this in
the other direction at the Python level rather than via OOB: it checks
whether the store is now empty and returns `partials/empty_state.html`
(swapped in over the deleted `<li>` via that request's own
`hx-swap="outerHTML"`) instead of an empty response, bringing the
message back when the last todo goes.

This is the one piece of this template's behavior that's easy to get
subtly wrong and have it still look fine in a quick glance — see the
gotcha below.

## Styling: `css=vanilla` vs `css=tailwind`

`css=vanilla` (the default) is exactly what's shown above: a single
hand-written `static/css/style.css`, no build step, no dependency —
open it and edit it directly.

`css=tailwind` swaps in [Tailwind CSS v4](https://tailwindcss.com)
instead, via the [standalone CLI](https://tailwindcss.com/blog/standalone-cli)
([`pytailwindcss`](https://pypi.org/project/pytailwindcss/), a
`pyproject.toml` dependency, downloads and manages the platform binary
on first run) — **no Node.js or npm required**, matching the rest of
this template's "everything through `uv`" story. The source of truth
becomes `static/css/input.css`:

```css
@import "tailwindcss";

@theme {
  --color-accent: #e8622c;
  --color-accent-dark: #f27a44;
}
```

That `@theme` block is Tailwind v4's CSS-first configuration — no
`tailwind.config.js` needed to define custom design tokens like the
accent color, which then become ordinary utility classes
(`bg-accent`, `text-accent-dark`, ...) usable straight in templates.
`templates/index.html` and `templates/partials/todo_item.html` are
rewritten to use Tailwind utility classes in this mode; `static/css/style.css`
becomes a **build artifact**, git-ignored, produced by actually running
the CLI:

```bash
# One-off build:
uv run tailwindcss -i src/my_app/static/css/input.css -o src/my_app/static/css/style.css

# Watch and rebuild on every change, while developing:
uv run tailwindcss -i src/my_app/static/css/input.css -o src/my_app/static/css/style.css --watch
```

This means a freshly generated `css=tailwind` project has **no styling
at all** until you run the build once — the same "one required setup
step before first run" shape as `migrations=true` needing a migration
applied first. `--docker` covers this automatically: the Dockerfile
runs the one-off build (with `--minify`) as part of the image, so a
container always ships current, correctly-styled CSS regardless of
whether you remembered to build it locally.

## A full example

```bash
flint new my-app \
  --framework fastapi --template full-stack \
  -o database=postgres -o orm=sqlmodel -o migrations=true \
  -o worker=taskiq -o broker=redis \
  --docker --git --install --yes
```

Once it's generated:

```bash
cd my-app

# migrations are on, so the schema doesn't exist until you run this
uv run alembic upgrade head

# start the app
uv run fastapi dev src/my_app/main.py
```

Open `http://127.0.0.1:8000` — a Todo list. Type into the input and
submit: the new item appears without a page reload. Check its box: it
gets a strikethrough, also without a reload. Delete it: it's removed,
and if it was the last one, "Nothing to do yet" reappears — all via
HTMX requests you can watch in your browser's network tab, each
returning a small HTML fragment instead of a full page or JSON.

Drop `--docker` and any `-o` flags you don't want; every one of them,
plus `--framework fastapi --template full-stack`, has an interactive
equivalent if you just run `flint new my-app` and answer the prompts
instead. Add `-o css=tailwind` to any of these to get Tailwind CSS
instead of the vanilla stylesheet — see [Styling](#styling-cssvanilla-vs-csstailwind)
above.

## Gotchas worth knowing before you edit the generated code

### Migrations, worker task discovery, isolated test databases

This template shares its database/ORM/migrations/worker/broker
machinery byte-for-byte with `rest-api` — the "migrations replace
auto-create" behavior, the always-isolated-SQLite test database, the
Taskiq-is-async-only rationale, and the bottom-of-file `worker.py` task
imports all apply here identically. See
[FastAPI · REST API → Gotchas](fastapi-rest-api.md#gotchas-worth-knowing-before-you-edit-the-generated-code)
for the full write-up of each — not repeated here since nothing about
them changes when the presentation layer is HTML instead of JSON.

### A route that changes state returns a fragment, not the whole page

`routes/todos.py` never re-renders `index.html` from a `POST`/`DELETE`
handler — only `GET /` does. Every state-changing route returns exactly
the fragment that changed (`partials/todo_item.html`,
`partials/todo_created.html`, or `partials/empty_state.html`), and lets
`hx-target`/`hx-swap` on the triggering element decide where it lands.
Re-rendering the whole page from a partial-swap endpoint would still
technically work — HTMX would just replace more of the DOM than
necessary — but it defeats the reason to use partial swaps at all, and
breaks the moment two different pages start sharing this template's
routes. If you add a new state-changing endpoint, give it its own
fragment template rather than reaching for `index.html`.

### The OOB delete only fires if the target `id` still exists

`hx-swap-oob="delete"` on `#empty-state` in `todo_created.html` is a
no-op, not an error, whenever `#empty-state` isn't currently in the
DOM — which is the normal case once the list has at least one item
already. If you're debugging "why didn't the empty-state message go
away," check the actual response HTML (browser dev tools → Network →
the `POST /todos` response) before assuming the route logic is wrong;
this is usually working exactly as designed and the message you're
looking at is stale from before HTMX processed the swap.

## `.agents/skills/`

Every generated project ships an `AGENTS.md` plus a `.agents/skills/`
catalog scoped to exactly the stack your options produced — see
[Agent Skills](../agent-skills.md) for how the catalog itself works.
Identical skill set to `rest-api`'s (see
[FastAPI · REST API → `.agents/skills/`](fastapi-rest-api.md#agentsskills)) —
picking `full-stack` over `rest-api` doesn't change which library
skills you get, since the underlying stack choices are the same.

## Docker

Pass `--docker` and flint adds a `Dockerfile` (plus a matching
`.dockerignore`) to the project root — identical to `rest-api`'s, since
containerizing an HTML-rendering FastAPI app needs nothing different
from containerizing a JSON one. The one addition specific to this
template: with `css=tailwind`, the Dockerfile has one extra `RUN uv run
tailwindcss ... --minify` step so the built image always has current CSS
(see [Styling](#styling-cssvanilla-vs-csstailwind) above).

```bash
docker build -t my-app .
docker run -p 8000:8000 my-app
```

## Next

- [Templates overview](index.md) — how `hello-world`, `rest-api`, and
  `full-stack` compare, for each framework
- [FastAPI · REST API](fastapi-rest-api.md) — the JSON counterpart this
  template shares almost all of its machinery with
- [Flask · Full-Stack](flask-full-stack.md) — the same Todo app, same
  `templates/`/`static/` content, on Flask's sync stack
- [CLI Reference](../cli-reference.md) — every `-o` key this template
  accepts, and every top-level flag
