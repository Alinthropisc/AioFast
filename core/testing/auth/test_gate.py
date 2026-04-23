from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.auth.gate import Gate, Response
from core.exceptions import AuthorizationException


@dataclass
class FakeUser:
    id: int
    name: str
    is_admin: bool = False
    is_super_admin: bool = False


@dataclass
class FakePost:
    id: int
    author_id: int
    title: str = "Test"


class TestGate:
    @pytest.mark.asyncio
    async def test_define_and_allows(self):
        gate = Gate()
        gate.define("edit", lambda user, post: user.id == post.author_id)

        user = FakeUser(id=1, name="Alice")
        post = FakePost(id=1, author_id=1)

        assert await gate.allows(user, "edit", post) is True

    @pytest.mark.asyncio
    async def test_denies(self):
        gate = Gate()
        gate.define("edit", lambda user, post: user.id == post.author_id)

        user = FakeUser(id=2, name="Bob")
        post = FakePost(id=1, author_id=1)

        assert await gate.denies(user, "edit", post) is True

    @pytest.mark.asyncio
    async def test_authorize_passes(self):
        gate = Gate()
        gate.define("view", lambda user: True)

        user = FakeUser(id=1, name="Alice")
        response = await gate.authorize(user, "view")
        assert response.allowed

    @pytest.mark.asyncio
    async def test_authorize_raises(self):
        gate = Gate()
        gate.define("delete", lambda user: user.is_admin)

        user = FakeUser(id=1, name="Alice", is_admin=False)

        with pytest.raises(AuthorizationException):
            await gate.authorize(user, "delete")

    @pytest.mark.asyncio
    async def test_before_hook_allow(self):
        gate = Gate()
        gate.before(lambda user, ability: True if user.is_super_admin else None)
        gate.define("delete", lambda user: False)

        super_admin = FakeUser(id=1, name="Root", is_super_admin=True)
        assert await gate.allows(super_admin, "delete") is True

    @pytest.mark.asyncio
    async def test_before_hook_deny(self):
        gate = Gate()
        gate.before(lambda user, ability: False if not user.is_admin else None)
        gate.define("view", lambda user: True)

        user = FakeUser(id=1, name="Alice", is_admin=False)
        assert await gate.allows(user, "view") is False

    @pytest.mark.asyncio
    async def test_before_hook_pass_through(self):
        gate = Gate()
        gate.before(lambda user, ability: None)
        gate.define("view", lambda user: True)

        user = FakeUser(id=1, name="Alice")
        assert await gate.allows(user, "view") is True

    @pytest.mark.asyncio
    async def test_undefined_ability(self):
        gate = Gate()
        user = FakeUser(id=1, name="Alice")
        assert await gate.allows(user, "fly") is False

    @pytest.mark.asyncio
    async def test_any(self):
        gate = Gate()
        gate.define("read", lambda user: True)
        gate.define("write", lambda user: False)

        user = FakeUser(id=1, name="Alice")
        assert await gate.any(user, ["read", "write"]) is True
        assert await gate.any(user, ["write"]) is False

    @pytest.mark.asyncio
    async def test_all(self):
        gate = Gate()
        gate.define("read", lambda user: True)
        gate.define("write", lambda user: True)

        user = FakeUser(id=1, name="Alice")
        assert await gate.all(user, ["read", "write"]) is True

        gate.define("delete", lambda user: False)
        assert await gate.all(user, ["read", "delete"]) is False

    @pytest.mark.asyncio
    async def test_response_object(self):
        gate = Gate()
        gate.define(
            "publish",
            lambda user: Response.allow("OK") if user.is_admin else Response.deny("No"),
        )

        admin = FakeUser(id=1, name="Admin", is_admin=True)
        result = await gate.inspect(admin, "publish")
        assert result.allowed
        assert result.message == "OK"

    @pytest.mark.asyncio
    async def test_for_user(self):
        gate = Gate()
        gate.define("view", lambda user: True)

        user = FakeUser(id=1, name="Alice")
        user_gate = gate.for_user(user)

        assert await user_gate.can("view") is True
        assert await user_gate.cannot("view") is False

    def test_has_ability(self):
        gate = Gate()
        gate.define("edit", lambda u: True)
        assert gate.has("edit")
        assert not gate.has("fly")

    @pytest.mark.asyncio
    async def test_async_callback(self):
        gate = Gate()

        async def check(user):
            return user.is_admin

        gate.define("admin-check", check)

        admin = FakeUser(id=1, name="Admin", is_admin=True)
        assert await gate.allows(admin, "admin-check") is True
