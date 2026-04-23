from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..exceptions import AuthorizationException
from .gate import Gate
from .policy import Policy, PolicyRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class AccessManager:
    """
    Central authorization manager — combines Gate + Policy + Casbin.

    Single entry point for all authorization checks.

    Usage:
        access = AccessManager()

        # Gate abilities
        access.gate.define("view-dashboard", lambda user: user.is_admin)

        # Policies
        access.policies.register(Post, PostPolicy())

        # Combined check
        if await access.can(user, "update", post):
            ...

        # Authorize or raise
        await access.authorize(user, "delete", post)

        # Check roles (via Casbin)
        if await access.has_role(user, "admin"):
            ...

    Resolution order:
      1. Gate.before hooks
      2. Gate abilities (if defined for this ability name)
      3. Policy (if resource has a registered policy)
      4. Casbin (if configured)
      5. Deny by default
    """

    def __init__(self) -> None:
        self.gate = Gate()
        self.policies = PolicyRegistry()
        self._casbin: Any | None = None  # CasbinGuard

    def set_casbin(self, casbin_guard: Any) -> None:
        """Attach CasbinGuard for RBAC/ABAC."""
        self._casbin = casbin_guard

    # ── Main API ──────────────────────────────────────────

    async def can(self, user: Any, ability: str, resource: Any = None) -> bool:
        """
        Can user perform ability on resource?
        Checks Gate → Policy → Casbin in order.
        """
        # 1. Try Gate (if ability defined)
        if self.gate.has(ability):
            if resource is not None:
                return await self.gate.allows(user, ability, resource)
            return await self.gate.allows(user, ability)

        # 2. Try Policy (if resource has a policy)
        if resource is not None:
            policy = self.policies.for_model(resource)
            if policy is not None:
                return await self.policies.check(user, ability, resource)

        # 3. Try Casbin
        if self._casbin is not None:
            user_id = self._get_user_id(user)
            resource_name = self._get_resource_name(resource)
            return await self._casbin.enforce(user_id, resource_name, ability)

        # 4. Deny by default
        return False

    async def cannot(self, user: Any, ability: str, resource: Any = None) -> bool:
        return not await self.can(user, ability, resource)

    async def authorize(self, user: Any, ability: str, resource: Any = None) -> None:
        """Check and raise AuthorizationException if denied."""
        if not await self.can(user, ability, resource):
            raise AuthorizationException(ability=ability, resource=resource)

    async def any(self, user: Any, abilities: list[str], resource: Any = None) -> bool:
        for ability in abilities:
            if await self.can(user, ability, resource):
                return True
        return False

    async def all(self, user: Any, abilities: list[str], resource: Any = None) -> bool:
        for ability in abilities:
            if not await self.can(user, ability, resource):
                return False
        return True

    # ── Role / Permission shortcuts ───────────────────────

    async def has_role(self, user: Any, role: str) -> bool:
        """Check if user has a role (via Casbin)."""
        if self._casbin is None:
            return False
        user_id = self._get_user_id(user)
        return await self._casbin.has_role(user_id, role)

    async def has_permission(self, user: Any, permission: str, resource: str = "*") -> bool:
        """Check if user has a permission (via Casbin)."""
        if self._casbin is None:
            return False
        user_id = self._get_user_id(user)
        return await self._casbin.enforce(user_id, resource, permission)

    async def has_any_role(self, user: Any, *roles: str) -> bool:
        for role in roles:
            if await self.has_role(user, role):
                return True
        return False

    async def has_all_roles(self, user: Any, *roles: str) -> bool:
        for role in roles:
            if not await self.has_role(user, role):
                return False
        return True

    # ── Convenience ───────────────────────────────────────

    def for_user(self, user: Any) -> _UserAccess:
        """Create user-bound accessor."""
        return _UserAccess(self, user)

    def define(self, ability: str, callback: Callable) -> AccessManager:
        """Shortcut: define a gate ability."""
        self.gate.define(ability, callback)
        return self

    def policy(self, model: type, policy: Policy) -> AccessManager:
        """Shortcut: register a policy."""
        self.policies.register(model, policy)
        return self

    # ── Internal ──────────────────────────────────────────

    @staticmethod
    def _get_user_id(user: Any) -> str:
        """Extract user identifier for Casbin."""
        if isinstance(user, str):
            return user
        if hasattr(user, "id"):
            return str(user.id)
        if hasattr(user, "username"):
            return str(user.username)
        return str(user)

    @staticmethod
    def _get_resource_name(resource: Any) -> str:
        """Extract resource name for Casbin."""
        if resource is None:
            return "*"
        if isinstance(resource, str):
            return resource
        if isinstance(resource, type):
            return resource.__name__.lower()
        return type(resource).__name__.lower()

    def __repr__(self) -> str:
        return f"<AccessManager gate={len(self.gate.abilities)} abilities, policies={len(self.policies.registered_models)} models, casbin={'yes' if self._casbin else 'no'}>"


class _UserAccess:
    """AccessManager bound to a specific user."""

    __slots__ = ("_access", "_user")

    def __init__(self, access: AccessManager, user: Any) -> None:
        self._access = access
        self._user = user

    async def can(self, ability: str, resource: Any = None) -> bool:
        return await self._access.can(self._user, ability, resource)

    async def cannot(self, ability: str, resource: Any = None) -> bool:
        return await self._access.cannot(self._user, ability, resource)

    async def authorize(self, ability: str, resource: Any = None) -> None:
        return await self._access.authorize(self._user, ability, resource)

    async def has_role(self, role: str) -> bool:
        return await self._access.has_role(self._user, role)

    async def has_permission(self, perm: str, resource: str = "*") -> bool:
        return await self._access.has_permission(self._user, perm, resource)
