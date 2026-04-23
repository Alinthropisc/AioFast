from __future__ import annotations

import pytest
from sqlalchemy import select

from core.database.cursor import CursorPage, CursorPaginator
from core.testing.database.conftest import User


@pytest.fixture
async def paginator_with_data(session):
    """Create paginator + seed 30 users."""
    for i in range(30):
        session.add(User(name=f"User{i:03d}", email=f"u{i}@cursor.com", age=20 + i))
    await session.flush()

    return CursorPaginator(session)


class TestCursorPaginator:
    @pytest.mark.asyncio
    async def test_first_page(self, session, paginator_with_data):
        paginator = paginator_with_data

        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
        )

        assert isinstance(page, CursorPage)
        assert len(page.items) == 10
        assert page.has_next is True
        assert page.has_prev is False
        assert page.next_cursor is not None
        assert page.per_page == 10

    @pytest.mark.asyncio
    async def test_next_page(self, session, paginator_with_data):
        paginator = paginator_with_data

        # First page
        page1 = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
        )

        # Second page
        page2 = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
            after=page1.next_cursor,
        )

        assert len(page2.items) == 10
        assert page2.has_next is True
        assert page2.has_prev is True

        # IDs should not overlap
        ids1 = {u.id for u in page1.items}
        ids2 = {u.id for u in page2.items}
        assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_last_page(self, session, paginator_with_data):
        paginator = paginator_with_data

        # Navigate to last page
        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
        )
        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
            after=page.next_cursor,
        )
        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
            after=page.next_cursor,
        )

        assert len(page.items) == 10
        assert page.has_next is False

    @pytest.mark.asyncio
    async def test_small_dataset(self, session):
        paginator = CursorPaginator(session)

        # Only 3 items, per_page=10
        for i in range(3):
            session.add(User(name=f"Small{i}", email=f"small{i}@c.com"))
        await session.flush()

        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
        )

        assert len(page.items) == 3
        assert page.has_next is False

    @pytest.mark.asyncio
    async def test_empty_dataset(self, session):
        paginator = CursorPaginator(session)

        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=10,
        )

        assert len(page.items) == 0
        assert page.has_next is False
        assert page.has_prev is False
        assert page.next_cursor is None

    @pytest.mark.asyncio
    async def test_invalid_cursor(self, session):
        paginator = CursorPaginator(session)

        with pytest.raises(ValueError, match="Invalid cursor"):
            await paginator.paginate(
                select(User).order_by(User.id),
                model=User,
                per_page=10,
                after="!!!invalid!!!",
            )

    @pytest.mark.asyncio
    async def test_encode_decode_roundtrip(self):
        original = 42
        encoded = CursorPaginator._encode_cursor(original)
        decoded = CursorPaginator._decode_cursor(encoded)
        assert decoded == original

    @pytest.mark.asyncio
    async def test_per_page_1(self, session, paginator_with_data):
        paginator = paginator_with_data

        page = await paginator.paginate(
            select(User).order_by(User.id),
            model=User,
            per_page=1,
        )

        assert len(page.items) == 1
        assert page.has_next is True
