from __future__ import annotations

import pytest

from core.database.database_service_provider import DatabaseServiceProvider
from core.database.manager import DatabaseManager


class TestDatabaseServiceProvider:
    @pytest.mark.asyncio
    async def test_registers_manager(self, app):
        # register_provider — синхронный, НЕ await'им
        provider = DatabaseServiceProvider(app)
        await provider.register()  # async метод
        manager = await app.make(DatabaseManager)
        assert isinstance(manager, DatabaseManager)

    @pytest.mark.asyncio
    async def test_registers_by_string(self, app):
        provider = DatabaseServiceProvider(app)
        await provider.register()
        manager = await app.make("db.manager")  # по строке
        assert isinstance(manager, DatabaseManager)

    @pytest.mark.asyncio
    async def test_boot_with_env(self, app, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        provider = DatabaseServiceProvider(app)
        await provider.register()
        await provider.boot()
        manager = await app.make(DatabaseManager)
        assert manager.is_connected
