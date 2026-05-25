"""Example controller — decorator-based routing with DI support."""

from __future__ import annotations

from typing import ClassVar

from core.controller.base import Controller
from core.controller.decorators import get


class HealthController(Controller):
    path = "/health"
    tags: ClassVar[list[str]] = ["system"]

    @get(summary="Liveness probe")
    async def index(self) -> dict:
        return self.ok({"status": "healthy"})

    @get("/ping", name="ping", summary="Ping")
    async def ping(self) -> dict:
        return {"pong": True}
