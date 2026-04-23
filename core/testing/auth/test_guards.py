from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.auth.guards import ApiKeyGuard, GuardManager, JWTGuard, SessionGuard
from core.auth.tokens import TokenManager


@dataclass
class FakeRequest:
    headers: dict
    cookies: dict = None  # ty:ignore[invalid-assignment]
    query_params: dict = None  # ty:ignore[invalid-assignment]
    session: dict = None  # ty:ignore[invalid-assignment]

    def __post_init__(self):
        self.cookies = self.cookies or {}
        self.query_params = self.query_params or {}
        self.session = self.session or {}


@dataclass
class FakeUser:
    id: int
    name: str


class TestJWTGuard:
    @pytest.mark.asyncio
    async def test_authenticate(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        users = {"1": FakeUser(id=1, name="Alice")}

        guard = JWTGuard(
            token_manager=tm,
            # sync lambda — guards.py handles both sync/async
            user_provider=lambda uid: users.get(uid),
        )

        pair = tm.issue("1")
        request = FakeRequest(headers={"Authorization": f"Bearer {pair.access_token}"})

        user = await guard.user(request)
        assert user is not None
        assert user.name == "Alice"

    @pytest.mark.asyncio
    async def test_authenticate_async_provider(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        users = {"1": FakeUser(id=1, name="Alice")}

        # async provider
        async def find_user(uid):
            return users.get(uid)

        guard = JWTGuard(
            token_manager=tm,
            user_provider=find_user,
        )

        pair = tm.issue("1")
        request = FakeRequest(headers={"Authorization": f"Bearer {pair.access_token}"})

        user = await guard.user(request)
        assert user is not None
        assert user.name == "Alice"

    @pytest.mark.asyncio
    async def test_no_token(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        guard = JWTGuard(token_manager=tm)
        request = FakeRequest(headers={})
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        guard = JWTGuard(token_manager=tm)
        request = FakeRequest(headers={"Authorization": "Bearer invalid"})
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_no_provider_returns_payload(self):
        """Without user_provider, returns TokenPayload."""
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        guard = JWTGuard(token_manager=tm)  # no user_provider

        pair = tm.issue("42")
        request = FakeRequest(headers={"Authorization": f"Bearer {pair.access_token}"})

        result = await guard.user(request)
        assert result is not None
        assert result.sub == "42"

    @pytest.mark.asyncio
    async def test_extract_from_cookie(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        guard = JWTGuard(token_manager=tm, cookie_name="access_token")

        pair = tm.issue("1")
        request = FakeRequest(
            headers={},
            cookies={"access_token": pair.access_token},
        )

        result = await guard.user(request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_from_query(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        guard = JWTGuard(token_manager=tm, query_param="token")

        pair = tm.issue("1")
        request = FakeRequest(
            headers={},
            query_params={"token": pair.access_token},
        )

        result = await guard.user(request)
        assert result is not None


class TestApiKeyGuard:
    @pytest.mark.asyncio
    async def test_authenticate_sync(self):
        """Sync key_provider."""
        users = {"key123": FakeUser(id=1, name="Bot")}
        guard = ApiKeyGuard(key_provider=lambda k: users.get(k))

        request = FakeRequest(headers={"X-API-Key": "key123"})
        user = await guard.user(request)
        assert user is not None
        assert user.name == "Bot"

    @pytest.mark.asyncio
    async def test_authenticate_async(self):
        """Async key_provider."""
        users = {"key456": FakeUser(id=2, name="AsyncBot")}

        async def find_by_key(k):
            return users.get(k)

        guard = ApiKeyGuard(key_provider=find_by_key)

        request = FakeRequest(headers={"X-API-Key": "key456"})
        user = await guard.user(request)
        assert user is not None
        assert user.name == "AsyncBot"

    @pytest.mark.asyncio
    async def test_no_key(self):
        guard = ApiKeyGuard(key_provider=lambda k: None)
        request = FakeRequest(headers={})
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_invalid_key(self):
        guard = ApiKeyGuard(key_provider=lambda k: None)
        request = FakeRequest(headers={"X-API-Key": "wrong"})
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_extract_from_query(self):
        users = {"qkey": FakeUser(id=3, name="QueryBot")}
        guard = ApiKeyGuard(key_provider=lambda k: users.get(k))

        request = FakeRequest(
            headers={},
            query_params={"api_key": "qkey"},
        )
        user = await guard.user(request)
        assert user is not None
        assert user.name == "QueryBot"


class TestSessionGuard:
    @pytest.mark.asyncio
    async def test_authenticate(self):
        users = {"1": FakeUser(id=1, name="Web User")}
        guard = SessionGuard(user_provider=lambda uid: users.get(uid))

        request = FakeRequest(headers={}, session={"user_id": "1"})
        user = await guard.user(request)
        assert user is not None
        assert user.name == "Web User"

    @pytest.mark.asyncio
    async def test_no_session(self):
        guard = SessionGuard()
        request = FakeRequest(headers={})
        request.session = None  # ty:ignore[invalid-assignment]
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_no_user_in_session(self):
        guard = SessionGuard()
        request = FakeRequest(headers={}, session={})
        assert await guard.user(request) is None

    @pytest.mark.asyncio
    async def test_no_provider_returns_dict(self):
        guard = SessionGuard()  # no user_provider
        request = FakeRequest(headers={}, session={"user_id": "42"})
        result = await guard.user(request)
        assert result == {"id": "42"}


class TestGuardManager:
    @pytest.mark.asyncio
    async def test_multiple_guards(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        users = {"1": FakeUser(id=1, name="Alice")}

        manager = GuardManager()
        manager.register(
            "jwt",
            JWTGuard(
                token_manager=tm,
                user_provider=lambda uid: users.get(uid),
            ),
        )
        manager.register(
            "api_key",
            ApiKeyGuard(
                key_provider=lambda k: users.get("1") if k == "my-key" else None,
            ),
        )

        # JWT
        pair = tm.issue("1")
        req = FakeRequest(headers={"Authorization": f"Bearer {pair.access_token}"})
        user = await manager.user(req, "jwt")
        assert user is not None
        assert user.name == "Alice"

        # API Key
        req2 = FakeRequest(headers={"X-API-Key": "my-key"})
        user2 = await manager.user(req2, "api_key")
        assert user2 is not None
        assert user2.name == "Alice"

    @pytest.mark.asyncio
    async def test_user_from_any(self):
        manager = GuardManager()
        manager.register("fail", ApiKeyGuard(key_provider=lambda k: None))
        manager.register(
            "ok",
            ApiKeyGuard(
                key_provider=lambda k: FakeUser(1, "Found") if k == "x" else None,
            ),
        )

        req = FakeRequest(headers={"X-API-Key": "x"})
        user = await manager.user_from_any(req)
        assert user is not None
        assert user.name == "Found"

    @pytest.mark.asyncio
    async def test_user_from_any_none(self):
        manager = GuardManager()
        manager.register("g1", ApiKeyGuard(key_provider=lambda k: None))
        manager.register("g2", ApiKeyGuard(key_provider=lambda k: None))

        req = FakeRequest(headers={"X-API-Key": "nothing"})
        user = await manager.user_from_any(req)
        assert user is None

    @pytest.mark.asyncio
    async def test_default_guard(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        manager = GuardManager()
        manager.register("jwt", JWTGuard(token_manager=tm))

        assert manager.guard().name == "jwt"

    @pytest.mark.asyncio
    async def test_set_default(self):
        manager = GuardManager()
        manager.register("a", ApiKeyGuard())
        manager.register("b", ApiKeyGuard())
        manager.set_default("b")
        assert manager.guard().name == "b"

    @pytest.mark.asyncio
    async def test_unknown_guard(self):
        manager = GuardManager()
        with pytest.raises(KeyError, match="not registered"):
            manager.guard("nonexistent")

    @pytest.mark.asyncio
    async def test_set_default_unknown(self):
        manager = GuardManager()
        with pytest.raises(KeyError):
            manager.set_default("nope")

    @pytest.mark.asyncio
    async def test_check(self):
        tm = TokenManager(secret="test-secret-key-long-enough-32chars!")
        manager = GuardManager()
        manager.register("jwt", JWTGuard(token_manager=tm))

        pair = tm.issue("1")
        req_auth = FakeRequest(headers={"Authorization": f"Bearer {pair.access_token}"})
        req_no_auth = FakeRequest(headers={})

        assert await manager.check(req_auth) is True
        assert await manager.check(req_no_auth) is False

    def test_guards_list(self):
        manager = GuardManager()
        manager.register("jwt", JWTGuard())
        manager.register("api", ApiKeyGuard())
        assert set(manager.guards) == {"jwt", "api"}

    def test_repr(self):
        manager = GuardManager()
        manager.register("jwt", JWTGuard())
        r = repr(manager)
        assert "GuardManager" in r
        assert "jwt" in r
