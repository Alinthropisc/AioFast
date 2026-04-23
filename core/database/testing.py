from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from .manager import DatabaseConfig, DatabaseManager
from .model import Model

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class DatabaseTestCase:
    """
    Test helper — wraps each test in a transaction that rolls back.

    Zero cleanup needed. Each test gets a clean slate.

    Usage:
        class TestUsers(DatabaseTestCase):
            async def test_create_user(self):
                user = User(name="Alice", email="a@t.com")
                self.session.add(user)
                await self.session.flush()
                assert user.id is not None
                # Auto-rolled back after test!

        # Or as pytest fixture:
        @pytest_asyncio.fixture
        async def db():
            async with test_session() as session:
                yield session
                # auto rollback
    """

    manager: DatabaseManager
    session: AsyncSession

    @classmethod
    async def setup_class(cls) -> None:
        cls.manager = DatabaseManager()
        cls.manager.add_connection(DatabaseConfig(name="test", url="sqlite+aiosqlite:///:memory:", echo=False))
        await cls.manager.connect_all()
        engine = cls.manager.engine("test")

        async with engine.begin() as conn:
            await conn.run_sync(Model.metadata.create_all)

    @classmethod
    async def teardown_class(cls) -> None:
        await cls.manager.disconnect_all()

    async def setup_method(self) -> None:
        """Begin transaction before each test."""
        engine = self.manager.engine("test")
        self._connection = await engine.connect()
        self._transaction = await self._connection.begin()
        self.session = AsyncSession(bind=self._connection)

    async def teardown_method(self) -> None:
        """Rollback after each test."""
        await self.session.close()
        await self._transaction.rollback()
        await self._connection.close()


async def test_session(url: str = "sqlite+aiosqlite:///:memory:") -> AsyncIterator[AsyncSession]:
    """
    Async context manager for test sessions.

    Usage:
        async with test_session() as session:
            user = User(name="Alice")
            session.add(user)
            await session.flush()
            # auto rollback at end
    """
    manager = DatabaseManager()
    manager.add_connection(DatabaseConfig(url=url))
    await manager.connect_all()

    engine = manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    async with manager.session() as session:
        yield session

    await manager.disconnect_all()


class RefreshDatabase:
    """
    Mixin — recreate tables before each test.

    Usage:
        class TestUsers(RefreshDatabase):
            async def setup_method(self):
                await self.refresh()

            async def test_create(self):
                ...
    """

    manager: DatabaseManager

    async def refresh(self) -> None:
        engine = self.manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(Model.metadata.drop_all)
            await conn.run_sync(Model.metadata.create_all)


def assert_database_has(session: AsyncSession, model: type, **conditions):
    """
    Assert helper for database tests.

    Usage:
        await assert_database_has(session, User, email="alice@t.com")
    """

    async def _check():
        from sqlalchemy import select

        result = await session.execute(select(model).filter_by(**conditions))
        row = result.scalar_one_or_none()
        assert row is not None, f"Expected {model.__name__} with {conditions} to exist in database, but it doesn't."

    return _check()


def assert_database_missing(session: AsyncSession, model: type, **conditions):
    """Assert record does NOT exist."""

    async def _check():
        from sqlalchemy import select

        result = await session.execute(select(model).filter_by(**conditions))
        row = result.scalar_one_or_none()
        assert row is None, f"Expected {model.__name__} with {conditions} to NOT exist in database, but it does."

    return _check()


def assert_database_count(session: AsyncSession, model: type, expected: int):
    """Assert exact record count."""

    async def _check():
        from sqlalchemy import func, select

        result = await session.execute(select(func.count()).select_from(model))
        count = result.scalar_one()
        assert count == expected, f"Expected {expected} {model.__name__} records, found {count}."

    return _check()
