from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload, subqueryload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class EagerLoader:
    """
    Eager loading helper — prevent N+1 queries.

    Usage:
        loader = EagerLoader(session)

        # Load user with posts and comments (one query each):
        user = await loader.load(
            User, 1,
            with_=["posts", "posts.comments", "profile"]
        )

        # Load many with relations:
        users = await loader.load_many(
            User,
            with_=["posts"],
            where={"is_active": True},
        )

        # Strategy control:
        users = await loader.load_many(
            User,
            with_={"posts": "selectin", "profile": "joined"},
        )
    """

    STRATEGIES = {
        "joined": joinedload,
        "selectin": selectinload,
        "subquery": subqueryload,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, model: type[T], pk: Any, with_: Any = None) -> T | None:
        """Load single record with eager-loaded relations."""
        query = select(model)
        query = self._apply_eager(query, model, with_)

        # Filter by PK
        pk_col = next(iter(model.__table__.primary_key.columns))  # ty:ignore[unresolved-attribute]
        query = query.where(pk_col == pk)

        result = await self._session.execute(query)
        return result.unique().scalar_one_or_none()

    async def load_many(
        self,
        model: type[T],
        with_: Any = None,
        where: dict | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[T]:
        """Load multiple records with eager-loaded relations."""
        query = select(model)
        query = self._apply_eager(query, model, with_)

        if where:
            query = query.filter_by(**where)

        if order_by:
            col = getattr(model, order_by)
            query = query.order_by(col)

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.unique().scalars().all())

    def _apply_eager(self, query, model, with_):
        """Apply eager loading options to query."""
        if with_ is None:
            return query

        if isinstance(with_, (list, tuple)):
            for rel in with_:
                query = self._add_relation(query, model, rel, "selectin")

        elif isinstance(with_, dict):
            for rel, strategy in with_.items():
                query = self._add_relation(query, model, rel, strategy)

        return query

    def _add_relation(self, query, model, relation: str, strategy: str):
        """Add single relation with proper nesting."""
        loader_fn = self.STRATEGIES.get(strategy, selectinload)
        parts = relation.split(".")

        # Build nested loader
        current = getattr(model, parts[0], None)
        if current is None:
            return query

        option = loader_fn(current)

        for part in parts[1:]:
            # For nested: selectinload(User.posts).selectinload(Post.comments)
            option = option.selectinload(getattr(option.property.mapper.class_, part, part))  # ty:ignore[invalid-argument-type, unresolved-attribute]

        return query.options(option)

    def __repr__(self) -> str:
        return "<EagerLoader>"
