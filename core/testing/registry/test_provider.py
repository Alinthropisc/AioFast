from __future__ import annotations

import pytest

from core.foundation import Application
from core.registry import AdapterManager, RegistryServiceProvider


class TestRegistryServiceProvider:
    @pytest.mark.asyncio
    async def test_register_binds_manager(self):
        app = Application()
        provider = RegistryServiceProvider(app)
        await provider.register()

        mgr = await app.make(AdapterManager)
        assert isinstance(mgr, AdapterManager)

    @pytest.mark.asyncio
    async def test_register_by_string(self):
        app = Application()
        provider = RegistryServiceProvider(app)
        await provider.register()

        mgr = await app.make("adapters")
        assert isinstance(mgr, AdapterManager)
