from __future__ import annotations

import pytest

from core.service.base import CrudService


class HookedService(CrudService):
    def __init__(self):
        self._items: dict[int, dict] = {
            1: {"id": 1, "name": "Alice"},
        }
        self._next = 2
        self.hook_log: list[str] = []

    async def get_all(self, **f):
        return list(self._items.values())

    async def get_by_id(self, id):
        return self._items.get(int(id))

    async def create(self, data):
        item = {"id": self._next, **data}
        self._items[self._next] = item
        self._next += 1
        return item

    async def update(self, id, data):
        item = self._items.get(int(id))
        if item:
            item.update(data)
        return item

    async def delete(self, id):
        return self._items.pop(int(id), None) is not None

    # ── hooks ─────────────────────────────────────────

    async def before_create(self, data):
        self.hook_log.append("before_create")
        data["source"] = "hook"
        return data

    async def after_create(self, item):
        self.hook_log.append("after_create")

    async def before_update(self, id, data):
        self.hook_log.append("before_update")
        return data

    async def after_update(self, item):
        self.hook_log.append("after_update")

    async def before_delete(self, id):
        self.hook_log.append("before_delete")
        # Block deletion of id=999
        return int(id) != 999

    async def after_delete(self, id):
        self.hook_log.append("after_delete")


class TestCreateWithHooks:
    @pytest.mark.asyncio
    async def test_hooks_called(self):
        svc = HookedService()
        item = await svc.create_with_hooks({"name": "Bob"})

        assert item["name"] == "Bob"
        assert item["source"] == "hook"  # before_create modified data
        assert "before_create" in svc.hook_log
        assert "after_create" in svc.hook_log

    @pytest.mark.asyncio
    async def test_hook_order(self):
        svc = HookedService()
        await svc.create_with_hooks({"name": "Test"})
        assert svc.hook_log == ["before_create", "after_create"]


class TestUpdateWithHooks:
    @pytest.mark.asyncio
    async def test_hooks_called(self):
        svc = HookedService()
        item = await svc.update_with_hooks(1, {"name": "Updated"})

        assert item["name"] == "Updated"
        assert "before_update" in svc.hook_log
        assert "after_update" in svc.hook_log


class TestDeleteWithHooks:
    @pytest.mark.asyncio
    async def test_hooks_called(self):
        svc = HookedService()
        result = await svc.delete_with_hooks(1)

        assert result is True
        assert "before_delete" in svc.hook_log
        assert "after_delete" in svc.hook_log

    @pytest.mark.asyncio
    async def test_before_delete_cancels(self):
        svc = HookedService()
        result = await svc.delete_with_hooks(999)

        assert result is False
        assert "before_delete" in svc.hook_log
        assert "after_delete" not in svc.hook_log


class TestCreateMany:
    @pytest.mark.asyncio
    async def test_create_many_with_hooks(self):
        svc = HookedService()
        items = await svc.create_many([{"name": "X"}, {"name": "Y"}])

        assert len(items) == 2
        assert all(i["source"] == "hook" for i in items)
        assert svc.hook_log.count("before_create") == 2
        assert svc.hook_log.count("after_create") == 2


class TestUpdateOrCreate:
    @pytest.mark.asyncio
    async def test_update_existing(self):
        svc = HookedService()
        item, created = await svc.update_or_create(1, {"name": "Mod"})

        assert created is False
        assert item["name"] == "Mod"
        assert "before_update" in svc.hook_log

    @pytest.mark.asyncio
    async def test_create_new(self):
        svc = HookedService()
        _item, created = await svc.update_or_create(99, {"name": "New"})

        assert created is True
        assert "before_create" in svc.hook_log


class TestFirstOrFail:
    @pytest.mark.asyncio
    async def test_found(self):
        svc = HookedService()
        item = await svc.first_or_fail()
        assert item["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_not_found(self):
        svc = HookedService()
        svc._items.clear()
        with pytest.raises(ValueError, match="not found"):
            await svc.first_or_fail()
