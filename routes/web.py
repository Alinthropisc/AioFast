"""Web routes.

Each route module exposes ``register(routes, app)`` where ``routes`` is a
:class:`~core.registry.RouteCollector`. Define plain function handlers or
attach controllers.
"""

from __future__ import annotations

from core.registry import RouteCollector


async def home() -> dict:
    return {
        "framework": "AioFast",
        "message": "⚡ Your async-first app is running.",
        "docs": "/schema/swagger",
    }


def register(routes: RouteCollector, app) -> None:
    routes.get("/", home, name="home")
