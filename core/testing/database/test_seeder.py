from __future__ import annotations

import itertools

import pytest
from sqlalchemy import select

from core.database.seeder import Factory, Seeder
from core.testing.database.conftest import User


class UserSeeder(Seeder):
    async def run(self):
        data_list = [
            {
                "name": f"User{i}",
                "email": f"user{i}@example.com",
                "is_active": True,
                "role": "user",
                "age": 20 + i,
            }
            for i in range(5)
        ]

        return await self.create(User, data_list)


class TestSeeder:
    @pytest.mark.asyncio
    async def test_seed(self, session):
        seeder = UserSeeder(session)
        data = [
            {"name": "Admin", "email": "admin@app.com"},
            {"name": "User", "email": "user@app.com"},
        ]
        await seeder.create(User, data)  # ← передаём СПИСОК целиком

        result = await session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_create_one(self, session):
        seeder = UserSeeder(session)
        user = await seeder.create_one(User, name="Solo", email="solo@app.com")
        assert user.id is not None
        assert user.name == "Solo"

    @pytest.mark.asyncio
    async def test_truncate(self, session):
        seeder = UserSeeder(session)
        await seeder.run()  # создаёт 5

        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 5  # проверяем что создались

        await seeder.truncate(User)

        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_call_child_seeders(self, session):
        class ParentSeeder(Seeder):
            async def run(self):
                await self.call(UserSeeder)

        seeder = ParentSeeder(session)
        await seeder.run()

        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 5  # ← UserSeeder создаёт 5, не 2


class UserFactory(Factory[User]):
    model = User
    _counter = itertools.count(1)

    def definition(self) -> dict:
        n = next(self._counter)
        return {
            "name": f"User_{n}",
            "email": f"user_{n}@test.com",
        }


class TestFactory:
    def test_make(self):
        factory = UserFactory()
        user = factory.make()
        assert isinstance(user, User)
        assert user.name is not None

    def test_make_with_override(self):
        factory = UserFactory()
        user = factory.make(name="Custom")
        assert user.name == "Custom"

    def test_make_many(self):
        factory = UserFactory()
        users = factory.make_many(3)
        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_create(self, session):
        factory = UserFactory()
        user = await factory.create(session, email="factory@t.com")
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_many(self, session):
        factory = UserFactory()
        # ❌ email="batch@t.com" для всех 5 → UNIQUE constraint
        # ✅ без override — каждый получит уникальный email из definition()
        users = await factory.create_many(session, 5)
        assert len(users) == 5
        # проверим что email уникальны
        emails = [u.email for u in users]
        assert len(set(emails)) == 5

    def test_state(self):
        factory = UserFactory()
        factory.state(name="Admin")
        user = factory.make()
        assert user.name == "Admin"
