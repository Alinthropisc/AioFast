from __future__ import annotations

import pytest

from core.database.migration import MigrationManager


class TestMigrationManager:
    @pytest.mark.asyncio
    async def test_create_tables(self, db_manager):
        mgr = MigrationManager(db_manager)

        # drop + create
        await mgr.drop_tables()
        await mgr.create_tables()

        # Verify by pinging
        assert await db_manager.ping()

    @pytest.mark.asyncio
    async def test_fresh(self, db_manager):
        mgr = MigrationManager(db_manager)
        await mgr.fresh()
        assert await db_manager.ping()

    @pytest.mark.asyncio
    async def test_drop_tables(self, db_manager):
        mgr = MigrationManager(db_manager)
        await mgr.create_tables()
        await mgr.drop_tables()
        # Tables dropped — re-create for other tests
        await mgr.create_tables()
