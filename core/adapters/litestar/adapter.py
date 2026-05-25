from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any

from ...registry.adapter import AdapterState, BaseAdapter
from ...registry.route import Route, RouteType

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Litestar

    from ...foundation import Application

logger = logging.getLogger(__name__)


class LitestarAdapter(BaseAdapter):
    """
    Bridges AIoFast with Litestar.

    - Compiles Route definitions → Litestar route handlers
    - Bridges DI: Container bindings → Litestar Provide()
    - Bridges middleware
    - Creates and manages Litestar app instance
    """

    name = "litestar"
    supported_route_types = {RouteType.HTTP, RouteType.WEBSOCKET}

    def __init__(self) -> None:
        super().__init__()
        self._litestar: Litestar | None = None
        self._compiled_handlers: list[Any] = []
        self._native_handlers: list[Any] = []
        self._middleware: list[Any] = []
        self._dependencies: dict[str, Any] = {}
        self._exception_handlers: dict[Any, Any] = {}
        self._on_startup: list[Callable] = []
        self._on_shutdown: list[Callable] = []
        self._litestar_kwargs: dict[str, Any] = {}
        self._plugins: list[Any] = []

    async def configure(self, app: Application, config: dict[str, Any]) -> None:
        try:
            import litestar  # noqa: F401
        except ImportError as exc:
            raise ImportError("litestar is required for LitestarAdapter. Install: pip install litestar") from exc
        self._app = app
        self._config = config
        self._state = AdapterState.CONFIGURED

    def compile_routes(self, routes: list[Route]) -> None:
        from litestar import route as litestar_route
        from litestar.handlers import HTTPRouteHandler

        for route_def in routes:
            if route_def.route_type != RouteType.HTTP:
                continue

            # Already a native Litestar handler — pass through
            if isinstance(route_def.handler, HTTPRouteHandler):
                self._compiled_handlers.append(route_def.handler)
                continue

            # Skip if handler is None
            if route_def.handler is None:
                continue

            # Compile to Litestar handler
            try:
                handler = litestar_route(
                    route_def.path,
                    http_method=[m.upper() for m in route_def.methods],  # ty:ignore[invalid-argument-type]
                    name=route_def.name,
                    opt={
                        "tags": route_def.tags,
                        "description": route_def.description,
                    }
                    if route_def.tags or route_def.description
                    else None,
                )(route_def.handler)

                self._compiled_handlers.append(handler)

            except Exception as e:
                logger.error("Failed to compile route %s: %s", route_def.path, e)
                raise

    async def start(self) -> None:
        from litestar import Litestar

        from .dependency import build_container_dependencies
        from .middleware import create_container_middleware

        # Build DI bridge
        auto_deps = build_container_dependencies(self._app)  # ty:ignore[invalid-argument-type]
        all_deps = {**auto_deps, **self._dependencies}
        # Build middleware — container scope first
        all_middleware: list[Any] = [
            create_container_middleware(self._app),  # ty:ignore[invalid-argument-type]
        ]
        all_middleware.extend(self._middleware)
        # All handlers
        all_handlers = self._compiled_handlers + self._native_handlers
        # Boot/shutdown hooks
        app_ref = self._app

        async def _on_startup(litestar_app: Litestar) -> None:
            for hook in self._on_startup:
                result = hook()
                if inspect.isawaitable(result):
                    await result

        async def _on_shutdown(litestar_app: Litestar) -> None:
            for hook in self._on_shutdown:
                result = hook()
                if inspect.isawaitable(result):
                    await result
            await app_ref.shutdown()  # ty:ignore[unresolved-attribute]

        # Create Litestar app
        self._litestar = Litestar(
            route_handlers=all_handlers,
            middleware=all_middleware or None,
            dependencies=all_deps or None,
            exception_handlers=self._exception_handlers or None,
            plugins=self._plugins or None,
            debug=self._config.get("debug", self._app.is_debug),  # ty: ignore[unresolved-attribute]
            on_startup=[_on_startup] if self._on_startup else None,
            on_shutdown=[_on_shutdown],
            **self._litestar_kwargs,
        )  # ty:ignore[unresolved-attribute]
        # Store in container
        self._app.instance("litestar", self._litestar)  # ty:ignore[unresolved-attribute]
        self._app.instance(Litestar, self._litestar)  # ty:ignore[unresolved-attribute]
        self._state = AdapterState.STARTED
        logger.info(
            "Litestar started — %d handlers, %d middleware, %d dependencies",
            len(all_handlers),
            len(all_middleware),
            len(all_deps),
        )

    async def stop(self) -> None:
        self._state = AdapterState.STOPPED

    def get_native_app(self) -> Litestar | None:
        return self._litestar

    def add_route_handler(self, *handlers: Any) -> LitestarAdapter:
        """Add native Litestar handlers/controllers."""
        self._native_handlers.extend(handlers)
        return self

    def add_middleware(self, *middleware: Any) -> LitestarAdapter:
        self._middleware.extend(middleware)
        return self

    def add_dependency(self, name: str, provider: Any) -> LitestarAdapter:
        self._dependencies[name] = provider
        return self

    def add_exception_handler(self, exc_class: type, handler: Callable) -> LitestarAdapter:
        self._exception_handlers[exc_class] = handler
        return self

    def add_plugin(self, plugin: Any) -> LitestarAdapter:
        self._plugins.append(plugin)
        return self

    def on_startup(self, handler: Callable) -> LitestarAdapter:
        self._on_startup.append(handler)
        return self

    def on_shutdown(self, handler: Callable) -> LitestarAdapter:
        self._on_shutdown.append(handler)
        return self

    def set_options(self, **kwargs: Any) -> LitestarAdapter:
        """Pass extra kwargs to Litestar constructor."""
        self._litestar_kwargs.update(kwargs)
        return self
