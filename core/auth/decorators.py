from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

from ..exceptions import AuthorizationException, PermissionException, RoleException

if TYPE_CHECKING:
    from collections.abc import Callable


def authorize(ability: str, resource_param: str | None = None):
    """
    Decorator — check authorization before handler.

    Usage:
        @authorize("edit", resource_param="post")
        async def update_post(request, post: Post) -> Response:
            ...

        @authorize("view-dashboard")
        async def dashboard(request) -> Response:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user and resource from kwargs
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None:
                # Try first arg (request) → request.user
                for arg in args:
                    if hasattr(arg, "user"):
                        user = arg.user
                        break

            if user is None:
                raise AuthorizationException("No authenticated user found.", ability=ability)
            resource = kwargs.get(resource_param) if resource_param else None
            # Get AccessManager from app
            access = kwargs.get("_access_manager")

            if access is None:
                for arg in args:
                    if hasattr(arg, "app"):
                        app = arg.app
                        if hasattr(app, "state") and hasattr(app.state, "access"):
                            access = app.state.access
                        break

            if access is not None:
                await access.authorize(user, ability, resource)
            else:
                raise AuthorizationException("AccessManager not available.", ability=ability)
            return await fn(*args, **kwargs)

        wrapper._authorize_ability = ability  # ty:ignore[unresolved-attribute]
        return wrapper

    return decorator


def requires_role(*roles: str):
    """
    Decorator — require user to have any of the given roles.

    Usage:
        @requires_role("admin", "moderator")
        async def admin_panel(request) -> Response:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None:
                for arg in args:
                    if hasattr(arg, "user"):
                        user = arg.user
                        break

            if user is None:
                raise RoleException(roles[0], "No authenticated user.")
            access = kwargs.get("_access_manager")

            if access is None:
                for arg in args:
                    if hasattr(arg, "app"):
                        app = arg.app
                        if hasattr(app, "state") and hasattr(app.state, "access"):
                            access = app.state.access
                        break

            if access is not None:
                if not await access.has_any_role(user, *roles):
                    raise RoleException(roles[0], f"Requires one of roles: {', '.join(roles)}")
            else:
                # Fallback: check user.role attribute
                user_role = getattr(user, "role", None)
                if user_role not in roles:
                    raise RoleException(roles[0])

            return await fn(*args, **kwargs)

        wrapper._requires_roles = roles  # ty:ignore[unresolved-attribute]
        return wrapper

    return decorator


def requires_permission(*permissions: str):
    """
    Decorator — require user to have any of the given permissions.

    Usage:
        @requires_permission("posts.create", "posts.manage")
        async def create_post(request) -> Response:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None:
                for arg in args:
                    if hasattr(arg, "user"):
                        user = arg.user
                        break

            if user is None:
                raise PermissionException(permissions[0], "No user.")
            access = kwargs.get("_access_manager")

            if access is None:
                for arg in args:
                    if hasattr(arg, "app"):
                        app = arg.app
                        if hasattr(app, "state") and hasattr(app.state, "access"):
                            access = app.state.access
                        break

            if access is not None:
                for perm in permissions:
                    if await access.has_permission(user, perm):
                        return await fn(*args, **kwargs)
                raise PermissionException(permissions[0], f"Requires one of: {', '.join(permissions)}")
            else:
                raise PermissionException(permissions[0], "No AccessManager.")
            return await fn(*args, **kwargs)

        wrapper._requires_permissions = permissions  # ty:ignore[unresolved-attribute]
        return wrapper

    return decorator
