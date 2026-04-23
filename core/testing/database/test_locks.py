from __future__ import annotations

import pytest

from core.database.locks import DatabaseLock


class TestDatabaseLock:
    @pytest.mark.asyncio
    async def test_lock_id_deterministic(self, db_manager):
        lock = DatabaseLock(db_manager)
        id1 = lock._lock_id("my-lock")
        id2 = lock._lock_id("my-lock")
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_different_names_different_ids(self, db_manager):
        lock = DatabaseLock(db_manager)
        id1 = lock._lock_id("lock-a")
        id2 = lock._lock_id("lock-b")
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_dialect_detection(self, db_manager):
        lock = DatabaseLock(db_manager)
        dialect = lock._get_dialect()
        # We're using SQLite in tests
        assert dialect == "other"

    def test_repr(self, db_manager):
        lock = DatabaseLock(db_manager)
        assert "DatabaseLock" in repr(lock)
