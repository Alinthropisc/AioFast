import pytest

from core.foundation import ServiceProvider
from core.testing.foundation.conftest import (
    CacheInterface,
    DatabaseInterface,
    DummyCache,
    DummyConfig,
    DummyDatabase,
)


class ConfigProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.instance(DummyConfig, DummyConfig())


class CacheProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.singleton(CacheInterface, DummyCache)


class DatabaseProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.singleton(DatabaseInterface, DummyDatabase)

    async def boot(self) -> None:
        db = await self.app.make(DatabaseInterface)
        await db.connect()


class DeferredProvider(ServiceProvider):
    @property
    def deferred(self) -> bool:
        return True

    def provides(self) -> list:
        return ["lazy_service"]

    async def register(self) -> None:
        self.app.bind("lazy_service", lambda c: "I am lazy")


class TestServiceProvider:
    @pytest.mark.asyncio
    async def test_register_and_boot(self, app):
        app.register_providers(ConfigProvider, CacheProvider, DatabaseProvider)
        await app.boot()

        cfg = await app.make(DummyConfig)
        assert isinstance(cfg, DummyConfig)

        cache = await app.make(CacheInterface)
        assert isinstance(cache, DummyCache)

        db = await app.make(DatabaseInterface)
        assert isinstance(db, DummyDatabase)
        assert db.connected

    @pytest.mark.asyncio
    async def test_deferred_provider(self, app):
        app.register_providers(ConfigProvider, DeferredProvider)
        await app.boot()

        assert not app.has("lazy_service")

        result = await app.make("lazy_service")
        assert result == "I am lazy"

    @pytest.mark.asyncio
    async def test_get_providers(self, app):
        app.register_providers(ConfigProvider, CacheProvider)
        providers = app.get_providers()
        assert len(providers) == 2

    @pytest.mark.asyncio
    async def test_provider_repr(self):
        """Test repr without full Application boot (avoid recursion)."""

        class MyProvider(ServiceProvider):
            pass

        # Use a minimal mock instead of full Application
        class FakeApp:
            pass

        p = MyProvider(FakeApp())  # ty:ignore[invalid-argument-type]
        assert "MyProvider" in repr(p)

    @pytest.mark.asyncio
    async def test_boot_order(self, app):
        order = []

        class FirstProvider(ServiceProvider):
            async def register(self) -> None:
                order.append("first_register")

            async def boot(self) -> None:
                order.append("first_boot")

        class SecondProvider(ServiceProvider):
            async def register(self) -> None:
                order.append("second_register")

            async def boot(self) -> None:
                order.append("second_boot")

        app.register_providers(FirstProvider, SecondProvider)
        await app.boot()

        assert order == [
            "first_register",
            "second_register",
            "first_boot",
            "second_boot",
        ]
