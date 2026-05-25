# Quick Start

## Install

```bash
uv sync
```

## Configure

```bash
cp .env.example .env
python aiocraft.py key:generate
```

## Run the HTTP server

```bash
python aiocraft.py serve --port=8000
```

Then open:

- `http://127.0.0.1:8000/` — example route
- `http://127.0.0.1:8000/api/health` — example controller
- `http://127.0.0.1:8000/schema/swagger` — OpenAPI docs

## Define routes

Routes live in `routes/web.py` and `routes/api.py`. Each module exposes
`register(routes, app)`:

```python
from core.registry import RouteCollector


async def home() -> dict:
    return {"hello": "world"}


def register(routes: RouteCollector, app) -> None:
    routes.get("/", home, name="home")
```
