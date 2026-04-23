from __future__ import annotations

import os

from ..foundation.service_provider import ServiceProvider
from .base import BaseServer, ServerConfig
from .granian import GranianServer
from .uvicorn import UvicornServer


class ServerServiceProvider(ServiceProvider):
    """
    Register server based on config/available packages.

    Config (config/server.py or env):
        SERVER_TYPE=uvicorn|granian
        SERVER_HOST=0.0.0.0
        SERVER_PORT=8000
        SERVER_WORKERS=1
        SERVER_RELOAD=true
    """

    async def register(self) -> None:
        config = self._build_config()
        server = self._create_server(config)
        self.app.instance("server", server)
        self.app.instance(BaseServer, server)
        self.app.instance("server.config", config)
        self.app.instance(ServerConfig, config)

    async def boot(self) -> None:
        pass

    def _build_config(self) -> ServerConfig:
        env = os.environ.get
        return ServerConfig(
            host=env("SERVER_HOST", "0.0.0.0"),
            port=int(env("SERVER_PORT", "8000")),
            workers=int(env("SERVER_WORKERS", "1")),
            reload=env("SERVER_RELOAD", "false").lower() in ("true", "1"),
            log_level=env("SERVER_LOG_LEVEL", "info"),
            ssl_keyfile=env("SERVER_SSL_KEY"),
            ssl_certfile=env("SERVER_SSL_CERT"),
        )

    def _create_server(self, config: ServerConfig) -> BaseServer:
        preferred = os.environ.get("SERVER_TYPE", "auto").lower()

        if preferred == "granian" and GranianServer.is_available():
            interface = os.environ.get("GRANIAN_INTERFACE", "asgi")
            return GranianServer(config, interface=interface)

        if preferred == "uvicorn" and UvicornServer.is_available():
            return UvicornServer(config)

        # Auto-detect
        if preferred == "auto":
            if GranianServer.is_available():
                return GranianServer(config)
            if UvicornServer.is_available():
                return UvicornServer(config)

        # Fallback
        if UvicornServer.is_available():
            return UvicornServer(config)

        raise ImportError(
            "No ASGI server found. Install uvicorn or granian:\n  pip install uvicorn\n  pip install granian\n uv add granian\n uv add uvicorn\n"
        )
