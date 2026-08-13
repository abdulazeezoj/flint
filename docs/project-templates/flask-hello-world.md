# Flask · Hello World

```bash
spindle new my-api --framework flask --template hello-world --yes
```

A minimal, `uv`-managed Flask app: one `GET /` route returning
`{"message": "Hello, World!"}`, a passing `pytest` test, and everything
else [every Spindle project ships](../getting-started.md#what-you-get-every-time).
It's the Flask mirror of [FastAPI · Hello World](fastapi-hello-world.md) —
same shape, same options, same layer structure — so switching between
Spindle's two frameworks isn't a relearn. Reach for
[Flask · REST API](flask-rest-api.md) instead if you need a database,
migrations, or a background worker from the start.

## What you get

```text
my-api/
├── src/
│   └── my_api/
│       ├── __init__.py
│       └── main.py          # Flask(__name__) app + GET /
├── tests/
│   └── test_main.py         # app.test_client() hits GET / and checks the response
├── AGENTS.md                 # context for AI coding agents
├── README.md                  # this project's own run/test instructions
├── pyproject.toml
└── .gitignore
```

`main.py` is a plain module-level app — no application-factory pattern.
Flask's own docs treat `create_app()` as something you reach for once an
app needs multiple configurations or instances; a one-route hello-world
doesn't need it. (The factory pattern does show up in
[Flask · REST API](flask-rest-api.md), once there's actually something to
configure.)

```python
from flask import Flask

app = Flask(__name__)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
```

Flask (>=1.1) auto-serializes a returned `dict` to a JSON response, so this
reads almost identically to the FastAPI version.

## Run and test

```bash
uv run flask --app src/my_api/main run
```

Open <http://127.0.0.1:5000> — you should see `{"message": "Hello, World!"}`.

```bash
uv run pytest
```

!!! note
    The entrypoint is `main.py`, not Flask's more common `app.py`/`wsgi.py`
    — Spindle uses `main.py` for every framework's entrypoint so the landmark
    file is identical whichever one you picked.

## Options

`hello-world` declares one option:

| Flag | Values | Default | Effect |
|---|---|---|---|
| `-o config=<bool>` | `true` / `false` | `false` | Adds `pydantic-settings`-based configuration. |

Turn on `-o config=true` and Spindle adds a `core/config.py` module, then
swaps in a version of `main.py` that reads from it instead of hardcoding
values. Flask's constructor takes an *import name*, not a display name, so
the configured values land on `app.config` rather than getting passed to
`Flask(...)`:

```python
from flask import Flask

from my_api.core.config import settings

app = Flask(__name__)
app.config["APP_NAME"] = settings.app_name
app.config["DEBUG"] = settings.debug


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
```

```python
# src/my_api/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "my-api"
    debug: bool = False


settings = Settings()
```

It also adds `.env` (git-ignored) and a checked-in `.env.example` with the
same content:

```text
my-api/
├── src/
│   └── my_api/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py     # Settings, loaded from .env
│       └── main.py           # reads app.config["APP_NAME"] / ["DEBUG"]
├── .env                       # git-ignored
├── .env.example                # checked-in reference
└── ...
```

## Docker

This template supports `--docker`: pass the flag and Spindle adds a
`Dockerfile` and `.dockerignore`:

```bash
spindle new my-api --framework flask --template hello-world --docker --yes
```

Flask's own dev server isn't meant for production, so the container runs
`gunicorn` instead of `flask run`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
# ...
CMD ["gunicorn", "--chdir", "src", "--bind", "0.0.0.0:8000", "my_api.main:app"]
```

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

`gunicorn` is only added to `dependencies` when `--docker` is passed — no
production WSGI server pulled in for projects that never asked for a
container. No Docker Compose is generated either, here or anywhere in
Spindle — one `Dockerfile` is the entire Docker story.

## Agent skills

This combination ships `.agents/skills/` entries for:

| Skill | Included when |
|---|---|
| `flask` | always |
| `pytest` | always |
| `pydantic-settings` | `-o config=true` |

See [Agent Skills](../agent-skills.md) for what each `SKILL.md` actually
contains and how `AGENTS.md` points at them.

## Non-interactive example

```bash
spindle new my-api \
  --framework flask --template hello-world \
  -o config=true \
  --docker --git --install --yes
```

`--yes` accepts the default for any prompt you didn't pass a flag for. See
[CLI Reference](../cli-reference.md) for every flag.
