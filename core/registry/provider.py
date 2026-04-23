from __future__ import annotations

from ..foundation import ServiceProvider
from .manager import AdapterManager


class RegistryServiceProvider(ServiceProvider):
    """Register AdapterManager in the container."""

    async def register(self) -> None:
        manager = AdapterManager()
        self.app.instance("adapters", manager)
        self.app.instance(AdapterManager, manager)

    async def boot(self) -> None:
        manager: AdapterManager = await self.app.make(AdapterManager)

        if manager.adapter_names:
            await manager.configure(self.app)
            await manager.start()
