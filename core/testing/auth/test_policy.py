from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.auth.policy import Policy, PolicyRegistry
from core.exceptions import AuthorizationException


@dataclass
class User:
    id: int
    name: str
    is_admin: bool = False


@dataclass
class Post:
    id: int
    author_id: int
    title: str = "Test"


class PostPolicy(Policy):
    def before(self, user, ability):
        if user.is_admin:
            return True
        return None

    def view(self, user, post):  # ty:ignore[invalid-method-override]
        return True

    def update(self, user, post):  # ty:ignore[invalid-method-override]
        return user.id == post.author_id

    def delete(self, user, post):  # ty:ignore[invalid-method-override]
        return user.id == post.author_id

    def create(self, user):
        return True


class TestPolicy:
    @pytest.mark.asyncio
    async def test_check_allowed(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=1, name="Alice")
        post = Post(id=1, author_id=1)

        assert await registry.check(user, "update", post) is True

    @pytest.mark.asyncio
    async def test_check_denied(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=2, name="Bob")
        post = Post(id=1, author_id=1)

        assert await registry.check(user, "update", post) is False

    @pytest.mark.asyncio
    async def test_before_admin_bypass(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        admin = User(id=99, name="Admin", is_admin=True)
        post = Post(id=1, author_id=1)

        assert await registry.check(admin, "delete", post) is True

    @pytest.mark.asyncio
    async def test_view_anyone(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=999, name="Random")
        post = Post(id=1, author_id=1)

        assert await registry.check(user, "view", post) is True

    @pytest.mark.asyncio
    async def test_create_no_resource(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=1, name="Alice")
        # create doesn't need resource instance
        # But we need model type for policy lookup
        # So pass Post class or None
        assert await registry.check(user, "create", Post(id=0, author_id=0)) is True

    @pytest.mark.asyncio
    async def test_authorize_raises(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=2, name="Bob")
        post = Post(id=1, author_id=1)

        with pytest.raises(AuthorizationException):
            await registry.authorize(user, "delete", post)

    @pytest.mark.asyncio
    async def test_no_policy_returns_false(self):
        registry = PolicyRegistry()
        user = User(id=1, name="Alice")
        assert await registry.check(user, "view", "unknown") is False

    @pytest.mark.asyncio
    async def test_undefined_method_returns_false(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())

        user = User(id=1, name="Alice")
        post = Post(id=1, author_id=1)

        assert await registry.check(user, "nonexistent", post) is False

    def test_registered_models(self):
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())
        assert Post in registry.registered_models
