"""Example User factory — generates fake users with Faker.

from database.factories.user_factory import UserFactory

user = UserFactory().make()                       # in-memory
users = await UserFactory().create_many(session, 10)  # persisted
"""

from __future__ import annotations

from typing import Any

from app.models.user import User
from core.database.seeder import Factory


class UserFactory(Factory[User]):
    model = User

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.faker.name(),
            "email": self.faker.unique.email(),
            "password": "hashed-password-placeholder",
        }
