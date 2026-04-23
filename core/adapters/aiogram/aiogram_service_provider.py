from __future__ import annotations

import logging

from ...foundation.service_provider import ServiceProvider
from ...registry.manager import AdapterManager
from .adapter import AiogramAdapter

logger = logging.getLogger(__name__)


class AiogramServiceProvider(ServiceProvider):
    """Register and configure AiogramAdapter."""

    async def register(self) -> None:
        adapter = AiogramAdapter()
        self.app.instance("aiogram.adapter", adapter)
        self.app.instance(AiogramAdapter, adapter)

        if self.app.has(AdapterManager):
            manager: AdapterManager = await self.app.make(AdapterManager)
            manager.register(adapter)

    async def boot(self) -> None:
        pass
