from __future__ import annotations

import pytest

from core.database.model import BaseModel
from core.database.scopes import ScopeQuery
from core.testing.database.conftest import ScopedUser

# ── Model with scopes ────────────────────────────────────


@pytest.fixture(autouse=True)
async def _create_scoped_table(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


class TestScopeQuery:
    @pytest.mark.asyncio
    async def test_query_returns_scope_query(self):
        q = ScopedUser.query()
        assert isinstance(q, ScopeQuery)

    @pytest.mark.asyncio
    async def test_active_scope(self, session):
        session.add_all(
            [
                ScopedUser(name="Alice", email="a@t.com", is_active=True),
                ScopedUser(name="Bob", email="b@t.com", is_active=False),
                ScopedUser(name="Charlie", email="c@t.com", is_active=True),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().active().execute(session)
        assert len(result) == 2
        assert all(u.is_active for u in result)

    @pytest.mark.asyncio
    async def test_admins_scope(self, session):
        session.add_all(
            [
                ScopedUser(name="Admin1", email="a1@t.com", role="admin"),
                ScopedUser(name="User1", email="u1@t.com", role="user"),
                ScopedUser(name="Admin2", email="a2@t.com", role="admin"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().admins().execute(session)
        assert len(result) == 2
        assert all(u.role == "admin" for u in result)

    @pytest.mark.asyncio
    async def test_chained_scopes(self, session):
        session.add_all(
            [
                ScopedUser(name="Active Admin", email="aa@t.com", is_active=True, role="admin"),
                ScopedUser(name="Inactive Admin", email="ia@t.com", is_active=False, role="admin"),
                ScopedUser(name="Active User", email="au@t.com", is_active=True, role="user"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().active().admins().execute(session)
        assert len(result) == 1
        assert result[0].name == "Active Admin"

    @pytest.mark.asyncio
    async def test_scope_with_args(self, session):
        session.add_all(
            [
                ScopedUser(name="Admin", email="a@t.com", role="admin"),
                ScopedUser(name="Editor", email="e@t.com", role="editor"),
                ScopedUser(name="User", email="u@t.com", role="user"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().by_role("editor").execute(session)
        assert len(result) == 1
        assert result[0].role == "editor"

    @pytest.mark.asyncio
    async def test_search_scope(self, session):
        session.add_all(
            [
                ScopedUser(name="Alice Smith", email="alice@t.com"),
                ScopedUser(name="Bob Jones", email="bob@t.com"),
                ScopedUser(name="Charlie", email="alice2@t.com"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().search("alice").execute(session)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_where_kwargs(self, session):
        session.add_all(
            [
                ScopedUser(name="A", email="a@t.com", role="admin"),
                ScopedUser(name="B", email="b@t.com", role="user"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().where(role="admin").execute(session)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_first(self, session):
        session.add_all(
            [
                ScopedUser(name="First", email="f@t.com"),
                ScopedUser(name="Second", email="s@t.com"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().first(session)
        assert result is not None

    @pytest.mark.asyncio
    async def test_count(self, session):
        session.add_all(
            [
                ScopedUser(name="A", email="a@t.com"),
                ScopedUser(name="B", email="b@t.com"),
                ScopedUser(name="C", email="c@t.com"),
            ]
        )
        await session.flush()

        count = await ScopedUser.query().count(session)
        assert count == 3

    @pytest.mark.asyncio
    async def test_limit_offset(self, session):
        for i in range(10):
            session.add(ScopedUser(name=f"U{i}", email=f"u{i}@t.com"))
        await session.flush()

        result = await ScopedUser.query().limit(3).offset(2).execute(session)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_order_by(self, session):
        session.add_all(
            [
                ScopedUser(name="Zara", email="z@t.com"),
                ScopedUser(name="Alice", email="a@t.com"),
                ScopedUser(name="Mike", email="m@t.com"),
            ]
        )
        await session.flush()

        result = await ScopedUser.query().order_by("name").execute(session)
        names = [u.name for u in result]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_undefined_scope_raises(self):
        with pytest.raises(AttributeError, match="not defined"):
            ScopedUser.query().nonexistent()

    def test_repr(self):
        q = ScopedUser.query()
        assert "ScopeQuery" in repr(q)
        assert "ScopedUser" in repr(q)
