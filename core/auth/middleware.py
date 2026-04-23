from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..exceptions import AuthorizationException

if TYPE_CHECKING:
    from collections.abc import Callable

    from .access import AccessManager

logger = logging.getLogger(__name__)


class AuthorizationMiddleware:
    """
    Middleware — check route-level authorization.

    Usage (Litestar):
        @get("/admin", middleware=[AuthorizationMiddleware(access, role="admin")])
        async def admin():
            ...

    Usage (generic):
        middleware = AuthorizationMiddleware(access)
        middleware.require_role("admin")
        middleware.require_ability("view-dashboard")
    """

    def __init__(
        self,
        access: AccessManager,
        *,
        role: str | None = None,
        roles: list[str] | None = None,
        ability: str | None = None,
        permission: str | None = None,
    ) -> None:
        self._access = access
        self._role = role
        self._roles = roles or []
        self._ability = ability
        self._permission = permission

    async def __call__(self, request: Any, handler: Callable) -> Any:
        """ASGI-style middleware call."""
        user = getattr(request, "user", None)

        if user is None:
            raise AuthorizationException("Authentication required.")
        # Check role
        all_roles = list(self._roles)

        if self._role:
            all_roles.append(self._role)

        if all_roles and not await self._access.has_any_role(user, *all_roles):
            raise AuthorizationException(f"Requires role: {', '.join(all_roles)}", ability=f"role:{all_roles[0]}")

        # Check ability
        if self._ability:
            await self._access.authorize(user, self._ability)

        # Check permission
        if self._permission:
            has = await self._access.has_permission(user, self._permission)
            if not has:
                raise AuthorizationException(f"Permission required: {self._permission}", ability=self._permission)
        return await handler(request)

    def __repr__(self) -> str:
        parts = []
        if self._role:
            parts.append(f"role={self._role}")
        if self._ability:
            parts.append(f"ability={self._ability}")
        if self._permission:
            parts.append(f"permission={self._permission}")
        return f"<AuthorizationMiddleware {' '.join(parts)}>"
