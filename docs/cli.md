# The `aiocraft` CLI

Run any command with `python aiocraft.py <command>` (or `./aiocraft <command>`).

## Core commands

| Command | Description |
| --- | --- |
| `serve` | Boot the app and start the Litestar HTTP server |
| `key:generate` | Generate and write `APP_KEY` to `.env` |
| `route:list` | Print all registered routes |
| `about` | Show application & environment info |

## Generators (`make:*`)

| Command | Creates |
| --- | --- |
| `make:controller <Name>` | HTTP controller in `app/http/controllers/` |
| `make:model <Name>` | SQLAlchemy model in `app/models/` |
| `make:command <Name>` | Console command in `app/commands/` |
| `make:middleware <Name>` | HTTP middleware in `app/http/middleware/` |
| `make:provider <Name>` | Service provider in `app/providers/` |
| `make:service <Name>` | Service class in `app/services/` |
| `make:bot-handler <Name>` | Aiogram handler in `app/bot/handlers/` |

!!! tip
    Options use the `--key=value` form, e.g. `python aiocraft.py serve --port=8080`.
