"""``serve`` — boot the application and start the HTTP server."""

from __future__ import annotations

from typing import Any

from core.console import Command
from core.console.descriptors import Option


class ServeCommand(Command):
    name = "serve"
    description = "Start the HTTP server (Litestar)"

    host = Option("--host", type=str, default=None, description="Host to bind (overrides SERVER_HOST)")
    port = Option("--port", type=int, default=None, description="Port to bind (overrides SERVER_PORT)")

    async def handle(self, **kwargs: Any) -> int:
        from core.registry import AdapterManager
        from core.server.base import ServerConfig
        from core.server.uvicorn import UvicornServer

        app = self._app.container if self._app else None  # the AioFast Application
        if app is None:
            self.error("No application container available.")
            return self.FAILURE

        self.comment("Booting application...")
        await app.boot()

        manager: AdapterManager = await app.make(AdapterManager)
        asgi = manager.get_asgi_app()
        if asgi is None:
            self.error("No HTTP adapter produced an ASGI app. Is LitestarServiceProvider registered?")
            return self.FAILURE

        # Resolve the configured server settings, applying CLI overrides.
        config: ServerConfig = await app.make("server.config")
        if self.host is not None:
            config.host = self.host
        if self.port is not None:
            config.port = self.port

        routes = len(manager.all_routes())
        self.success(f"AioFast ready — {routes} route(s) registered.")
        self.line(f"  [green]→[/green] http://{config.host}:{config.port}")
        self.line(f"  [green]→[/green] OpenAPI: http://{config.host}:{config.port}/schema/swagger")
        self.newline()

        # Uvicorn supports an in-process async serve loop, which keeps the
        # already-booted container (DB pools, etc.) alive in the same loop.
        server = UvicornServer(config)
        await server.serve(asgi)
        return self.SUCCESS
