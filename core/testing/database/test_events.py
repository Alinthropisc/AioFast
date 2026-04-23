from __future__ import annotations

import pytest
from sqlalchemy import text

from core.database.events import QueryLogger


class TestQueryLogger:
    @pytest.mark.asyncio
    async def test_logs_queries(self, db_manager):
        logger = QueryLogger(slow_threshold=10.0)
        logger.attach(db_manager.engine())

        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))
            await session.execute(text("SELECT 2"))

        assert logger.query_count >= 2

    @pytest.mark.asyncio
    async def test_detects_slow_queries(self, db_manager):
        logger = QueryLogger(slow_threshold=0.0)  # всё "медленное"
        logger.attach(db_manager.engine())

        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))

        assert len(logger.slow_queries) >= 1

    @pytest.mark.asyncio
    async def test_on_query_callback(self, db_manager):
        logger = QueryLogger()
        logger.attach(db_manager.engine())

        captured = []
        logger.on_query(lambda e: captured.append(e))

        async with db_manager.session() as session:
            await session.execute(text("SELECT 42"))

        assert len(captured) >= 1
        assert "SELECT 42" in captured[0].sql

    @pytest.mark.asyncio
    async def test_summary(self, db_manager):
        logger = QueryLogger()
        logger.attach(db_manager.engine())

        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))

        s = logger.summary()
        assert "total_queries" in s
        assert s["total_queries"] >= 1

    @pytest.mark.asyncio
    async def test_reset(self, db_manager):
        logger = QueryLogger()
        logger.attach(db_manager.engine())

        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))

        assert logger.query_count >= 1
        logger.reset()
        assert logger.query_count == 0
