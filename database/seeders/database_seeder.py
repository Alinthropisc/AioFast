"""Example seeders.

``DatabaseSeeder`` is the entry point — it calls the other seeders. Run it
against an ``AsyncSession``:

    async with session_factory() as session:
        await DatabaseSeeder(session).run()
        await session.commit()
"""

from __future__ import annotations

from app.models.user import User
from core.database.seeder import Seeder
from database.factories.user_factory import UserFactory


class UserSeeder(Seeder):
    async def run(self) -> None:
        # One deterministic admin, plus 10 random users.
        await self.create_one(
            User,
            name="Admin",
            email="admin@example.com",
            password="hashed-password-placeholder",
        )
        await UserFactory().create_many(self._session, 10)


class DatabaseSeeder(Seeder):
    async def run(self) -> None:
        await self.call(UserSeeder)
