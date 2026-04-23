from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, update
from sqlalchemy.dialects import postgresql, sqlite

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BulkOperations:
    """
    Efficient bulk operations — no N+1.

    Usage:
        bulk = BulkOperations(session)

        # Bulk insert (single statement)
        await bulk.insert(User, [
            {"name": "A", "email": "a@t.com"},
            {"name": "B", "email": "b@t.com"},
        ])

        # Upsert (INSERT ... ON CONFLICT UPDATE)
        await bulk.upsert(User, data, conflict_columns=["email"])

        # Bulk update by conditions
        await bulk.update_where(User, {"is_active": False}, id_in=[1, 2, 3])

        # Chunk insert (large datasets)
        await bulk.insert_chunked(User, huge_list, chunk_size=1000)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, model: type, data: list[dict[str, Any]]) -> int:
        """Bulk insert — single SQL statement."""
        if not data:
            return 0

        stmt = insert(model).values(data)
        await self._session.execute(stmt)
        await self._session.flush()

        logger.debug("Bulk inserted %d %s", len(data), model.__name__)
        return len(data)

    async def insert_chunked(self, model: type, data: list[dict[str, Any]], chunk_size: int = 1000) -> int:
        """Bulk insert in chunks — for very large datasets."""
        total = 0
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            total += await self.insert(model, chunk)
        return total

    async def insert_returning(self, model: type, data: list[dict[str, Any]]) -> list[Any]:
        """Bulk insert with RETURNING (PostgreSQL)."""
        if not data:
            return []

        stmt = insert(model).values(data).returning(model)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return list(result.scalars().all())

    async def upsert(
        self,
        model: type,
        data: list[dict[str, Any]],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> int:
        """
        Upsert — INSERT ON CONFLICT UPDATE.

        Args:
            model: SQLAlchemy model class
            data: list of dicts to upsert
            conflict_columns: columns that define uniqueness
            update_columns: columns to update on conflict (None = all non-conflict)
        """
        if not data:
            return 0
        # Determine dialect
        dialect = self._session.bind.dialect.name if self._session.bind else "sqlite"

        if dialect == "postgresql":
            return await self._upsert_pg(model, data, conflict_columns, update_columns)
        elif dialect == "sqlite":
            return await self._upsert_sqlite(model, data, conflict_columns, update_columns)
        else:
            # Fallback: manual upsert
            return await self._upsert_fallback(model, data, conflict_columns, update_columns)

    async def _upsert_pg(self, model, data, conflict_columns, update_columns) -> int:
        """PostgreSQL INSERT ON CONFLICT DO UPDATE."""
        stmt = postgresql.insert(model).values(data)

        if update_columns is None:
            update_columns = [k for k in data[0] if k not in conflict_columns]
        update_dict = {col: stmt.excluded[col] for col in update_columns}
        stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=update_dict)
        await self._session.execute(stmt)
        await self._session.flush()
        return len(data)

    async def _upsert_sqlite(self, model, data, conflict_columns, update_columns) -> int:
        """SQLite INSERT OR REPLACE."""
        stmt = sqlite.insert(model).values(data)

        if update_columns is None:
            update_columns = [k for k in data[0] if k not in conflict_columns]
        update_dict = {col: stmt.excluded[col] for col in update_columns}
        stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=update_dict)
        await self._session.execute(stmt)
        await self._session.flush()
        return len(data)

    async def _upsert_fallback(self, model, data, conflict_columns, update_columns) -> int:
        """Manual upsert for unsupported dialects."""
        count = 0
        for row in data:
            find_by = {k: row[k] for k in conflict_columns}
            existing = await self._session.execute(model.__table__.select().filter_by(**find_by))
            if existing.first():
                update_vals = {k: row[k] for k in (update_columns or row.keys()) if k not in conflict_columns}
                await self._session.execute(update(model).filter_by(**find_by).values(**update_vals))
            else:
                await self._session.execute(insert(model).values(**row))
            count += 1
        await self._session.flush()
        return count

    async def update_batch(self, model: type, updates: list[dict[str, Any]], key: str = "id") -> int:
        """
        Batch update — update multiple rows with different values.

        Each dict in updates must contain the key column.

        Usage:
            await bulk.update_batch(User, [
                {"id": 1, "name": "Alice Updated"},
                {"id": 2, "name": "Bob Updated"},
            ])
        """
        count = 0
        for row in updates:
            pk_value = row.pop(key, None)

            if pk_value is None:
                continue
            stmt = update(model).where(getattr(model, key) == pk_value).values(**row)
            result = await self._session.execute(stmt)
            count += result.rowcount  # ty:ignore[unresolved-attribute]
        await self._session.flush()
        return count

    async def delete_batch(self, model: type, ids: list[Any], key: str = "id") -> int:
        """Bulk delete by IDs."""
        if not ids:
            return 0

        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(model).where(getattr(model, key).in_(ids))
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # ty:ignore[unresolved-attribute]

    def __repr__(self) -> str:
        return "<BulkOperations>"
