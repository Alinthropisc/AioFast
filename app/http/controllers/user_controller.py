"""Example User controller.

Kept storage-free so the example app boots without a database. Swap the
in-memory list for a service/repository backed by the :class:`User` model.
"""

from __future__ import annotations

from typing import ClassVar

from core.controller.base import Controller
from core.controller.decorators import get


class UserController(Controller):
    path = "/users"
    tags: ClassVar[list[str]] = ["users"]

    _DEMO: ClassVar[list[dict]] = [
        {"id": 1, "name": "Ada Lovelace", "email": "ada@example.com"},
        {"id": 2, "name": "Alan Turing", "email": "alan@example.com"},
    ]

    @get(summary="List users")
    async def index(self) -> dict:
        return self.ok(self._DEMO)

    @get("/{user_id:int}", name="show", summary="Show user")
    async def show(self, user_id: int) -> dict:
        for user in self._DEMO:
            if user["id"] == user_id:
                return self.ok(user)
        return self.not_found("User")
