from __future__ import annotations

import pytest

from core.testing.database.conftest import SoftUser, User


class TestBaseModel:
    @pytest.mark.skip(reason="User model doesn't have created_at / to_dict / update")
    @pytest.mark.asyncio
    async def test_create(self, session):
        user = User(name="Alice", email="alice@test.com")
        session.add(user)
        await session.flush()
        await session.refresh(user)

        assert user.id is not None
        assert user.name == "Alice"
        assert user.created_at is not None  # ty:ignore[unresolved-attribute]

    @pytest.mark.skip(reason="User model doesn't have created_at / to_dict / update")
    @pytest.mark.asyncio
    async def test_to_dict(self, session):
        user = User(name="Bob", email="bob@test.com")
        session.add(user)
        await session.flush()
        await session.refresh(user)

        d = user.to_dict()  # ty:ignore[unresolved-attribute]
        assert d["name"] == "Bob"
        assert d["email"] == "bob@test.com"
        assert "id" in d

    @pytest.mark.skip(reason="User model doesn't have created_at / to_dict / update")
    @pytest.mark.asyncio
    async def test_update_method(self, session):
        user = User(name="Charlie", email="charlie@test.com")
        session.add(user)
        await session.flush()

        user.update(name="Updated")  # ty:ignore[unresolved-attribute]
        assert user.name == "Updated"

    @pytest.mark.asyncio
    async def test_repr(self, session):
        user = User(name="Dave", email="dave@test.com")
        session.add(user)
        await session.flush()
        await session.refresh(user)

        r = repr(user)
        assert "User" in r


class TestSoftDeleteMixin:
    @pytest.mark.asyncio
    async def test_soft_delete(self, session):
        user = SoftUser(name="Alice", email="alice@test.com")
        session.add(user)
        await session.flush()

        assert user.is_deleted is False
        user.soft_delete()
        assert user.is_deleted is True
        assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_restore(self, session):
        user = SoftUser(name="Bob", email="bob@test.com")
        session.add(user)
        await session.flush()

        user.soft_delete()
        assert user.is_deleted is True

        user.restore()
        assert user.is_deleted is False
        assert user.deleted_at is None
