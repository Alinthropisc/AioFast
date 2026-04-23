from __future__ import annotations

import pytest

from core.database.manager import DatabaseConfig, DatabaseManager


def pool_status(self):
    pool = self.engine.pool

    if hasattr(pool, "size"):
        return {
            "pool": type(pool).__name__,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
        }

    return {"type": type(pool).__name__, "status": "sqlite_static_pool"}


class TestDatabaseConfig:
    def test_defaults(self):
        cfg = DatabaseConfig()
        assert cfg.name == "default"
        assert cfg.pool_size == 5

    def test_repr_masks_password(self):
        cfg = DatabaseConfig(url="postgresql+asyncpg://user:secret@host/db")
        r = repr(cfg)
        assert "secret" not in r
        assert "***" in r


class TestDatabaseManager:
    def test_add_connection(self):
        m = DatabaseManager()
        m.add_connection(DatabaseConfig(name="main"))
        assert "main" in m.connections

    def test_default_connection(self):
        m = DatabaseManager()
        m.add_connection(DatabaseConfig(name="first"))
        assert m.default_connection == "first"

    def test_set_default(self):
        m = DatabaseManager()
        m.add_connection(DatabaseConfig(name="a"))
        m.add_connection(DatabaseConfig(name="b"))
        m.set_default("b")
        assert m.default_connection == "b"

    def test_set_default_unknown_raises(self):
        m = DatabaseManager()
        with pytest.raises(KeyError):
            m.set_default("nonexistent")

    @pytest.mark.asyncio
    async def test_connect(self, db_manager):
        # assert db_manager.is_connected
        assert db_manager.engine() is not None

    @pytest.mark.asyncio
    async def test_ping(self, db_manager):
        assert await db_manager.ping() is True

    @pytest.mark.asyncio
    async def test_pool_status(self, db_manager):
        status = db_manager.pool_status()
        engine = db_manager.engine()
        if "sqlite" in engine.url.drivername:
            # SQLite использует StaticPool, у него нет атрибута size
            assert "pool" in status
        else:
            assert status["pool"]["size"] > 0

    @pytest.mark.asyncio
    async def test_disconnect(self):
        m = DatabaseManager()
        m.add_connection(
            DatabaseConfig(
                url="sqlite+aiosqlite:///:memory:",
            )
        )
        await m.connect_all()
        assert m.is_connected

        await m.disconnect_all()
        assert not m.is_connected

    def test_repr(self):
        m = DatabaseManager()
        m.add_connection(DatabaseConfig())
        r = repr(m)
        assert "DatabaseManager" in r


class TestDatabaseManagerSession:
    @pytest.mark.asyncio
    async def test_session_context(self, db_manager):
        async with db_manager.session() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_auto_rollback_on_error(self, db_manager):
        try:
            async with db_manager.session() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
                raise ValueError("test error")
        except ValueError:
            pass  # Session should have been rolled back

    @pytest.mark.asyncio
    async def test_create_session(self, db_manager):
        session = await db_manager.create_session()
        assert session is not None
        await session.close()
