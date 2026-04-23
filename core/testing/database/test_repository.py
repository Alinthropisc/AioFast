from __future__ import annotations

import pytest

from core.repository.base import BaseRepository
from core.testing.database.conftest import SoftUser, User


class UserRepository(BaseRepository[User]):
    model = User


class SoftUserRepository(BaseRepository[SoftUser]):
    model = SoftUser


@pytest.fixture
def user_repo(session) -> UserRepository:
    return UserRepository(session)


@pytest.fixture
def soft_repo(session) -> SoftUserRepository:
    return SoftUserRepository(session)


class TestRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create(self, user_repo):
        user = await user_repo.create(name="Alice", email="alice@test.com")
        assert user.id is not None
        assert user.name == "Alice"

    @pytest.mark.asyncio
    async def test_create_from_dict(self, user_repo):
        user = await user_repo.create_from_dict(
            {
                "name": "Bob",
                "email": "bob@test.com",
            }
        )
        assert user.name == "Bob"

    @pytest.mark.asyncio
    async def test_create_many(self, user_repo):
        users = await user_repo.create_many(
            [
                {"name": "X", "email": "x@t.com"},
                {"name": "Y", "email": "y@t.com"},
            ]
        )
        assert len(users) == 2


class TestRepositoryRead:
    @pytest.mark.asyncio
    async def test_all(self, user_repo):
        await user_repo.create(name="A", email="a@t.com")
        await user_repo.create(name="B", email="b@t.com")
        users = await user_repo.all()
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_find(self, user_repo):
        created = await user_repo.create(name="Alice", email="a@t.com")
        found = await user_repo.find(created.id)
        assert found is not None
        assert found.name == "Alice"

    @pytest.mark.asyncio
    async def test_find_missing(self, user_repo):
        found = await user_repo.find(9999)
        assert found is None

    @pytest.mark.asyncio
    async def test_find_or_fail(self, user_repo):
        created = await user_repo.create(name="Bob", email="b@t.com")
        found = await user_repo.find_or_fail(created.id)
        assert found.name == "Bob"

    @pytest.mark.asyncio
    async def test_find_or_fail_raises(self, user_repo):
        with pytest.raises(ValueError, match="not found"):
            await user_repo.find_or_fail(9999)

    @pytest.mark.asyncio
    async def test_find_by(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        found = await user_repo.find_by(email="a@t.com")
        assert found is not None
        assert found.name == "Alice"

    @pytest.mark.asyncio
    async def test_where(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        await user_repo.create(name="Alice", email="a2@t.com")
        await user_repo.create(name="Bob", email="b@t.com")
        result = await user_repo.where(name="Alice")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_first(self, user_repo):
        await user_repo.create(name="First", email="f@t.com")
        first = await user_repo.first()
        assert first is not None

    @pytest.mark.asyncio
    async def test_find_many(self, user_repo):
        u1 = await user_repo.create(name="A", email="a@t.com")
        u2 = await user_repo.create(name="B", email="b@t.com")
        await user_repo.create(name="C", email="c@t.com")
        found = await user_repo.find_many([u1.id, u2.id])
        assert len(found) == 2


class TestRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_instance(self, user_repo):
        user = await user_repo.create(name="Old", email="o@t.com")
        updated = await user_repo.update_instance(user, name="New")
        assert updated.name == "New"

    @pytest.mark.asyncio
    async def test_update_by_id(self, user_repo):
        user = await user_repo.create(name="Old", email="o@t.com")
        updated = await user_repo.update_by_id(user.id, name="New")
        assert updated is not None
        assert updated.name == "New"

    @pytest.mark.asyncio
    async def test_update_by_id_missing(self, user_repo):
        result = await user_repo.update_by_id(9999, name="X")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_or_create_existing(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        item, created = await user_repo.update_or_create(
            find_by={"email": "a@t.com"},
            update_with={"name": "Updated"},
        )
        assert created is False
        assert item.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_or_create_new(self, user_repo):
        item, created = await user_repo.update_or_create(
            find_by={"email": "new@t.com"},
            update_with={"name": "New User"},
        )
        assert created is True
        assert item.name == "New User"


class TestRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_instance(self, user_repo):
        user = await user_repo.create(name="Del", email="d@t.com")
        await user_repo.delete_instance(user)
        assert await user_repo.find(user.id) is None

    @pytest.mark.asyncio
    async def test_delete_by_id(self, user_repo):
        user = await user_repo.create(name="Del", email="d@t.com")
        result = await user_repo.delete_by_id(user.id)
        assert result is True
        assert await user_repo.find(user.id) is None

    @pytest.mark.asyncio
    async def test_delete_by_id_missing(self, user_repo):
        result = await user_repo.delete_by_id(9999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_where(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        await user_repo.create(name="Alice", email="a2@t.com")
        count = await user_repo.delete_where(name="Alice")
        assert count == 2


class TestRepositorySoftDelete:
    @pytest.mark.asyncio
    async def test_soft_delete(self, soft_repo):
        user = await soft_repo.create(name="Alice", email="a@t.com")
        result = await soft_repo.soft_delete(user.id)
        assert result is not None
        assert result.is_deleted is True

    @pytest.mark.asyncio
    async def test_restore(self, soft_repo):
        user = await soft_repo.create(name="Bob", email="b@t.com")
        await soft_repo.soft_delete(user.id)
        restored = await soft_repo.restore(user.id)
        assert restored is not None
        assert restored.is_deleted is False

    @pytest.mark.asyncio
    async def test_only_trashed(self, soft_repo):
        u1 = await soft_repo.create(name="A", email="a@t.com")
        await soft_repo.create(name="B", email="b@t.com")
        await soft_repo.soft_delete(u1.id)
        trashed = await soft_repo.only_trashed()
        assert len(trashed) == 1
        assert trashed[0].name == "A"


class TestRepositoryAggregation:
    @pytest.mark.asyncio
    async def test_count(self, user_repo):
        await user_repo.create(name="A", email="a@t.com")
        await user_repo.create(name="B", email="b@t.com")
        assert await user_repo.count() == 2

    @pytest.mark.asyncio
    async def test_count_with_filter(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        await user_repo.create(name="Alice", email="a2@t.com")
        await user_repo.create(name="Bob", email="b@t.com")
        assert await user_repo.count(name="Alice") == 2

    @pytest.mark.asyncio
    async def test_exists(self, user_repo):
        await user_repo.create(name="Alice", email="a@t.com")
        assert await user_repo.exists(name="Alice") is True
        assert await user_repo.exists(name="Nobody") is False


class TestRepositoryPagination:
    @pytest.mark.asyncio
    async def test_paginate(self, user_repo):
        for i in range(25):
            await user_repo.create(name=f"User{i}", email=f"u{i}@t.com")

        page = await user_repo.paginate(page=1, per_page=10)
        assert len(page["items"]) == 10
        assert page["total"] == 25
        assert page["total_pages"] == 3
        assert page["has_next"] is True
        assert page["has_prev"] is False

    @pytest.mark.asyncio
    async def test_paginate_last_page(self, user_repo):
        for i in range(25):
            await user_repo.create(name=f"User{i}", email=f"u{i}@t.com")

        page = await user_repo.paginate(page=3, per_page=10)
        assert len(page["items"]) == 5
        assert page["has_next"] is False
        assert page["has_prev"] is True


class TestRepositoryRepr:
    def test_repr(self, user_repo):
        r = repr(user_repo)
        assert "UserRepository" in r
        assert "User" in r
