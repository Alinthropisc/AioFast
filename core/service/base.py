from __future__ import annotations

import re
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Service:
    """
    Base service.

    Services contain business logic.
    Dependencies injected via __init__ from container.
    """

    @classmethod
    def service_name(cls) -> str:
        name = cls.__name__
        for suffix in ("Service", "Svc"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class CrudService(Service, Generic[T]):
    """
    CRUD service with hooks.

    Hooks (override to customize):
        before_create(data)    → modify data before create
        after_create(item)     → side effects after create
        before_update(id, data)
        after_update(item)
        before_delete(id)
        after_delete(id)

    Usage:
        class UserService(CrudService):
            async def before_create(self, data):
                data["created_at"] = datetime.utcnow()
                return data

            async def after_create(self, item):
                await self.send_welcome_email(item["email"])
    """

    # ── CRUD (override these) ─────────────────────────────

    async def get_all(self, **filters: Any) -> list[Any]:
        raise NotImplementedError

    async def get_by_id(self, id: Any) -> Any | None:
        raise NotImplementedError

    async def create(self, data: Any) -> Any:
        raise NotImplementedError

    async def update(self, id: Any, data: Any) -> Any:
        raise NotImplementedError

    async def delete(self, id: Any) -> bool:
        raise NotImplementedError

    # ── hooks ─────────────────────────────────────────────

    async def before_create(self, data: Any) -> Any:
        """Called before create. Return modified data."""
        return data

    async def after_create(self, item: Any) -> None:
        """Called after create. For side effects."""
        pass

    async def before_update(self, id: Any, data: Any) -> Any:
        """Called before update. Return modified data."""
        return data

    async def after_update(self, item: Any) -> None:
        """Called after update."""
        pass

    async def before_delete(self, id: Any) -> bool:
        """Called before delete. Return False to cancel."""
        return True

    async def after_delete(self, id: Any) -> None:
        """Called after delete."""
        pass

    # ── CRUD with hooks ───────────────────────────────────

    async def create_with_hooks(self, data: Any) -> Any:
        """Create with before/after hooks."""
        data = await self.before_create(data)
        item = await self.create(data)
        await self.after_create(item)
        return item

    async def update_with_hooks(self, id: Any, data: Any) -> Any:
        """Update with before/after hooks."""
        data = await self.before_update(id, data)
        item = await self.update(id, data)
        await self.after_update(item)
        return item

    async def delete_with_hooks(self, id: Any) -> bool:
        """Delete with before/after hooks."""
        allowed = await self.before_delete(id)
        if not allowed:
            return False
        result = await self.delete(id)
        if result:
            await self.after_delete(id)
        return result

    # ── helpers ───────────────────────────────────────────

    async def exists(self, id: Any) -> bool:
        result = await self.get_by_id(id)
        return result is not None

    async def count(self, **filters: Any) -> int:
        items = await self.get_all(**filters)
        return len(items)

    async def get_or_fail(self, id: Any) -> Any:
        result = await self.get_by_id(id)
        if result is None:
            raise ValueError(f"{self.service_name()} with id={id} not found")
        return result

    async def create_many(self, items: list[Any]) -> list[Any]:
        return [await self.create_with_hooks(item) for item in items]

    async def update_or_create(self, id: Any, data: Any) -> tuple[Any, bool]:
        existing = await self.get_by_id(id)
        if existing is not None:
            return await self.update_with_hooks(id, data), False
        return await self.create_with_hooks(data), True

    async def first_or_fail(self, **filters: Any) -> Any:
        """Get first item matching filters or raise."""
        items = await self.get_all(**filters)

        if not items:
            raise ValueError(f"{self.service_name()} not found with filters={filters}")
        return items[0]

    async def paginate(self, page: int = 1, per_page: int = 20, **filters: Any) -> dict[str, Any]:
        all_items = await self.get_all(**filters)
        total = len(all_items)
        start = (page - 1) * per_page
        end = start + per_page
        items = all_items[start:end]
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
