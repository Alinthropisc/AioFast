from __future__ import annotations

import pytest

from core.database.testing import (
    assert_database_count,
    assert_database_has,
    assert_database_missing,
)
from core.testing.database.conftest import User


class TestAssertHelpers:
    @pytest.mark.asyncio
    async def test_assert_has(self, session):
        user = User(name="Alice", email="alice@assert.com")
        session.add(user)
        await session.flush()

        await assert_database_has(session, User, email="alice@assert.com")

    @pytest.mark.asyncio
    async def test_assert_has_fails(self, session):
        with pytest.raises(AssertionError, match="to exist"):
            await assert_database_has(session, User, email="nobody@test.com")

    @pytest.mark.asyncio
    async def test_assert_missing(self, session):
        await assert_database_missing(session, User, email="ghost@test.com")

    @pytest.mark.asyncio
    async def test_assert_missing_fails(self, session):
        user = User(name="Bob", email="bob@assert.com")
        session.add(user)
        await session.flush()

        with pytest.raises(AssertionError, match="to NOT exist"):
            await assert_database_missing(session, User, email="bob@assert.com")

    @pytest.mark.asyncio
    async def test_assert_count(self, session):
        session.add_all(
            [
                User(name="A", email="a@count.com"),
                User(name="B", email="b@count.com"),
                User(name="C", email="c@count.com"),
            ]
        )
        await session.flush()

        await assert_database_count(session, User, 3)

    @pytest.mark.asyncio
    async def test_assert_count_fails(self, session):
        session.add(User(name="A", email="a@cf.com"))
        await session.flush()

        with pytest.raises(AssertionError, match="Expected 5"):
            await assert_database_count(session, User, 5)
