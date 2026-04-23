from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send

from .context import LogContext


class RequestLogMiddleware:
    """
    ASGI middleware — auto-log HTTP requests with timing.

    Logs:
      → GET /api/users
      ← GET /api/users 200 12.34ms

    Also pushes request_id into LogContext so all logs
    within a request have the same request_id.

    Usage in Kernel:
        from aiofast.log.middleware import RequestLogMiddleware
        middleware = [create_middleware_from_asgi(RequestLogMiddleware)]
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_manager: Any = None,
        slow_threshold_ms: float = 1000.0,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self._log = log_manager
        self._slow = slow_threshold_ms
        self._exclude = set(exclude_paths or ["/health", "/favicon.ico"])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._exclude:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "?")
        request_id = uuid.uuid4().hex[:12]
        status_code = 0

        async def capture_send(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                # Inject request-id header
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)  # ty:ignore[invalid-argument-type]

        log = self._get_logger()

        with LogContext(request_id=request_id):
            log.info("→ {} {}", method, path)
            start = time.perf_counter()

            try:
                await self.app(scope, receive, capture_send)  # ty:ignore[invalid-argument-type]
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                log.error("✗ {} {} 500 {:.2f}ms — {}", method, path, elapsed, exc)
                raise

            elapsed = (time.perf_counter() - start) * 1000

            if status_code >= 500:
                log.error("← {} {} {} {:.2f}ms", method, path, status_code, elapsed)
            elif status_code >= 400:
                log.warning("← {} {} {} {:.2f}ms", method, path, status_code, elapsed)
            elif elapsed >= self._slow:
                log.warning("← {} {} {} {:.2f}ms 🐌", method, path, status_code, elapsed)
            else:
                log.info("← {} {} {} {:.2f}ms", method, path, status_code, elapsed)

    def _get_logger(self) -> Any:
        if self._log:
            return self._log
        from loguru import logger

        return logger
