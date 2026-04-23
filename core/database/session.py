from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from .manager import DatabaseManager


async def get_session(manager: DatabaseManager, connection: str | None = None) -> AsyncIterator[AsyncSession]:
    """
    Async generator for dependency injection.

    Yields a session, commits on success, rolls back on error.

    Usage with Litestar:
        async def provide_session(app: Application) -> AsyncIterator[AsyncSession]:
            manager = await app.make(DatabaseManager)
            async with manager.session() as session:
                yield session

    Usage with AIoFast container (scoped):
        app.scoped(AsyncSession, lambda c: get_session_factory(c))
    """
    async with manager.session(connection) as session:
        yield session


def make_session_provider(manager: DatabaseManager, connection: str | None = None):
    """
    Create a Litestar dependency provider for AsyncSession.

    Returns an async generator compatible with Litestar's Provide().
    """

    async def _provide() -> AsyncIterator[AsyncSession]:
        async with manager.session(connection) as session:
            yield session

    return _provide


class UnitOfWork:
    """
    Unit of Work pattern — wraps a session with explicit commit/rollback.

    Usage:
        async with UnitOfWork(manager) as uow:
            user = User(name="Alice")
            uow.session.add(user)
            await uow.commit()

            # If exception → auto rollback
    """

    def __init__(self, manager: DatabaseManager, connection: str | None = None) -> None:
        self._manager = manager
        self._connection = connection
        self._session: AsyncSession | None = None
        self._committed: bool = False

    async def __aenter__(self) -> UnitOfWork:
        factory = self._manager.session_factory(self._connection)
        self._session = factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        return self._session

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()
            self._committed = True

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()

    async def flush(self) -> None:
        if self._session:
            await self._session.flush()

    def add(self, instance: Any) -> None:
        self.session.add(instance)

    def add_all(self, instances: list) -> None:
        self.session.add_all(instances)

    async def delete(self, instance: Any) -> None:
        await self.session.delete(instance)

    async def refresh(self, instance: Any) -> None:
        await self.session.refresh(instance)
