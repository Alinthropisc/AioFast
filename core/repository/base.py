from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update

from .criteria import Criteria, Paginate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository — wraps SQLAlchemy session for a specific model.

    Provides typed CRUD operations with criteria support.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User

        repo = UserRepository(session)
        users = await repo.all()
        user = await repo.find(1)
        user = await repo.create(name="Alice", email="a@b.com")
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # ── Read ──────────────────────────────────────────────

    async def all(self, *criteria: Criteria) -> list[T]:
        """Get all records, optionally filtered by criteria."""
        query = select(self.model)
        for c in criteria:
            query = c.apply(query)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def find(self, id: Any) -> T | None:
        """Find by primary key."""
        return await self._session.get(self.model, id)

    async def find_or_fail(self, id: Any) -> T:
        """Find by primary key or raise ValueError."""
        instance = await self.find(id)
        if instance is None:
            raise ValueError(f"{self.model.__name__} with id={id} not found")
        return instance

    async def find_by(self, **kwargs: Any) -> T | None:
        """Find first record matching conditions."""
        query = select(self.model).filter_by(**kwargs)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_many(self, ids: list[Any]) -> list[T]:
        """Find multiple records by primary keys."""
        if not ids:
            return []
        pk = self._primary_key_column()
        query = select(self.model).where(pk.in_(ids))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def where(self, **kwargs: Any) -> list[T]:
        """Get records matching conditions."""
        query = select(self.model).filter_by(**kwargs)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def first(self, *criteria: Criteria) -> T | None:
        """Get first record."""
        query = select(self.model)
        for c in criteria:
            query = c.apply(query)
        query = query.limit(1)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_criteria(self, *criteria: Criteria) -> list[T]:
        """Get records filtered by criteria objects."""
        return await self.all(*criteria)

    # ── Create ────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> T:
        """Create a new record."""
        instance = self.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def create_from_dict(self, data: dict[str, Any]) -> T:
        """Create from dictionary."""
        return await self.create(**data)

    async def create_many(self, items: list[dict[str, Any]]) -> list[T]:
        """Create multiple records."""
        instances = [self.model(**data) for data in items]
        self._session.add_all(instances)
        await self._session.flush()
        for inst in instances:
            await self._session.refresh(inst)
        return instances

    # ── Update ────────────────────────────────────────────

    async def update_instance(self, instance: T, **kwargs: Any) -> T:
        """Update an existing instance."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update_by_id(self, id: Any, **kwargs: Any) -> T | None:
        """Find by id and update."""
        instance = await self.find(id)
        if instance is None:
            return None
        return await self.update_instance(instance, **kwargs)

    async def update_where(self, filters: dict[str, Any], values: dict[str, Any]) -> int:
        """Bulk update records matching filters. Returns count."""
        stmt = update(self.model).filter_by(**filters).values(**values)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # ty:ignore[unresolved-attribute]

    async def update_or_create(self, find_by: dict[str, Any], update_with: dict[str, Any]) -> tuple[T, bool]:
        """Find by conditions, update if exists, create if not."""
        instance = await self.find_by(**find_by)
        if instance is not None:
            await self.update_instance(instance, **update_with)
            return instance, False
        merged = {**find_by, **update_with}
        instance = await self.create(**merged)
        return instance, True

    # ── Delete ────────────────────────────────────────────

    async def delete_instance(self, instance: T) -> None:
        """Delete an instance."""
        await self._session.delete(instance)
        await self._session.flush()

    async def delete_by_id(self, id: Any) -> bool:
        """Delete by primary key. Returns True if deleted."""
        instance = await self.find(id)
        if instance is None:
            return False
        await self.delete_instance(instance)
        return True

    async def delete_where(self, **kwargs: Any) -> int:
        """Delete records matching conditions. Returns count."""
        stmt = delete(self.model).filter_by(**kwargs)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # ty:ignore[unresolved-attribute]

    # ── Soft Delete ───────────────────────────────────────

    async def soft_delete(self, id: Any) -> T | None:
        """Soft delete by id (requires SoftDeleteMixin)."""
        instance = await self.find(id)
        if instance is None:
            return None
        if hasattr(instance, "soft_delete"):
            instance.soft_delete()  # ty:ignore[call-non-callable]
            await self._session.flush()
        return instance

    async def restore(self, id: Any) -> T | None:
        """Restore soft-deleted record."""
        instance = await self.find(id)
        if instance is None:
            return None
        if hasattr(instance, "restore"):
            instance.restore()  # ty:ignore[call-non-callable]
            await self._session.flush()
        return instance

    async def with_trashed(self, *criteria: Criteria) -> list[T]:
        """Get all records INCLUDING soft-deleted."""
        return await self.all(*criteria)

    async def only_trashed(self) -> list[T]:
        """Get only soft-deleted records."""
        if not hasattr(self.model, "deleted_at"):
            return []
        query = select(self.model).where(self.model.deleted_at.isnot(None))  # ty:ignore[unresolved-attribute]
        result = await self._session.execute(query)
        return list(result.scalars().all())

    # ── Aggregation ───────────────────────────────────────

    async def count(self, **filters: Any) -> int:
        """Count records."""
        query = select(func.count()).select_from(self.model)
        if filters:
            query = query.filter_by(**filters)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def exists(self, **kwargs: Any) -> bool:
        """Check if any record matches conditions."""
        return await self.count(**kwargs) > 0

    # ── Pagination ────────────────────────────────────────

    async def paginate(self, page: int = 1, per_page: int = 20, *criteria: Criteria) -> dict[str, Any]:
        """Paginate results."""
        total = await self.count()

        paginate_criteria = Paginate(page=page, per_page=per_page)
        all_criteria = [*list(criteria), paginate_criteria]
        items = await self.all(*all_criteria)

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

    # ── Internal ──────────────────────────────────────────

    def _primary_key_column(self):
        """Get primary key column."""
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(self.model)
        return mapper.primary_key[0]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model.__name__}>"
