from __future__ import annotations

from ..foundation.service_provider import ServiceProvider


class ValidationServiceProvider(ServiceProvider):
    """Register validation services."""

    async def register(self) -> None:
        pass

    async def boot(self) -> None:
        pass
