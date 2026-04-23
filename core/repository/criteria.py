from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from sqlalchemy import Select

T = TypeVar("T")


class Criteria(ABC):
    """
    Query criteria — reusable query modifiers.

    Like Laravel's Eloquent scopes but composable.

    Usage:
        class ActiveUsers(Criteria):
            def apply(self, query):
                return query.where(User.deleted_at.is_(None))

        class OrderByName(Criteria):
            def apply(self, query):
                return query.order_by(User.name)

        # In repository:
        users = await repo.get_by_criteria(ActiveUsers(), OrderByName())
    """

    @abstractmethod
    def apply(self, query: Select) -> Select:
        """Modify and return the query."""


class WhereCriteria(Criteria):
    """Simple where clause."""

    def __init__(self, **conditions: Any) -> None:
        self._conditions = conditions

    def apply(self, query: Select) -> Select:
        for key, value in self._conditions.items():
            query = query.where(getattr(query.column_descriptions[0]["entity"], key) == value)
        return query


class OrderBy(Criteria):
    """Order by column."""

    def __init__(self, column: str, desc: bool = False) -> None:
        self._column = column
        self._desc = desc

    def apply(self, query: Select) -> Select:
        from sqlalchemy import desc as sa_desc

        entity = query.column_descriptions[0]["entity"]
        col = getattr(entity, self._column)
        query = query.order_by(sa_desc(col)) if self._desc else query.order_by(col)
        return query


class Limit(Criteria):
    """Limit results."""

    def __init__(self, limit: int, offset: int = 0) -> None:
        self._limit = limit
        self._offset = offset

    def apply(self, query: Select) -> Select:
        return query.limit(self._limit).offset(self._offset)


class Paginate(Criteria):
    """Pagination criteria."""

    def __init__(self, page: int = 1, per_page: int = 20) -> None:
        self.page = page
        self.per_page = per_page

    def apply(self, query: Select) -> Select:
        offset = (self.page - 1) * self.per_page
        return query.limit(self.per_page).offset(offset)


class SoftDeleteFilter(Criteria):
    """Filter out soft-deleted records."""

    def apply(self, query: Select) -> Select:
        entity = query.column_descriptions[0]["entity"]
        if hasattr(entity, "deleted_at"):
            return query.where(entity.deleted_at.is_(None))
        return query
