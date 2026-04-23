from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    and_,
    delete,
    func,
    insert,
    or_,
    select,
    text,
    update,
)
from sqlalchemy import desc as sa_desc

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class DB:
    """
    Database facade — like Laravel's DB::.

    Usage:
        db = DB(manager)

        # Fluent query builder:
        users = await db.table(User).where("active", True).get()
        user  = await db.table(User).find(1)

        # Raw SQL:
        rows = await db.select_raw("SELECT * FROM users WHERE id = :id", {"id": 1})
        await db.execute("DELETE FROM logs WHERE created_at < :d", {"d": cutoff})

        # Transaction:
        async with db.transaction() as session:
            session.add(user)
            session.add(profile)
    """

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager

    def table(self, model_or_name: Any) -> QueryBuilder:
        """Start a fluent query."""
        return QueryBuilder(self._manager, model_or_name)

    async def raw(self, sql: str, params: dict[str, Any] | None = None, connection: str | None = None) -> Any:
        """Execute raw SQL, return SQLAlchemy Result."""
        async with self._manager.session(connection) as session:
            return await session.execute(text(sql), params or {})

    async def select_raw(
        self, sql: str, params: dict[str, Any] | None = None, connection: str | None = None
    ) -> list[dict[str, Any]]:
        """Raw SELECT → list of dicts."""
        result = await self.raw(sql, params, connection)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    async def execute(self, sql: str, params: dict[str, Any] | None = None, connection: str | None = None) -> int:
        """Raw INSERT/UPDATE/DELETE → affected rows."""
        async with self._manager.session(connection) as session:
            result = await session.execute(text(sql), params or {})
            return result.rowcount  # ty:ignore[unresolved-attribute]

    def transaction(self, connection: str | None = None):
        """Transaction context manager."""
        return self._manager.session(connection)

    async def ping(self, connection: str | None = None) -> bool:
        return await self._manager.ping(connection)

    def __repr__(self) -> str:
        return f"<DB manager={self._manager!r}>"


# ── QueryBuilder ──────────────────────────────────────────


class QueryBuilder:
    """
    Fluent query builder — Laravel-like API over SQLAlchemy.

    db.table(User)
        .where("age", ">", 18)
        .where(active=True)
        .where_not_null("email")
        .order_by("name")
        .limit(10)
        .get()
    """

    def __init__(self, manager: DatabaseManager, model_or_name: Any) -> None:
        self._manager = manager
        self._connection: str | None = None

        if isinstance(model_or_name, str):
            from .model import Model

            table = Model.metadata.tables.get(model_or_name)
            if table is None:
                raise ValueError(f"Table '{model_or_name}' not in metadata. Define a model or use DB.raw().")
            self._table = table
            self._model = None
        else:
            self._model = model_or_name
            self._table = model_or_name.__table__

        self._wheres: list[Any] = []
        self._or_wheres: list[Any] = []
        self._orders: list[tuple[str, str]] = []
        self._groups: list[str] = []
        self._limit_val: int | None = None
        self._offset_val: int | None = None
        self._select_cols: list[Any] = []
        self._distinct_flag: bool = False

    # ── Connection ────────────────────────────────────────

    def on(self, connection: str) -> QueryBuilder:
        """Use specific DB connection."""
        self._connection = connection
        return self

    # ── Select ────────────────────────────────────────────

    def select_columns(self, *columns: str) -> QueryBuilder:
        self._select_cols = [self._col(c) for c in columns]
        return self

    def distinct(self) -> QueryBuilder:
        self._distinct_flag = True
        return self

    # ── Where ─────────────────────────────────────────────

    def where(self, column: Any = None, op: Any = None, value: Any = None, **kwargs: Any) -> QueryBuilder:
        """
        .where("age", ">", 18)
        .where("name", "Alice")   # = implied
        .where(name="Alice")      # kwargs
        """
        if kwargs:
            for k, v in kwargs.items():
                self._wheres.append(self._col(k) == v)
            return self

        if column is not None:
            if value is None and op is not None:
                value, op = op, "="
            col = self._col(column) if isinstance(column, str) else column
            self._wheres.append(self._op(col, op, value))
        return self

    def where_in(self, column: str, values: list) -> QueryBuilder:
        self._wheres.append(self._col(column).in_(values))
        return self

    def where_not_in(self, column: str, values: list) -> QueryBuilder:
        self._wheres.append(self._col(column).notin_(values))
        return self

    def where_null(self, column: str) -> QueryBuilder:
        self._wheres.append(self._col(column).is_(None))
        return self

    def where_not_null(self, column: str) -> QueryBuilder:
        self._wheres.append(self._col(column).isnot(None))
        return self

    def where_between(self, column: str, low: Any, high: Any) -> QueryBuilder:
        self._wheres.append(self._col(column).between(low, high))
        return self

    def where_like(self, column: str, pattern: str) -> QueryBuilder:
        self._wheres.append(self._col(column).like(pattern))
        return self

    def or_where(self, column: str, op: Any = None, value: Any = None) -> QueryBuilder:
        if value is None:
            value, op = op, "="
        self._or_wheres.append(self._op(self._col(column), op, value))
        return self

    # ── Order / Group / Limit ─────────────────────────────

    def order_by(self, column: str, direction: str = "asc") -> QueryBuilder:
        self._orders.append((column, direction.lower()))
        return self

    def latest(self, column: str = "created_at") -> QueryBuilder:
        return self.order_by(column, "desc")

    def oldest(self, column: str = "created_at") -> QueryBuilder:
        return self.order_by(column, "asc")

    def group_by(self, *columns: str) -> QueryBuilder:
        self._groups.extend(columns)
        return self

    def limit(self, n: int) -> QueryBuilder:
        self._limit_val = n
        return self

    def offset(self, n: int) -> QueryBuilder:
        self._offset_val = n
        return self

    def take(self, n: int) -> QueryBuilder:
        return self.limit(n)

    def skip(self, n: int) -> QueryBuilder:
        return self.offset(n)

    # ── Read ──────────────────────────────────────────────

    async def get(self) -> list[Any]:
        """Execute → all results."""
        query = self._build_select()
        async with self._session() as session:
            result = await session.execute(query)
            if self._model:
                return list(result.scalars().all())
            return [dict(row._mapping) for row in result.fetchall()]

    async def first(self) -> Any | None:
        """First result or None."""
        self._limit_val = 1
        items = await self.get()
        return items[0] if items else None

    async def find(self, pk: Any) -> Any | None:
        """Find by primary key."""
        pk_col = next(iter(self._table.primary_key.columns))
        self._wheres.append(pk_col == pk)
        return await self.first()

    async def value(self, column: str) -> Any:
        """Single column value from first row."""
        self._select_cols = [self._col(column)]
        self._limit_val = 1
        async with self._session() as session:
            result = await session.execute(self._build_select())
            row = result.first()
            return row[0] if row else None

    async def pluck(self, column: str) -> list[Any]:
        """List of single column values."""
        self._select_cols = [self._col(column)]
        async with self._session() as session:
            result = await session.execute(self._build_select())
            return [row[0] for row in result.fetchall()]

    async def chunk(self, size: int) -> AsyncIterator[list[Any]]:
        """Yield results in chunks."""
        offset = 0
        while True:
            self._limit_val = size
            self._offset_val = offset
            items = await self.get()
            if not items:
                break
            yield items
            if len(items) < size:
                break
            offset += size

    # ── Aggregates ────────────────────────────────────────

    async def count(self) -> int:
        q = select(func.count()).select_from(self._table)
        q = self._apply_wheres(q)
        async with self._session() as session:
            return (await session.execute(q)).scalar_one()

    async def exists(self) -> bool:
        return (await self.count()) > 0

    async def sum(self, column: str) -> Any:
        return await self._agg(func.sum, column)

    async def avg(self, column: str) -> Any:
        return await self._agg(func.avg, column)

    async def min(self, column: str) -> Any:
        return await self._agg(func.min, column)

    async def max(self, column: str) -> Any:
        return await self._agg(func.max, column)

    async def _agg(self, fn, column: str) -> Any:
        q = select(fn(self._col(column))).select_from(self._table)
        q = self._apply_wheres(q)
        async with self._session() as session:
            return (await session.execute(q)).scalar_one()

    # ── Insert ────────────────────────────────────────────

    async def insert(self, **data: Any) -> Any:
        if self._model:
            async with self._session() as session:
                inst = self._model(**data)
                session.add(inst)
                await session.flush()
                await session.refresh(inst)
                return inst
        stmt = insert(self._table).values(**data)
        async with self._session() as session:
            return await session.execute(stmt)

    async def insert_many(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        stmt = insert(self._table).values(records)
        async with self._session() as session:
            await session.execute(stmt)
            return len(records)

    # ── Update ────────────────────────────────────────────

    async def update(self, **values: Any) -> int:
        stmt = update(self._table).values(**values)
        for w in self._wheres:
            stmt = stmt.where(w)
        async with self._session() as session:
            result = await session.execute(stmt)
            return result.rowcount

    # ── Delete ────────────────────────────────────────────

    async def delete(self) -> int:
        stmt = delete(self._table)
        for w in self._wheres:
            stmt = stmt.where(w)
        async with self._session() as session:
            result = await session.execute(stmt)
            return result.rowcount

    # ── Pagination ────────────────────────────────────────

    async def paginate(self, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        total = await self.count()
        self._limit_val = per_page
        self._offset_val = (page - 1) * per_page
        items = await self.get()
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

    def _col(self, name: str):
        """Resolve column by name."""
        if self._model and hasattr(self._model, name):
            return getattr(self._model, name)
        if name in self._table.c:
            return self._table.c[name]
        raise ValueError(f"Column '{name}' not found")

    def _op(self, col, op: str, value: Any):
        """Build comparison expression."""
        _OPS = {
            "=": lambda c, v: c == v,
            "!=": lambda c, v: c != v,
            "<>": lambda c, v: c != v,
            ">": lambda c, v: c > v,
            ">=": lambda c, v: c >= v,
            "<": lambda c, v: c < v,
            "<=": lambda c, v: c <= v,
            "like": lambda c, v: c.like(v),
            "ilike": lambda c, v: c.ilike(v),
            "in": lambda c, v: c.in_(v),
        }
        fn = _OPS.get(op.lower() if isinstance(op, str) else "=")
        if fn is None:
            raise ValueError(f"Unknown operator: {op}")
        return fn(col, value)

    def _build_select(self):
        if self._select_cols:
            q = select(*self._select_cols)
        elif self._model:
            q = select(self._model)
        else:
            q = select(self._table)

        q = self._apply_wheres(q)

        if self._distinct_flag:
            q = q.distinct()

        for col_name, direction in self._orders:
            col = self._col(col_name)
            q = q.order_by(sa_desc(col) if direction == "desc" else col)

        for col_name in self._groups:
            q = q.group_by(self._col(col_name))

        if self._limit_val is not None:
            q = q.limit(self._limit_val)
        if self._offset_val is not None:
            q = q.offset(self._offset_val)

        return q

    def _apply_wheres(self, q):
        if self._wheres:
            q = q.where(and_(*self._wheres))
        if self._or_wheres:
            q = q.where(or_(*self._or_wheres))
        return q

    def _session(self):
        return self._manager.session(self._connection)

    def __repr__(self) -> str:
        return f"<QueryBuilder table={self._table.name}>"
