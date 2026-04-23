from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.auth.access import AccessManager
from core.auth.policy import Policy
from core.exceptions import AuthorizationException


@dataclass
class User:
    id: int
    name: str
    is_admin: bool = False


@dataclass
class Article:
    id: int
    author_id: int


class ArticlePolicy(Policy):
    def view(self, user, article):  # ty:ignore[invalid-method-override]
        return True

    def update(self, user, article):  # ty:ignore[invalid-method-override]
        return user.id == article.author_id

    def delete(self, user, article):  # ty:ignore[invalid-method-override]
        return user.is_admin


class TestAccessManager:
    @pytest.mark.asyncio
    async def test_gate_ability(self):
        access = AccessManager()
        access.define("dashboard", lambda user: user.is_admin)

        admin = User(id=1, name="Admin", is_admin=True)
        user = User(id=2, name="User")

        assert await access.can(admin, "dashboard") is True
        assert await access.can(user, "dashboard") is False

    @pytest.mark.asyncio
    async def test_policy_check(self):
        access = AccessManager()
        access.policy(Article, ArticlePolicy())

        user = User(id=1, name="Alice")
        article = Article(id=1, author_id=1)

        assert await access.can(user, "update", article) is True

    @pytest.mark.asyncio
    async def test_policy_denied(self):
        access = AccessManager()
        access.policy(Article, ArticlePolicy())

        user = User(id=2, name="Bob")
        article = Article(id=1, author_id=1)

        assert await access.can(user, "update", article) is False

    @pytest.mark.asyncio
    async def test_authorize_raises(self):
        access = AccessManager()
        access.policy(Article, ArticlePolicy())

        user = User(id=2, name="Bob", is_admin=False)
        article = Article(id=1, author_id=1)

        with pytest.raises(AuthorizationException):
            await access.authorize(user, "delete", article)

    @pytest.mark.asyncio
    async def test_cannot(self):
        access = AccessManager()
        access.define("fly", lambda user: False)

        user = User(id=1, name="Alice")
        assert await access.cannot(user, "fly") is True

    @pytest.mark.asyncio
    async def test_any_abilities(self):
        access = AccessManager()
        access.define("read", lambda u: True)
        access.define("write", lambda u: False)

        user = User(id=1, name="Alice")
        assert await access.any(user, ["read", "write"]) is True
        assert await access.any(user, ["write"]) is False

    @pytest.mark.asyncio
    async def test_all_abilities(self):
        access = AccessManager()
        access.define("read", lambda u: True)
        access.define("write", lambda u: True)

        user = User(id=1, name="Alice")
        assert await access.all(user, ["read", "write"]) is True

    @pytest.mark.asyncio
    async def test_for_user(self):
        access = AccessManager()
        access.define("view", lambda u: True)

        user = User(id=1, name="Alice")
        ua = access.for_user(user)

        assert await ua.can("view") is True
        assert await ua.cannot("view") is False

    @pytest.mark.asyncio
    async def test_default_deny(self):
        access = AccessManager()
        user = User(id=1, name="Alice")
        assert await access.can(user, "undefined") is False

    @pytest.mark.asyncio
    async def test_gate_takes_priority_over_policy(self):
        access = AccessManager()
        # Gate says yes
        access.define("update", lambda u, a: True)
        # Policy would say no
        access.policy(Article, ArticlePolicy())

        user = User(id=999, name="Stranger")
        article = Article(id=1, author_id=1)

        # Gate is checked first since ability is defined
        assert await access.can(user, "update", article) is True
