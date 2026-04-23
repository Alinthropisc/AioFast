from __future__ import annotations

from typing import Any


class AuthorizationException(Exception):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "This action is unauthorized.",
        *,
        ability: str | None = None,
        resource: Any = None,
        status_code: int = 403,
    ) -> None:
        super().__init__(message)
        self.ability = ability
        self.resource = resource
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"<AuthorizationException ability={self.ability!r} status={self.status_code}>"


class RoleException(AuthorizationException):
    """Raised when user lacks required role."""

    def __init__(self, role: str, message: str | None = None) -> None:
        super().__init__(message or f"Role required: {role}", ability=f"role:{role}")
        self.role = role


class PermissionException(AuthorizationException):
    """Raised when user lacks required permission."""

    def __init__(self, permission: str, message: str | None = None) -> None:
        super().__init__(message or f"Permission required: {permission}", ability=f"permission:{permission}")
        self.permission = permission
