from __future__ import annotations

import pytest

from core.foundation.application import Application
from core.service.base import Service
from core.service.service_service_provider import ServiceServiceProvider


class MyService(Service):
    async def work(self) -> str:
        return "done"


class AnotherService(Service):
    pass


class SampleServiceProvider(ServiceServiceProvider):
    def services(self):
        return {
            MyService: "singleton",
            AnotherService: "transient",
        }


class TestServiceServiceProvider:
    @pytest.mark.asyncio
    async def test_registers_services(self):
        app = Application()
        provider = SampleServiceProvider(app)
        await provider.register()

        svc = await app.make(MyService)
        assert isinstance(svc, MyService)

    @pytest.mark.asyncio
    async def test_singleton_scope(self):
        app = Application()
        provider = SampleServiceProvider(app)
        await provider.register()

        s1 = await app.make(MyService)
        s2 = await app.make(MyService)
        assert s1 is s2

    @pytest.mark.asyncio
    async def test_transient_scope(self):
        app = Application()
        provider = SampleServiceProvider(app)
        await provider.register()

        s1 = await app.make(AnotherService)
        s2 = await app.make(AnotherService)
        assert s1 is not s2
