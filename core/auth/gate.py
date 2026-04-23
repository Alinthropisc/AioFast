from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..exceptions import AuthorizationException

logger = logging.getLogger(__name__)

# Callback types
AbilityCallback = Callable[..., Any]  # (user, *args) -> bool | None
HookCallback = Callable[..., Any]  # (user, ability, *args) -> bool | None


class Response:
    """Authorization response — allows/denies with message."""

    __slots__ = ("allowed", "message")

    def __init__(self, allowed: bool, message: str = "") -> None:
        self.allowed = allowed
        self.message = message

    @staticmethod
    def allow(message: str = "") -> Response:
        return Response(True, message)

    @staticmethod
    def deny(message: str = "This action is unauthorized.") -> Response:
        return Response(False, message)

    def __bool__(self) -> bool:
        return self.allowed

    def __repr__(self) -> str:
        status = "allowed" if self.allowed else "denied"
        return f"<Response {status} {self.message!r}>"


class Gate:
    """
    Gate — closure-based authorization.

    Like Laravel's Gate but async-first.

    Usage:
        gate = Gate()

        # Define abilities
        gate.define("edit-post", lambda user, post: user.id == post.author_id)
        gate.define("delete-post", lambda user, post: user.is_admin)

        # Global hooks
        gate.before(lambda user, ability: True if user.is_super_admin else None)

        # Check
        if await gate.allows(user, "edit-post", post):
            ...

        # Or raise
        await gate.authorize(user, "edit-post", post)
    """

    def __init__(self) -> None:
        self._abilities: dict[str, AbilityCallback] = {}
        self._before_hooks: list[HookCallback] = []
        self._after_hooks: list[HookCallback] = []

    # ── Define ────────────────────────────────────────────

    def define(self, ability: str, callback: AbilityCallback) -> Gate:
        """Register an ability check."""
        self._abilities[ability] = callback
        logger.debug("Gate: defined ability '%s'", ability)
        return self

    def has(self, ability: str) -> bool:
        """Check if ability is defined."""
        return ability in self._abilities

    @property
    def abilities(self) -> list[str]:
        return list(self._abilities.keys())

    # ── Hooks ─────────────────────────────────────────────

    def before(self, callback: HookCallback) -> Gate:
        """
        Run before every check.
        Return True → always allow.
        Return False → always deny.
        Return None → continue to ability check.
        """
        self._before_hooks.append(callback)
        return self

    def after(self, callback: HookCallback) -> Gate:
        """
        Run after every check.
        Can override the result.
        """
        self._after_hooks.append(callback)
        return self

    # ── Check ─────────────────────────────────────────────

    async def allows(self, user: Any, ability: str, *args: Any) -> bool:
        """Check if user is allowed to perform ability."""
        response = await self.inspect(user, ability, *args)
        return response.allowed

    async def denies(self, user: Any, ability: str, *args: Any) -> bool:
        """Check if user is denied."""
        return not await self.allows(user, ability, *args)

    async def authorize(self, user: Any, ability: str, *args: Any) -> Response:
        """
        Check and raise AuthorizationException if denied.
        Returns Response if allowed.
        """
        response = await self.inspect(user, ability, *args)

        if not response.allowed:
            raise AuthorizationException(
                response.message or "This action is unauthorized.", ability=ability, resource=args[0] if args else None
            )
        return response

    async def any(self, user: Any, abilities: list[str], *args: Any) -> bool:
        """Check if user has ANY of the given abilities."""
        for ability in abilities:
            if await self.allows(user, ability, *args):
                return True
        return False

    async def none(self, user: Any, abilities: list[str], *args: Any) -> bool:
        """Check if user has NONE of the given abilities."""
        return not await self.any(user, abilities, *args)

    async def all(self, user: Any, abilities: list[str], *args: Any) -> bool:
        """Check if user has ALL of the given abilities."""
        for ability in abilities:
            if not await self.allows(user, ability, *args):
                return False
        return True

    async def inspect(self, user: Any, ability: str, *args: Any) -> Response:
        """Full inspection — returns Response with details."""
        # Before hooks
        for hook in self._before_hooks:
            result = await self._call(hook, user, ability, *args)
            if result is True:
                return Response.allow("Allowed by before hook")
            if result is False:
                return Response.deny("Denied by before hook")
            if isinstance(result, Response):
                return result
            # None → continue
        # Main ability check
        callback = self._abilities.get(ability)

        if callback is None:
            return Response.deny(f"Ability '{ability}' is not defined.")
        result = await self._call(callback, user, *args)

        if isinstance(result, Response):
            response = result
        elif isinstance(result, bool):
            response = Response(result)
        else:
            response = Response.deny()

        # After hooks
        for hook in self._after_hooks:
            after_result = await self._call(hook, user, ability, result, *args)
            if isinstance(after_result, Response):
                response = after_result
            elif isinstance(after_result, bool):
                response = Response(after_result)
            # None → keep original result
        return response

    def for_user(self, user: Any) -> _UserGate:
        """Create a user-bound gate for convenience."""
        return _UserGate(self, user)

    async def _call(self, fn: Callable, *args: Any) -> Any:
        """Call sync or async callback."""
        import asyncio
        import inspect

        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        max_args = len(params)
        has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)

        call_args = args[:max_args] if not has_var else args
        result = fn(*call_args)

        if asyncio.iscoroutine(result):
            result = await result
        return result

    def __repr__(self) -> str:
        return f"<Gate abilities={self.abilities}>"


class _UserGate:
    """Gate bound to a specific user."""

    __slots__ = ("_gate", "_user")

    def __init__(self, gate: Gate, user: Any) -> None:
        self._gate = gate
        self._user = user

    async def can(self, ability: str, *args: Any) -> bool:
        return await self._gate.allows(self._user, ability, *args)

    async def cannot(self, ability: str, *args: Any) -> bool:
        return await self._gate.denies(self._user, ability, *args)

    async def authorize(self, ability: str, *args: Any) -> Response:
        return await self._gate.authorize(self._user, ability, *args)
