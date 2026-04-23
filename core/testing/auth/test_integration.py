from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.auth.access import AccessManager
from core.auth.casbin_guard import CasbinGuard
from core.auth.policy import Policy


@dataclass
class User:
    id: int
    name: str


@dataclass
class Post:
    id: int
    author_id: int


class PostPolicy(Policy):
    def view(self, user, post):  # ty:ignore[invalid-method-override]
        return True

    def update(self, user, post):  # ty:ignore[invalid-method-override]
        return user.id == post.author_id


class TestFullIntegration:
    """Test Gate + Policy + Casbin together."""

    @pytest.mark.asyncio
    async def test_gate_policy_casbin_combined(self):
        # Setup
        access = AccessManager()

        # Gate
        access.define("dashboard", lambda u: True)

        # Policy
        access.policy(Post, PostPolicy())

        # Casbin
        guard = CasbinGuard()
        await guard.init_rbac()
        await guard.add_role_for_user("1", "admin")
        await guard.add_permission_for_role("admin", "system", "manage")
        access.set_casbin(guard)

        user = User(id=1, name="Alice")
        post = Post(id=1, author_id=1)
        other_post = Post(id=2, author_id=99)

        # Gate ability
        assert await access.can(user, "dashboard") is True

        # Policy check
        assert await access.can(user, "update", post) is True
        assert await access.can(user, "update", other_post) is False

        # Casbin RBAC
        assert await access.has_role(user, "admin") is True
        assert await access.has_permission(user, "manage", "system") is True

        # Convenience
        ua = access.for_user(user)
        assert await ua.can("dashboard") is True
        assert await ua.has_role("admin") is True

        await guard.close()

    @pytest.mark.asyncio
    async def test_casbin_fallback(self):
        """When no Gate or Policy, falls back to Casbin."""
        access = AccessManager()

        guard = CasbinGuard()
        await guard.init_rbac()
        await guard.add_role_for_user("1", "editor")
        await guard.add_permission_for_role("editor", "posts", "edit")
        access.set_casbin(guard)

        user = User(id=1, name="Alice")

        # No gate or policy for "edit" + "posts"
        # Falls through to Casbin
        assert await access.can(user, "edit", "posts") is True
        assert await access.can(user, "delete", "posts") is False

        await guard.close()
