from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def _route_action(
    methods: list[str],
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    """Internal: mark a method with route metadata."""

    def decorator(method: Callable) -> Callable:
        method._route_meta = {  # type: ignore[attr-defined]
            "methods": methods,
            "path": path,
            "name": name,
            "middleware": middleware or [],
            "tags": tags or [],
            "summary": summary,
            "description": description,
        }
        return method

    return decorator


def get(
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    """Mark method as GET handler."""
    return _route_action(
        ["GET"], path, name=name, middleware=middleware, tags=tags, summary=summary, description=description
    )


def post(
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    return _route_action(
        ["POST"], path, name=name, middleware=middleware, tags=tags, summary=summary, description=description
    )


def put(
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    return _route_action(
        ["PUT"], path, name=name, middleware=middleware, tags=tags, summary=summary, description=description
    )


def patch(
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    return _route_action(
        ["PATCH"], path, name=name, middleware=middleware, tags=tags, summary=summary, description=description
    )


def delete(
    path: str = "",
    *,
    name: str | None = None,
    middleware: list[Any] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> Callable:
    return _route_action(
        ["DELETE"], path, name=name, middleware=middleware, tags=tags, summary=summary, description=description
    )


def head(path: str = "", **kw: Any) -> Callable:
    return _route_action(["HEAD"], path, **kw)


def options(path: str = "", **kw: Any) -> Callable:
    return _route_action(["OPTIONS"], path, **kw)


def any(path: str = "", **kw: Any) -> Callable:
    return _route_action(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], path, **kw)


def middleware(*middlewares: Any) -> Callable:
    """Add middleware to a controller method."""

    def decorator(method: Callable) -> Callable:
        if not hasattr(method, "_route_meta"):
            method._extra_middleware = list(middlewares)  # type: ignore
        else:
            method._route_meta["middleware"].extend(middlewares)  # type: ignore
        return method

    return decorator


def has_route_meta(method: Any) -> bool:
    """Check if a method has route metadata."""
    return hasattr(method, "_route_meta")


def get_route_meta(method: Any) -> dict[str, Any] | None:
    """Get route metadata from a method."""
    return getattr(method, "_route_meta", None)
