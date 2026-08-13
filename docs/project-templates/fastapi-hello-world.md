# FastAPI · Hello World

```bash
flint new my-api --framework fastapi --template hello-world --yes
```

A minimal, `uv`-managed FastAPI app: one `GET /` route returning
`{"message": "Hello, World!"}`, a passing `pytest` test, and everything
else [every Flint project ships](../getting-started.md#what-you-get-every-time).
This is the fastest path from `uvx --from flint-kit flint` to a running app — reach for
[FastAPI · REST API](fastapi-rest-api.md) instead if you need a database,
migrations, or a background worker from the start.

## What you get

```text
my-api/
├── src/
│   └── my_api/
│       ├── __init__.py
│       └── main.py          # FastAPI() app + GET /
├── tests/
│   └── test_main.py         # TestClient hits GET / and checks the response
├── AGENTS.md                 # context for AI coding agents
├── README.md                  # this project's own run/test instructions
├── pyproject.toml
└── .gitignore
```

`main.py` is deliberately small:

```python
from fastapi import FastAPI

app = FastAPI(title="my-api")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
```

## Run and test

```bash
uv run fastapi dev src/my_api/main.py
```

Open <http://127.0.0.1:8000> — you should see `{"message": "Hello, World!"}`.

```bash
uv run pytest
```

## Options

`hello-world` declares one option:

| Flag | Values | Default | Effect |
|---|---|---|---|
| `-o config=<bool>` | `true` / `false` | `false` | Adds `pydantic-settings`-based configuration. |

Turn on `-o config=true` and Flint adds a `core/config.py` module, then
swaps in a version of `main.py` that reads from it instead of hardcoding
values:

```python
from fastapi import FastAPI

from my_api.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)


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
same content, so the project tree becomes:

```text
my-api/
├── src/
│   └── my_api/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py     # Settings, loaded from .env
│       └── main.py           # reads settings.app_name / settings.debug
├── .env                       # git-ignored
├── .env.example                # checked-in reference
└── ...
```

`config.py` lives under `core/` even in this single-file template, so a
project that later grows into [rest-api](fastapi-rest-api.md)'s fuller
`core/`/`routes/`/`tasks/` layout doesn't have to relearn where config
lives.

## Docker

This template supports `--docker`: pass the flag and Flint adds a
`Dockerfile` and `.dockerignore`:

```bash
flint new my-api --framework fastapi --template hello-world --docker --yes
```

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
# ...
CMD ["fastapi", "run", "src/my_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

No Docker Compose is generated — one `Dockerfile` is the entire Docker
story here, on purpose (see [Contributing](../contributing.md) if you're
curious why).

## Agent skills

This combination ships `.agents/skills/` entries for:

| Skill | Included when |
|---|---|
| `fastapi` | always |
| `pytest` | always |
| `pydantic-settings` | `-o config=true` |

See [Agent Skills](../agent-skills.md) for what each `SKILL.md` actually
contains and how `AGENTS.md` points at them.

## Non-interactive example

```bash
flint new my-api \
  --framework fastapi --template hello-world \
  -o config=true \
  --docker --git --install --yes
```

`--yes` accepts the default for any prompt you didn't pass a flag for. See
[CLI Reference](../cli-reference.md) for every flag.
