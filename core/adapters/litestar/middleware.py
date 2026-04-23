from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send

    from ...foundation import Application

logger = logging.getLogger(__name__)


class ContainerScopeMiddleware:
    """
    ASGI middleware — creates a scoped container per request.

    Ensures scoped bindings (e.g. DB session) are isolated per request
    and cleaned up after response.
    """

    def __init__(self, app: ASGIApp, *, aiofast_app: Application) -> None:
        self.app = app
        self._aiofast_app = aiofast_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async with self._aiofast_app.create_scope("request") as container_scope:
            scope["state"] = scope.get("state", {})
            scope["state"]["container_scope"] = container_scope
            scope["state"]["aiofast_app"] = self._aiofast_app
            await self.app(scope, receive, send)


class RequestIdMiddleware:
    """Inject X-Request-ID header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:12]
        scope["state"] = scope.get("state", {})
        scope["state"]["request_id"] = request_id

        async def send_with_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)  # ty:ignore[invalid-argument-type]

        await self.app(scope, receive, send_with_id)  # ty:ignore[invalid-argument-type]


class TimingMiddleware:
    """Add X-Process-Time header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_with_timing(message: dict) -> None:
            if message["type"] == "http.response.start":
                elapsed = time.perf_counter() - start
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", f"{elapsed:.4f}".encode()))
                message = {**message, "headers": headers}
            await send(message)  # ty:ignore[invalid-argument-type]

        await self.app(scope, receive, send_with_timing)  # ty:ignore[invalid-argument-type]


def create_container_middleware(aiofast_app: Application) -> type:
    """Factory that creates ContainerScopeMiddleware bound to our app."""

    class _Middleware:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app
            self._aiofast_app = aiofast_app

        async def __call__(self, scope, receive, send) -> None:
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            async with self._aiofast_app.create_scope("request") as scoped:
                scope["state"] = scope.get("state", {})
                scope["state"]["container_scope"] = scoped
                scope["state"]["aiofast_app"] = self._aiofast_app
                await self.app(scope, receive, send)

    return _Middleware
