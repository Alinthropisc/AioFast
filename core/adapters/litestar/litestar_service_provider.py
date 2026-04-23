from __future__ import annotations

import logging

from ...foundation import ServiceProvider
from ...registry import AdapterManager
from .adapter import LitestarAdapter

logger = logging.getLogger(__name__)


class LitestarServiceProvider(ServiceProvider):
    """Register and configure LitestarAdapter."""

    async def register(self) -> None:
        adapter = LitestarAdapter()
        self.app.instance("litestar.adapter", adapter)
        self.app.instance(LitestarAdapter, adapter)

        # Register with AdapterManager
        if self.app.has(AdapterManager):
            manager: AdapterManager = await self.app.make(AdapterManager)
            manager.register(adapter)

    async def boot(self) -> None:
        pass  # Lifecycle managed by AdapterManager
