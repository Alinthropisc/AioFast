from __future__ import annotations

import pytest
from sqlalchemy import select

from core.database.bulk import BulkOperations
from core.testing.database.conftest import User


class TestBulkInsert:
    @pytest.mark.asyncio
    async def test_insert(self, session):
        bulk = BulkOperations(session)
        count = await bulk.insert(
            User,
            [
                {"name": "A", "email": "a@bulk.com", "age": 20},
                {"name": "B", "email": "b@bulk.com", "age": 25},
                {"name": "C", "email": "c@bulk.com", "age": 30},
            ],
        )
        assert count == 3

        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 3

    @pytest.mark.asyncio
    async def test_insert_empty(self, session):
        bulk = BulkOperations(session)
        count = await bulk.insert(User, [])
        assert count == 0

    @pytest.mark.asyncio
    async def test_insert_chunked(self, session):
        bulk = BulkOperations(session)
        data = [{"name": f"User{i}", "email": f"u{i}@chunk.com", "age": i} for i in range(25)]
        count = await bulk.insert_chunked(User, data, chunk_size=10)
        assert count == 25

        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 25


class TestBulkUpsert:
    @pytest.mark.asyncio
    async def test_upsert_insert(self, session):
        bulk = BulkOperations(session)
        # First insert
        await bulk.insert(
            User,
            [
                {"name": "Alice", "email": "alice@upsert.com", "age": 25},
            ],
        )

        # Upsert — should update existing + insert new
        count = await bulk.upsert(
            User,
            [
                {"name": "Alice Updated", "email": "alice@upsert.com", "age": 26},
                {"name": "Bob", "email": "bob@upsert.com", "age": 30},
            ],
            conflict_columns=["email"],
            update_columns=["name", "age"],
        )
        assert count == 2

        result = await session.execute(select(User).where(User.email == "alice@upsert.com"))
        alice = result.scalar_one()
        assert alice.name == "Alice Updated"
        assert alice.age == 26


class TestBulkUpdate:
    @pytest.mark.asyncio
    async def test_update_batch(self, session):
        bulk = BulkOperations(session)

        # Create users
        await bulk.insert(
            User,
            [
                {"name": "A", "email": "a@batch.com", "age": 20},
                {"name": "B", "email": "b@batch.com", "age": 25},
            ],
        )

        result = await session.execute(select(User))
        users = result.scalars().all()

        # Batch update
        updates = [
            {"id": users[0].id, "name": "A Updated"},
            {"id": users[1].id, "name": "B Updated"},
        ]
        count = await bulk.update_batch(User, updates)
        assert count == 2

        # Verify
        result2 = await session.execute(select(User).where(User.id == users[0].id))
        assert result2.scalar_one().name == "A Updated"


class TestBulkDelete:
    @pytest.mark.asyncio
    async def test_delete_batch(self, session):
        bulk = BulkOperations(session)

        await bulk.insert(
            User,
            [
                {"name": "A", "email": "a@del.com", "age": 1},
                {"name": "B", "email": "b@del.com", "age": 2},
                {"name": "C", "email": "c@del.com", "age": 3},
            ],
        )

        result = await session.execute(select(User))
        users = result.scalars().all()
        ids_to_delete = [users[0].id, users[2].id]

        count = await bulk.delete_batch(User, ids_to_delete)
        assert count == 2

        remaining = await session.execute(select(User))
        assert len(remaining.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_delete_batch_empty(self, session):
        bulk = BulkOperations(session)
        count = await bulk.delete_batch(User, [])
        assert count == 0

    def test_repr(self, session):
        bulk = BulkOperations(session)
        assert "BulkOperations" in repr(bulk)
