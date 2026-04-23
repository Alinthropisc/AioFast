from __future__ import annotations

import logging
from typing import Any

from .base import BaseServer, ServerConfig, ServerType

logger = logging.getLogger(__name__)


class GranianServer(BaseServer):
    """
    Granian RSGI/ASGI server — Rust-based, very fast.

    Supports both ASGI and RSGI protocols.

    Usage:
        server = GranianServer(ServerConfig(port=8000, workers=4))
        server.run("main:app")  # Granian requires import string
    """

    name = "granian"
    server_type = ServerType.GRANIAN

    def __init__(self, config: ServerConfig | None = None, *, interface: str = "asgi") -> None:
        super().__init__(config)
        self._interface = interface  # "asgi" or "rsgi"

    async def serve(self, app: Any) -> None:
        # Granian doesn't have async serve — use run()
        raise NotImplementedError("Granian doesn't support async serve. Use run() with import string.")

    def run(self, app: Any) -> None:
        from granian import Granian

        if not isinstance(app, str):
            raise TypeError(
                "Granian requires an import string, e.g. 'main:app'. Use run_import_string() or pass a string."
            )

        logger.info(
            "Starting Granian (%s) on %s:%d (workers=%d)",
            self._interface,
            self._config.host,
            self._config.port,
            self._config.workers,
        )

        server = Granian(
            target=app,
            address=self._config.host,
            port=self._config.port,
            workers=self._config.workers,
            interface=self._interface,
            reload=self._config.reload,
            log_level=self._config.log_level.upper(),
            ssl_cert=self._config.ssl_certfile,
            ssl_key=self._config.ssl_keyfile,
            **self._config.extra,
        )  # ty:ignore[invalid-argument-type]
        self._running = True
        try:
            server.serve()
        finally:
            self._running = False

    @classmethod
    def is_available(cls) -> bool:
        try:
            import granian  # noqa: F401

            return True
        except ImportError:
            return False
