from __future__ import annotations

import pytest
import pytest_asyncio

from core.database.manager import DatabaseConfig, DatabaseManager
from core.database.replica import ReplicaManager


@pytest_asyncio.fixture
async def replica_manager():
    """Setup manager with 'master' + 2 'replicas' (all sqlite in-memory)."""
    manager = DatabaseManager()
    manager.add_connection(DatabaseConfig(name="master", url="sqlite+aiosqlite:///:memory:"))
    manager.add_connection(DatabaseConfig(name="replica1", url="sqlite+aiosqlite:///:memory:"))
    manager.add_connection(DatabaseConfig(name="replica2", url="sqlite+aiosqlite:///:memory:"))
    await manager.connect_all()

    replica = ReplicaManager(manager)
    replica.set_write("master")
    replica.add_read("replica1")
    replica.add_read("replica2")

    yield replica

    await manager.disconnect_all()


class TestReplicaManager:
    @pytest.mark.asyncio
    async def test_write_session(self, replica_manager):
        async with replica_manager.write_session() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_read_session(self, replica_manager):
        async with replica_manager.read_session() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_write_flag(self, replica_manager):
        async with replica_manager.session(write=True) as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_read_flag(self, replica_manager):
        async with replica_manager.session(write=False) as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_strategy_random(self, replica_manager):
        replica_manager.strategy = "random"
        # Just check it doesn't crash
        conns = set()
        for _ in range(20):
            conn = replica_manager._pick_read()
            conns.add(conn)
        assert len(conns) >= 1  # Should pick from replicas

    def test_strategy_round_robin(self, replica_manager):
        replica_manager.strategy = "round_robin"
        results = [replica_manager._pick_read() for _ in range(4)]
        # Should alternate
        assert results[0] == results[2]
        assert results[1] == results[3]
        assert results[0] != results[1]

    def test_strategy_first(self, replica_manager):
        replica_manager.strategy = "first"
        for _ in range(5):
            assert replica_manager._pick_read() == "replica1"

    def test_invalid_strategy(self, replica_manager):
        with pytest.raises(ValueError):
            replica_manager.strategy = "invalid"

    def test_fallback_to_write_when_no_reads(self):
        from core.database.manager import DatabaseManager

        mgr = DatabaseManager()
        replica = ReplicaManager(mgr)
        replica.set_write("master")
        # No reads added
        assert replica._pick_read() == "master"

    @pytest.mark.asyncio
    async def test_status(self, replica_manager):
        status = await replica_manager.status()
        assert "write" in status
        assert "read" in status
        assert status["write"]["connection"] == "master"
        assert len(status["read"]) == 2

    def test_repr(self, replica_manager):
        r = repr(replica_manager)
        assert "ReplicaManager" in r
        assert "master" in r
