from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import Select, select

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class ScopeMixin:
    """
    Query scopes on models — like Laravel's local scopes.

    Usage:
        class User(ScopeMixin, BaseModel):
            __tablename__ = "users"

            name: Mapped[str]
            email: Mapped[str]
            is_active: Mapped[bool] = mapped_column(default=True)
            role: Mapped[str] = mapped_column(default="user")

            # Define scopes as classmethods
            @scope
            def active(cls, query):
                return query.where(cls.is_active == True)

            @scope
            def admins(cls, query):
                return query.where(cls.role == "admin")

            @scope
            def created_after(cls, query, date):
                return query.where(cls.created_at >= date)

            @scope
            def search(cls, query, term):
                return query.where(
                    or_(cls.name.ilike(f"%{term}%"), cls.email.ilike(f"%{term}%"))
                )

        # Usage:
        query = User.query().active().admins().get()
        query = User.query().search("alice").created_after(yesterday).get()
    """

    _scopes: dict[str, Callable] = {}

    @classmethod
    def query(cls) -> ScopeQuery[T]:
        """Start a scoped query for this model."""
        return ScopeQuery(cls)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Collect scopes across the MRO. We inspect the *raw* class attribute
        # (the ``classmethod`` object) and read ``_is_scope`` off its underlying
        # function — bound-method attribute proxying is unreliable on 3.13+.
        scopes: dict[str, Callable] = {}
        for klass in reversed(cls.__mro__):
            for name, value in vars(klass).items():
                fn = value.__func__ if isinstance(value, classmethod) else value
                if callable(fn) and getattr(fn, "_is_scope", False):
                    scopes[name] = getattr(cls, name)
        cls._scopes = scopes


def scope(fn: Callable) -> Callable:
    """Decorator to mark a method as a query scope."""
    fn._is_scope = True  # ty:ignore[unresolved-attribute]
    return classmethod(fn)  # ty:ignore[invalid-return-type]


class ScopeQuery:
    """Fluent query with model scopes."""

    def __init__(self, model: type) -> None:
        self._model = model
        self._query = select(model)
        self._orders: list = []
        self._limit_val: int | None = None
        self._offset_val: int | None = None

    def __getattr__(self, name: str) -> Callable:
        """Delegate to model scope if exists."""
        if name.startswith("_"):
            raise AttributeError(name)
        scope_fn = self._model._scopes.get(name)  # ty:ignore[unresolved-attribute]

        if scope_fn is None:
            raise AttributeError(f"Scope '{name}' not defined on {self._model.__name__}")

        def apply_scope(*args: Any, **kwargs: Any) -> ScopeQuery:
            # scope_fn — это bound classmethod, cls уже привязан
            # передаём только query и дополнительные аргументы
            self._query = scope_fn(self._query, *args, **kwargs)  # ← БЕЗ self._model
            return self

        return apply_scope

    def where(self, *conditions: Any, **kwargs: Any) -> ScopeQuery:
        if kwargs:
            for k, v in kwargs.items():
                self._query = self._query.where(getattr(self._model, k) == v)
        for cond in conditions:
            self._query = self._query.where(cond)
        return self

    def order_by(self, column: str, desc: bool = False) -> ScopeQuery:
        from sqlalchemy import desc as sa_desc

        col = getattr(self._model, column)
        self._query = self._query.order_by(sa_desc(col) if desc else col)
        return self

    def limit(self, n: int) -> ScopeQuery:
        self._limit_val = n
        return self

    def offset(self, n: int) -> ScopeQuery:
        self._offset_val = n
        return self

    def build(self) -> Select:
        """Build the final SQLAlchemy Select."""
        q = self._query
        if self._limit_val is not None:
            q = q.limit(self._limit_val)
        if self._offset_val is not None:
            q = q.offset(self._offset_val)
        return q

    async def execute(self, session: Any) -> list:
        """Execute and return results."""
        result = await session.execute(self.build())
        return list(result.scalars().all())

    async def first(self, session: Any) -> Any | None:
        self._limit_val = 1
        items = await self.execute(session)
        return items[0] if items else None

    async def count(self, session: Any) -> int:
        from sqlalchemy import func

        q = select(func.count()).select_from(self._query.subquery())
        result = await session.execute(q)
        return result.scalar_one()

    def __repr__(self) -> str:
        return f"<ScopeQuery model={self._model.__name__}>"


# ── Built-in Scopes ──────────────────────────────────────


class CommonScopes:
    """Mixin with common reusable scopes."""

    @scope
    def recent(self, query, hours: int = 24):
        """Records created in last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return query.where(self.created_at >= cutoff)  # ty:ignore[unresolved-attribute]

    @scope
    def older_than(self, query, days: int):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return query.where(self.created_at < cutoff)  # ty:ignore[unresolved-attribute]

    @scope
    def not_deleted(self, query):
        """Exclude soft-deleted (if SoftDeleteMixin present)."""
        if hasattr(self, "deleted_at"):
            return query.where(self.deleted_at.is_(None))  # ty:ignore[unresolved-attribute]
        return query

    @scope
    def only_deleted(self, query):
        if hasattr(self, "deleted_at"):
            return query.where(self.deleted_at.isnot(None))  # ty:ignore[unresolved-attribute]
        return query
