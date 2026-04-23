from __future__ import annotations

from typing import Any

import pytest

from core.service.base import CrudService, Service


class SimpleService(Service):
    async def do_work(self) -> str:
        return "done"


class UserService(CrudService):
    def __init__(self) -> None:
        self._users: dict[int, dict] = {
            1: {"id": 1, "name": "Alice", "email": "alice@test.com"},
            2: {"id": 2, "name": "Bob", "email": "bob@test.com"},
            3: {"id": 3, "name": "Charlie", "email": "charlie@test.com"},
        }
        self._next_id = 4

    async def get_all(self, **filters: Any) -> list[dict]:
        items = list(self._users.values())
        if "name" in filters:
            items = [u for u in items if filters["name"] in u["name"]]
        return items

    async def get_by_id(self, id: Any) -> dict | None:
        return self._users.get(int(id))

    async def create(self, data: Any) -> dict:
        user = {"id": self._next_id, **data} if isinstance(data, dict) else {"id": self._next_id, "name": str(data)}
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    async def update(self, id: Any, data: Any) -> dict:
        user = self._users.get(int(id))
        if user and isinstance(data, dict):
            user.update(data)
        return user  # ty:ignore[invalid-return-type]

    async def delete(self, id: Any) -> bool:
        id_int = int(id)
        if id_int in self._users:
            del self._users[id_int]
            return True
        return False


class TestServiceName:
    def test_simple(self):
        assert SimpleService.service_name() == "simple"

    def test_with_suffix(self):
        assert UserService.service_name() == "user"

    def test_repr(self):
        s = SimpleService()
        assert "SimpleService" in repr(s)


class TestCrudServiceGetAll:
    @pytest.mark.asyncio
    async def test_get_all(self):
        svc = UserService()
        users = await svc.get_all()
        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_get_all_filtered(self):
        svc = UserService()
        users = await svc.get_all(name="Ali")
        assert len(users) == 1
        assert users[0]["name"] == "Alice"


class TestCrudServiceGetById:
    @pytest.mark.asyncio
    async def test_existing(self):
        svc = UserService()
        user = await svc.get_by_id(1)
        assert user is not None
        assert user["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_missing(self):
        svc = UserService()
        user = await svc.get_by_id(999)
        assert user is None


class TestCrudServiceCreate:
    @pytest.mark.asyncio
    async def test_create(self):
        svc = UserService()
        user = await svc.create({"name": "Dave", "email": "dave@test.com"})
        assert user["id"] == 4
        assert user["name"] == "Dave"
        assert len(await svc.get_all()) == 4


class TestCrudServiceUpdate:
    @pytest.mark.asyncio
    async def test_update(self):
        svc = UserService()
        user = await svc.update(1, {"name": "Alice Updated"})
        assert user["name"] == "Alice Updated"

        fetched = await svc.get_by_id(1)
        assert fetched["name"] == "Alice Updated"  # ty:ignore[not-subscriptable]


class TestCrudServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self):
        svc = UserService()
        result = await svc.delete(1)
        assert result is True
        assert len(await svc.get_all()) == 2

    @pytest.mark.asyncio
    async def test_delete_missing(self):
        svc = UserService()
        result = await svc.delete(999)
        assert result is False


class TestCrudServiceHelpers:
    @pytest.mark.asyncio
    async def test_exists(self):
        svc = UserService()
        assert await svc.exists(1) is True
        assert await svc.exists(999) is False

    @pytest.mark.asyncio
    async def test_count(self):
        svc = UserService()
        assert await svc.count() == 3

    @pytest.mark.asyncio
    async def test_get_or_fail_success(self):
        svc = UserService()
        user = await svc.get_or_fail(1)
        assert user["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_or_fail_raises(self):
        svc = UserService()
        with pytest.raises(ValueError, match="not found"):
            await svc.get_or_fail(999)

    @pytest.mark.asyncio
    async def test_create_many(self):
        svc = UserService()
        items = [{"name": "X"}, {"name": "Y"}]
        created = await svc.create_many(items)
        assert len(created) == 2
        assert len(await svc.get_all()) == 5

    @pytest.mark.asyncio
    async def test_update_or_create_update(self):
        svc = UserService()
        item, created = await svc.update_or_create(1, {"name": "Updated"})
        assert created is False
        assert item["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_or_create_create(self):
        svc = UserService()
        _item, created = await svc.update_or_create(999, {"name": "New"})
        assert created is True

    @pytest.mark.asyncio
    async def test_paginate(self):
        svc = UserService()
        result = await svc.paginate(page=1, per_page=2)
        assert result["total"] == 3
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["has_next"] is True
        assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_paginate_last_page(self):
        svc = UserService()
        result = await svc.paginate(page=2, per_page=2)
        assert len(result["items"]) == 1
        assert result["has_next"] is False
        assert result["has_prev"] is True


class TestCrudServiceNotImplemented:
    @pytest.mark.asyncio
    async def test_base_raises(self):
        svc = CrudService()
        with pytest.raises(NotImplementedError):
            await svc.get_all()
        with pytest.raises(NotImplementedError):
            await svc.get_by_id(1)
        with pytest.raises(NotImplementedError):
            await svc.create({})
        with pytest.raises(NotImplementedError):
            await svc.update(1, {})
        with pytest.raises(NotImplementedError):
            await svc.delete(1)
