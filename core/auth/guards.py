from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class Guard(ABC):
    """
    Auth guard — strategy for authenticating a request.
    """

    name: str = "base"

    @abstractmethod
    async def user(self, request: Any) -> Any | None:
        """Get authenticated user from request."""

    @abstractmethod
    async def validate(self, credentials: dict[str, Any]) -> Any | None:
        """Validate credentials. Returns user or None."""

    async def check(self, request: Any) -> bool:
        return await self.user(request) is not None

    async def id(self, request: Any) -> Any | None:
        u = await self.user(request)
        return getattr(u, "id", None) if u else None

    async def guest(self, request: Any) -> bool:
        return not await self.check(request)


async def _call_provider(fn: Callable, *args: Any) -> Any:
    """Call sync or async provider safely."""
    result = fn(*args)
    if asyncio.iscoroutine(result) or asyncio.isfuture(result):
        return await result
    return result


class GuardManager:
    """
    Manages multiple auth guards.

    Usage:
        manager = GuardManager()
        manager.register("jwt", JWTGuard(secret="..."))
        manager.register("api_key", ApiKeyGuard(repo=...))
        manager.set_default("jwt")

        user = await manager.guard("jwt").user(request)
        user = await manager.user(request)
        user = await manager.user_from_any(request, ["jwt", "api_key"])
    """

    def __init__(self) -> None:
        self._guards: dict[str, Guard] = {}
        self._default: str = "jwt"
        self._user_provider: Callable | None = None

    def register(self, name: str, guard: Guard) -> GuardManager:
        guard.name = name
        self._guards[name] = guard
        if len(self._guards) == 1:
            self._default = name
        logger.debug("Guard registered: %s", name)
        return self

    def set_default(self, name: str) -> GuardManager:
        if name not in self._guards:
            raise KeyError(f"Guard '{name}' not registered")
        self._default = name
        return self

    def set_user_provider(self, provider: Callable) -> GuardManager:
        self._user_provider = provider
        return self

    def guard(self, name: str | None = None) -> Guard:
        guard_name = name or self._default
        guard = self._guards.get(guard_name)
        if guard is None:
            raise KeyError(f"Guard '{guard_name}' not registered")
        return guard

    async def user(self, request: Any, guard: str | None = None) -> Any | None:
        return await self.guard(guard).user(request)

    async def user_from_any(self, request: Any, guards: list[str] | None = None) -> Any | None:
        guard_names = guards or list(self._guards.keys())
        for name in guard_names:
            user = await self.guard(name).user(request)
            if user is not None:
                return user
        return None

    async def check(self, request: Any, guard: str | None = None) -> bool:
        return await self.guard(guard).check(request)

    async def validate(self, credentials: dict[str, Any], guard: str | None = None) -> Any | None:
        return await self.guard(guard).validate(credentials)

    @property
    def guards(self) -> list[str]:
        return list(self._guards.keys())

    def __repr__(self) -> str:
        return f"<GuardManager guards={self.guards} default={self._default!r}>"


# ── JWT Guard ─────────────────────────────────────────────


class JWTGuard(Guard):
    """
    JWT Bearer token guard.

    Extracts token from:
      - Authorization: Bearer <token>
      - Query param: ?token=<token>
      - Cookie: access_token
    """

    name = "jwt"

    def __init__(
        self,
        token_manager: Any = None,
        user_provider: Callable | None = None,
        header: str = "Authorization",
        scheme: str = "Bearer",
        cookie_name: str | None = None,
        query_param: str | None = None,
    ) -> None:
        self._token_manager = token_manager
        self._user_provider = user_provider
        self._header = header
        self._scheme = scheme
        self._cookie_name = cookie_name
        self._query_param = query_param

    async def user(self, request: Any) -> Any | None:
        token = self._extract_token(request)
        if token is None:
            return None

        payload = self._token_manager.verify_access_token(token)
        if payload is None:
            return None

        # TokenPayload is a dataclass — access .sub directly
        user_id = payload.sub
        if user_id is None:
            return None

        if self._user_provider:
            return await _call_provider(self._user_provider, user_id)

        return payload

    async def validate(self, credentials: dict[str, Any]) -> Any | None:
        token = credentials.get("token")
        if token:
            return self._token_manager.verify_access_token(token)
        return None

    def _extract_token(self, request: Any) -> str | None:
        headers = getattr(request, "headers", {})
        auth_header = headers.get(self._header) or headers.get(self._header.lower())
        if auth_header and auth_header.startswith(f"{self._scheme} "):
            return auth_header[len(self._scheme) + 1 :]

        if self._query_param:
            query_params = getattr(request, "query_params", {})
            token = query_params.get(self._query_param)
            if token:
                return token

        if self._cookie_name:
            cookies = getattr(request, "cookies", {})
            token = cookies.get(self._cookie_name)
            if token:
                return token

        return None


# ── API Key Guard ─────────────────────────────────────────


class ApiKeyGuard(Guard):
    """
    API Key guard.

    Extracts from:
      - Header: X-API-Key
      - Query: ?api_key=<key>
    """

    name = "api_key"

    def __init__(
        self, key_provider: Callable | None = None, header: str = "X-API-Key", query_param: str = "api_key"
    ) -> None:
        self._key_provider = key_provider
        self._header = header
        self._query_param = query_param

    async def user(self, request: Any) -> Any | None:
        key = self._extract_key(request)
        if key is None:
            return None

        if self._key_provider:
            return await _call_provider(self._key_provider, key)
        return None

    async def validate(self, credentials: dict[str, Any]) -> Any | None:
        key = credentials.get("api_key")
        if key and self._key_provider:
            return await _call_provider(self._key_provider, key)
        return None

    def _extract_key(self, request: Any) -> str | None:
        headers = getattr(request, "headers", {})
        key = headers.get(self._header) or headers.get(self._header.lower())
        if key:
            return key

        query_params = getattr(request, "query_params", {})
        return query_params.get(self._query_param)


# ── Session Guard ─────────────────────────────────────────


class SessionGuard(Guard):
    """Session-based guard — for web apps with cookies."""

    name = "session"

    def __init__(self, session_key: str = "user_id", user_provider: Callable | None = None) -> None:
        self._session_key = session_key
        self._user_provider = user_provider

    async def user(self, request: Any) -> Any | None:
        session = getattr(request, "session", None)
        if session is None:
            return None

        user_id = session.get(self._session_key)
        if user_id is None:
            return None

        if self._user_provider:
            return await _call_provider(self._user_provider, user_id)
        return {"id": user_id}

    async def validate(self, credentials: dict[str, Any]) -> Any | None:
        return None


# ── Composite Guard ───────────────────────────────────────


class CompositeGuard(Guard):
    """Try multiple guards in order."""

    name = "composite"

    def __init__(self, *guards: Guard) -> None:
        self._guards = list(guards)

    async def user(self, request: Any) -> Any | None:
        for guard in self._guards:
            user = await guard.user(request)
            if user is not None:
                return user
        return None

    async def validate(self, credentials: dict[str, Any]) -> Any | None:
        for guard in self._guards:
            user = await guard.validate(credentials)
            if user is not None:
                return user
        return None
