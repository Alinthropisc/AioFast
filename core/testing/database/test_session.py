from __future__ import annotations

import pytest

from core.database.session import UnitOfWork
from core.testing.database.conftest import User


class TestUnitOfWork:
    @pytest.mark.asyncio
    async def test_commit(self, db_manager):
        async with UnitOfWork(db_manager) as uow:
            user = User(name="Alice", email="alice@uow.com")
            uow.add(user)
            await uow.flush()
            await uow.commit()

        # Verify persisted
        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.email == "alice@uow.com"))
            found = result.scalar_one_or_none()
            assert found is not None
            assert found.name == "Alice"

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, db_manager):
        try:
            async with UnitOfWork(db_manager) as uow:
                user = User(name="Fail", email="fail@uow.com")
                uow.add(user)
                await uow.flush()
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify NOT persisted
        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.email == "fail@uow.com"))
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_rollback_without_commit(self, db_manager):
        async with UnitOfWork(db_manager) as uow:
            user = User(name="NoCommit", email="nc@uow.com")
            uow.add(user)
            await uow.flush()
            # No commit → auto rollback

        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.email == "nc@uow.com"))
            assert result.scalar_one_or_none() is None
