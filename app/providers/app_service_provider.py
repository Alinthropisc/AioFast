"""Application service provider — the place to wire up your app.

Registers your route definitions with the framework's AdapterManager so that
the HTTP (Litestar) and bot (Aiogram) adapters can compile them on boot.
"""

from __future__ import annotations

from core.foundation import ServiceProvider
from core.registry import AdapterManager, RouteCollector


class AppServiceProvider(ServiceProvider):
    async def register(self) -> None:
        if not self.app.has(AdapterManager):
            return
        manager: AdapterManager = await self.app.make(AdapterManager)

        for module in self._route_modules():
            collector = RouteCollector()
            module.register(collector, self.app)
            manager.add_routes(collector)

    async def boot(self) -> None:
        pass

    def _route_modules(self) -> list:
        """Route modules to load. Each exposes ``register(routes, app)``."""
        modules = []
        try:
            from routes import api, web

            modules.extend([web, api])
        except ImportError:
            pass
        return modules
