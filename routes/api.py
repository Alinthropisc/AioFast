"""API routes.

Demonstrates controller-based routing under an ``/api`` prefix.
"""

from __future__ import annotations

from app.http.controllers.health_controller import HealthController
from app.http.controllers.user_controller import UserController
from core.registry import RouteCollector


def register(routes: RouteCollector, app) -> None:
    with routes.group(prefix="/api", name="api.") as r:
        r.controller(HealthController, container=app)
        r.controller(UserController, container=app)
