from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..controller.base import Controller, ResourceController


class RouteType(str, Enum):
    HTTP = "http"
    BOT_COMMAND = "bot.command"
    BOT_MESSAGE = "bot.message"
    BOT_CALLBACK = "bot.callback"
    WEBSOCKET = "websocket"


@dataclass
class RateLimit:
    max_requests: int = 60
    window_seconds: int = 60


@dataclass
class Route:
    path: str
    handler: Any
    methods: list[str] = field(default_factory=lambda: ["GET"])
    route_type: RouteType = RouteType.HTTP
    name: str | None = None
    title: str | None = None
    description: str | None = None
    middleware: list[Any] = field(default_factory=list)
    rate_limit: RateLimit | None = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return self.name or f"{self.methods[0].lower()}:{self.path}"

    def __repr__(self) -> str:
        methods = ",".join(self.methods)
        return f"<Route [{methods}] {self.path} → {_handler_name(self.handler)}>"


class RouteCollector:
    """
    Collects route definitions with grouping support.

    Usage:
        routes = RouteCollector()

        with routes as r:
            r.get("/", home)

            with r.group(prefix="/api/v1", middleware=[Auth]) as r:
                r.get("/users", list_users, name="users.index")
                r.post("/users", create_user, name="users.store")

                with r.group(prefix="/admin", name="admin.") as r:
                    r.get("/stats", stats, name="stats")
                    # full name: admin.stats, full path: /api/v1/admin/stats
    """

    def __init__(self) -> None:
        self._routes: list[Route] = []
        self._prefix_stack: list[str] = []
        self._middleware_stack: list[list[Any]] = [[]]
        self._name_stack: list[str] = []

    @property
    def _current_prefix(self) -> str:
        return "".join(self._prefix_stack)

    @property
    def _current_middleware(self) -> list[Any]:
        result: list[Any] = []
        for mw in self._middleware_stack:
            result.extend(mw)
        return result

    @property
    def _current_name_prefix(self) -> str:
        return "".join(self._name_stack)

    def get(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["GET"], path, handler, **kw)

    def post(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["POST"], path, handler, **kw)

    def put(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["PUT"], path, handler, **kw)

    def patch(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["PATCH"], path, handler, **kw)

    def delete(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["DELETE"], path, handler, **kw)

    def head(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["HEAD"], path, handler, **kw)

    def options(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["OPTIONS"], path, handler, **kw)

    def any(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], path, handler, **kw)

    def match(self, methods: list[str], path: str, handler: Any, **kw: Any) -> Route:
        return self._add([m.upper() for m in methods], path, handler, **kw)

    def command(self, cmd: str, handler: Any, **kw: Any) -> Route:
        """Register a bot command handler (/start, /help, etc.)."""
        return self._add(["COMMAND"], cmd, handler, route_type=RouteType.BOT_COMMAND, **kw)

    def on_message(self, handler: Any, *, filters: Any = None, **kw: Any) -> Route:
        """Register a bot message handler."""
        meta = kw.pop("meta", {})

        if filters is not None:
            meta["filters"] = filters
        return self._add(["MESSAGE"], "", handler, route_type=RouteType.BOT_MESSAGE, meta=meta, **kw)

    def on_callback(self, handler: Any, *, filters: Any = None, **kw: Any) -> Route:
        """Register a bot callback query handler."""
        meta = kw.pop("meta", {})
        if filters is not None:
            meta["filters"] = filters
        return self._add(["CALLBACK"], "", handler, route_type=RouteType.BOT_CALLBACK, meta=meta, **kw)

    def websocket(self, path: str, handler: Any, **kw: Any) -> Route:
        return self._add(["WEBSOCKET"], path, handler, route_type=RouteType.WEBSOCKET, **kw)

    def resource(self, path: str, controller: Any, **kw: Any) -> list[Route]:
        """Register CRUD routes for a resource."""
        name_base = path.strip("/").replace("/", ".")
        routes: list[Route] = []

        mapping = [
            (["GET"], path, "index", f"{name_base}.index"),
            (["POST"], path, "store", f"{name_base}.store"),
            (["GET"], f"{path}/{{id}}", "show", f"{name_base}.show"),
            (["PUT"], f"{path}/{{id}}", "update", f"{name_base}.update"),
            (["PATCH"], f"{path}/{{id}}", "update", f"{name_base}.patch"),
            (["DELETE"], f"{path}/{{id}}", "destroy", f"{name_base}.destroy"),
        ]

        for methods, route_path, method_name, route_name in mapping:
            handler = getattr(controller, method_name, None)
            if handler is not None:
                routes.append(self._add(methods, route_path, handler, name=route_name, **kw))
        return routes

    def api_resource(self, path: str, controller: Any, **kw: Any) -> list[Route]:
        """Register API CRUD routes (no create/edit form routes)."""
        return self.resource(path, controller, **kw)

    def group(self, *, prefix: str = "", middleware: list[Any] | None = None, name: str = "") -> _RouteGroup:
        """Create a route group with shared prefix/middleware/name."""
        return _RouteGroup(self, prefix, middleware or [], name)

    def prefix(self, prefix: str) -> _RouteGroup:
        """Shorthand for group(prefix=...)."""
        return self.group(prefix=prefix)

    def middleware_group(self, *middleware: Any) -> _RouteGroup:
        """Shorthand for group(middleware=...)."""
        return self.group(middleware=list(middleware))

    def collect(self) -> list[Route]:
        """Return all collected routes."""
        return list(self._routes)

    def collect_by_type(self, route_type: RouteType) -> list[Route]:
        """Return routes filtered by type."""
        return [r for r in self._routes if r.route_type == route_type]

    def find(self, name: str) -> Route | None:
        """Find route by name."""
        for r in self._routes:
            if r.name == name:
                return r
        return None

    def clear(self) -> None:
        """Clear all routes."""
        self._routes.clear()

    def controller(self, controller_class: type[Controller], *, container: Any = None) -> list[Route]:
        """
        Register a decorator-based controller.

        Scans for @get/@post/etc. decorated methods,
        generates routes with controller's path prefix.

        Usage:
            with routes.group(prefix="/api/v1") as r:
                r.controller(UserController)
        """
        from ..controller.compiler import compile_controller

        compiled = compile_controller(controller_class, container)
        # Apply current group prefix/middleware/name
        result = []

        for r in compiled:
            full_path = self._current_prefix + r.path
            full_name = self._current_name_prefix + r.name if r.name else None
            all_middleware = self._current_middleware + r.middleware

            adjusted = Route(
                path=full_path,
                handler=r.handler,
                methods=r.methods,
                route_type=r.route_type,
                name=full_name,
                title=r.title,
                description=r.description,
                middleware=all_middleware,
                tags=r.tags,
                rate_limit=r.rate_limit,
                meta=r.meta,
            )
            self._routes.append(adjusted)
            result.append(adjusted)

        return result

    def resource_controller(
        self, path: str, controller_class: type[ResourceController], *, container: Any = None
    ) -> list[Route]:
        """
        Register a ResourceController with CRUD routes.

        Usage:
            with routes.group(prefix="/api/v1") as r:
                r.resource("/posts", PostController)
                # Generates:
                #   GET    /api/v1/posts          → posts.index
                #   POST   /api/v1/posts          → posts.store
                #   GET    /api/v1/posts/{id}      → posts.show
                #   PUT    /api/v1/posts/{id}      → posts.update
                #   DELETE /api/v1/posts/{id}      → posts.destroy
        """
        from ..controller.compiler import compile_resource

        full_base = self._current_prefix + path
        compiled = compile_resource(controller_class, container, path=full_base)
        result = []

        for r in compiled:
            full_name = self._current_name_prefix + r.name if r.name else None
            all_middleware = self._current_middleware + r.middleware

            adjusted = Route(
                path=r.path,
                handler=r.handler,
                methods=r.methods,
                route_type=r.route_type,
                name=full_name,
                title=r.title,
                description=r.description,
                middleware=all_middleware,
                tags=r.tags,
                rate_limit=r.rate_limit,
                meta=r.meta,
            )
            self._routes.append(adjusted)
            result.append(adjusted)
        return result

    def _add(
        self,
        methods: list[str],
        path: str,
        handler: Any,
        *,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        middleware: list[Any] | None = None,
        route_type: RouteType = RouteType.HTTP,
        rate_limit: RateLimit | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Route:
        full_path = self._current_prefix + path
        full_name = None

        if name:
            full_name = self._current_name_prefix + name
        all_middleware = self._current_middleware + (middleware or [])
        r = Route(
            path=full_path,
            handler=handler,
            methods=methods,
            route_type=route_type,
            name=full_name,
            title=title,
            description=description,
            middleware=all_middleware,
            rate_limit=rate_limit,
            tags=tags or [],
            meta=meta or {},
        )
        self._routes.append(r)
        return r

    def _push_group(self, prefix: str, middleware: list[Any], name: str) -> None:
        self._prefix_stack.append(prefix)
        self._middleware_stack.append(middleware)
        self._name_stack.append(name)

    def _pop_group(self) -> None:
        self._prefix_stack.pop()
        self._middleware_stack.pop()
        self._name_stack.pop()

    def __enter__(self) -> RouteCollector:
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self):
        return iter(self._routes)

    def __repr__(self) -> str:
        return f"<RouteCollector routes={len(self._routes)}>"


class _RouteGroup:
    """Context manager that pushes/pops prefix and middleware on the collector."""

    __slots__ = ("_collector", "_middleware", "_name", "_prefix")

    def __init__(self, collector: RouteCollector, prefix: str, middleware: list[Any], name: str) -> None:
        self._collector = collector
        self._prefix = prefix
        self._middleware = middleware
        self._name = name

    def __enter__(self) -> RouteCollector:
        self._collector._push_group(self._prefix, self._middleware, self._name)
        return self._collector

    def __exit__(self, *exc: Any) -> None:
        self._collector._pop_group()


def route() -> RouteCollector:
    """Create a new route collector."""
    return RouteCollector()


def _handler_name(handler: Any) -> str:
    if hasattr(handler, "__qualname__"):
        return handler.__qualname__
    if hasattr(handler, "__name__"):
        return handler.__name__
    return repr(handler)


class RouteURLGenerator:
    """
    Generate URLs from named routes.

    Like Laravel's route() helper:
        url = urls.generate("users.show", id=1)
        # → /api/v1/users/1

        url = urls.generate("users.index")
        # → /api/v1/users
    """

    def __init__(self, routes: list[Route]) -> None:
        self._routes: dict[str, Route] = {}
        for r in routes:
            if r.name:
                self._routes[r.name] = r

    def generate(self, name: str, **params: Any) -> str:
        """Generate URL for a named route, substituting parameters."""
        if name not in self._routes:
            raise KeyError(f"Route '{name}' not found")

        route = self._routes[name]
        path = route.path

        # Replace {param} and {param:type} patterns
        import re

        def replacer(match: re.Match) -> str:
            param_name = match.group(1).split(":")[0]
            if param_name in params:
                return str(params[param_name])
            return match.group(0)

        return re.sub(r"\{([^}]+)\}", replacer, path)

    def has(self, name: str) -> bool:
        return name in self._routes

    def names(self) -> list[str]:
        return list(self._routes.keys())

    def __repr__(self) -> str:
        return f"<RouteURLGenerator routes={len(self._routes)}>"


@dataclass
class MiddlewareEntry:
    """Middleware with priority — lower number = runs first."""

    middleware: Any
    priority: int = 50
    name: str = ""

    def __post_init__(self):
        if not self.name and hasattr(self.middleware, "__name__"):
            self.name = self.middleware.__name__

    def __lt__(self, other: MiddlewareEntry) -> bool:
        return self.priority < other.priority
