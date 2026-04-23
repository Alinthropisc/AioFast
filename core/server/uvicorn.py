from __future__ import annotations

import logging
from typing import Any

from .base import BaseServer, ServerConfig, ServerType

logger = logging.getLogger(__name__)


class UvicornServer(BaseServer):
    """
    Uvicorn ASGI server.

    Usage:
        server = UvicornServer(ServerConfig(port=8000, reload=True))
        server.run(litestar_app)
    """

    name = "uvicorn"
    server_type = ServerType.UVICORN

    def __init__(self, config: ServerConfig | None = None, *, factory: bool = False) -> None:
        super().__init__(config)
        self._factory = factory

    async def serve(self, app: Any) -> None:
        import uvicorn

        uv_config = uvicorn.Config(
            app=app,
            host=self._config.host,
            port=self._config.port,
            workers=self._config.workers,
            reload=self._config.reload,
            log_level=self._config.log_level,
            ssl_keyfile=self._config.ssl_keyfile,
            ssl_certfile=self._config.ssl_certfile,
            factory=self._factory,
            **self._config.extra,
        )
        server = uvicorn.Server(uv_config)
        self._running = True

        try:
            await server.serve()
        finally:
            self._running = False

    def run(self, app: Any) -> None:
        import uvicorn

        logger.info(
            "Starting Uvicorn on %s:%d (workers=%d, reload=%s)",
            self._config.host,
            self._config.port,
            self._config.workers,
            self._config.reload,
        )
        uvicorn.run(
            app,
            host=self._config.host,
            port=self._config.port,
            workers=self._config.workers,
            reload=self._config.reload,
            log_level=self._config.log_level,
            ssl_keyfile=self._config.ssl_keyfile,
            ssl_certfile=self._config.ssl_certfile,
            factory=self._factory,
            **self._config.extra,
        )

    def run_import_string(self, app_path: str) -> None:
        """Run with import string: 'main:app'."""
        import uvicorn

        uvicorn.run(
            app_path,
            host=self._config.host,
            port=self._config.port,
            workers=self._config.workers,
            reload=self._config.reload,
            log_level=self._config.log_level,
            **self._config.extra,
        )

    @classmethod
    def is_available(cls) -> bool:
        try:
            import uvicorn  # noqa: F401

            return True
        except ImportError:
            return False
