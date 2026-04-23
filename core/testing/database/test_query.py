from __future__ import annotations

import pytest

from core.database.query import DB, QueryBuilder
from core.testing.database.conftest import User


@pytest.fixture
def db(db_manager) -> DB:
    return DB(db_manager)


class TestDB:
    @pytest.mark.asyncio
    async def test_raw(self, db):

        result = await db.raw("SELECT 1 as val")
        row = result.first()
        assert row[0] == 1

    @pytest.mark.asyncio
    async def test_select_raw(self, db):
        rows = await db.select_raw("SELECT 1 as val")
        assert rows[0]["val"] == 1

    @pytest.mark.asyncio
    async def test_execute(self, db):
        # Создаём запись через raw с указанием всех полей
        await db.raw(
            "INSERT INTO test_users (name, email, is_active, role, age) VALUES (:n, :e, :is_active, :role, :age)",
            {"n": "Raw", "e": "raw@t.com", "is_active": 1, "role": "user", "age": 0},
        )
        rows = await db.select_raw(
            "SELECT * FROM test_users WHERE email = :e",
            {"e": "raw@t.com"},
        )
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_table_returns_builder(self, db):
        qb = db.table(User)
        assert isinstance(qb, QueryBuilder)


class TestQueryBuilder:
    @pytest.mark.asyncio
    async def test_insert_and_get(self, db):
        await db.table(User).insert(name="Alice", email="a@q.com")
        users = await db.table(User).get()
        assert len(users) >= 1

    @pytest.mark.asyncio
    async def test_where_eq(self, db):
        await db.table(User).insert(name="Bob", email="b@q.com")
        await db.table(User).insert(name="Eve", email="e@q.com")
        result = await db.table(User).where("name", "Bob").get()
        assert len(result) == 1
        assert result[0].name == "Bob"

    @pytest.mark.asyncio
    async def test_where_kwargs(self, db):
        await db.table(User).insert(name="Kate", email="k@q.com")
        result = await db.table(User).where(name="Kate").get()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_where_gt(self, db):
        for i in range(5):
            await db.table(User).insert(name=f"U{i}", email=f"u{i}@q.com")
        result = await db.table(User).where("id", ">", 2).get()
        assert all(u.id > 2 for u in result)

    @pytest.mark.asyncio
    async def test_first(self, db):
        await db.table(User).insert(name="First", email="f@q.com")
        user = await db.table(User).first()
        assert user is not None

    @pytest.mark.asyncio
    async def test_find(self, db):
        created = await db.table(User).insert(name="Find", email="find@q.com")
        found = await db.table(User).find(created.id)
        assert found is not None
        assert found.name == "Find"

    @pytest.mark.asyncio
    async def test_count(self, db):
        await db.table(User).insert(name="C1", email="c1@q.com")
        await db.table(User).insert(name="C2", email="c2@q.com")
        count = await db.table(User).count()
        assert count >= 2

    @pytest.mark.asyncio
    async def test_exists(self, db):
        await db.table(User).insert(name="Ex", email="ex@q.com")
        assert await db.table(User).where(name="Ex").exists()
        assert not await db.table(User).where(name="Nobody").exists()

    @pytest.mark.asyncio
    async def test_order_by(self, db):
        await db.table(User).insert(name="Zara", email="z@q.com")
        await db.table(User).insert(name="Anna", email="an@q.com")
        result = await db.table(User).order_by("name").get()
        names = [u.name for u in result]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_limit(self, db):
        for i in range(5):
            await db.table(User).insert(name=f"L{i}", email=f"l{i}@q.com")
        result = await db.table(User).limit(2).get()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_update(self, db):
        await db.table(User).insert(name="Old", email="old@q.com")
        count = await db.table(User).where(name="Old").update(name="New")
        assert count == 1

        result = await db.table(User).where(name="New").get()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete(self, db):
        await db.table(User).insert(name="Del", email="del@q.com")
        count = await db.table(User).where(name="Del").delete()
        assert count == 1
        assert not await db.table(User).where(name="Del").exists()

    @pytest.mark.asyncio
    async def test_where_in(self, db):
        await db.table(User).insert(name="A", email="a@in.com")
        await db.table(User).insert(name="B", email="b@in.com")
        await db.table(User).insert(name="C", email="c@in.com")
        result = await db.table(User).where_in("name", ["A", "C"]).get()
        names = {u.name for u in result}
        assert names == {"A", "C"}

    @pytest.mark.asyncio
    async def test_where_null(self, db):
        await db.table(User).insert(name="N", email="n@q.com")
        # updated_at is None by default
        result = await db.table(User).where_null("updated_at").get()
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_paginate(self, db):
        for i in range(15):
            await db.table(User).insert(name=f"P{i}", email=f"p{i}@q.com")
        page = await db.table(User).paginate(page=1, per_page=5)
        assert len(page["items"]) == 5
        assert page["total"] >= 15
        assert page["has_next"] is True

    @pytest.mark.asyncio
    async def test_pluck(self, db):
        await db.table(User).insert(name="Pluck", email="pluck@q.com")
        names = await db.table(User).pluck("name")
        assert "Pluck" in names

    @pytest.mark.asyncio
    async def test_latest(self, db):
        await db.table(User).insert(name="Old", email="old2@q.com")
        await db.table(User).insert(name="New", email="new2@q.com")
        user = await db.table(User).latest().first()
        assert user is not None

    @pytest.mark.skip(reason="Table registration issue with TestBase")
    @pytest.mark.asyncio
    async def test_table_by_string(self, db):
        await db.table(User).insert(name="Str", email="str@q.com")
        result = await db.table("test_users").get()
        assert len(result) >= 1
        # String table → returns dicts
        assert isinstance(result[0], dict)
