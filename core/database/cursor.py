from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


@dataclass
class CursorPage:
    """Result of cursor-based pagination."""

    items: list[Any]
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool
    per_page: int


class CursorPaginator:
    """
    Cursor-based pagination — for millions of rows.

    Why cursor > offset?
      - OFFSET 1000000 → DB scans 1M rows then discards them
      - Cursor → DB seeks directly to the right position

    Usage:
        paginator = CursorPaginator(session)

        # First page:
        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=20,
        )

        # Next page:
        page2 = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=20,
            after=page.next_cursor,
        )

        # Previous:
        page0 = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=20,
            before=page2.prev_cursor,
        )
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def paginate(
        self,
        query: Select,
        *,
        model: type,
        per_page: int = 20,
        cursor_column: str = "id",
        after: str | None = None,
        before: str | None = None,
    ) -> CursorPage:
        """Execute cursor-based pagination."""
        col = getattr(model, cursor_column)

        if after:
            cursor_value = self._decode_cursor(after)
            query = query.where(col > cursor_value)

        if before:
            cursor_value = self._decode_cursor(before)
            query = query.where(col < cursor_value)
            # Reverse order for "before", then reverse results
            from sqlalchemy import desc

            query = query.order_by(desc(col))
        # Fetch one extra to determine has_next/has_prev
        query = query.limit(per_page + 1)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        # Reverse back if going backwards
        if before:
            items.reverse()

        has_more = len(items) > per_page
        if has_more:
            items = items[:per_page]
        # Build cursors
        next_cursor = None
        prev_cursor = None

        if items:
            last_item = items[-1]
            first_item = items[0]
            last_value = getattr(last_item, cursor_column)
            first_value = getattr(first_item, cursor_column)

            if has_more or after:
                next_cursor = self._encode_cursor(last_value) if has_more else None

            if after or before:
                prev_cursor = self._encode_cursor(first_value)
        return CursorPage(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_more if not before else bool(after),
            has_prev=bool(after) if not before else has_more,
            per_page=per_page,
        )

    @staticmethod
    def _encode_cursor(value: Any) -> str:
        """Encode cursor value to opaque string."""
        payload = json.dumps({"v": value}, default=str)
        return base64.urlsafe_b64encode(payload.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> Any:
        """Decode cursor string to value."""
        try:
            payload = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(payload)
            return data["v"]
        except Exception as exc:
            raise ValueError(f"Invalid cursor: {cursor}") from exc
