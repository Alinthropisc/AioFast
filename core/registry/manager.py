from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .adapter import AdapterState, BaseAdapter
from .health import HealthCheck, SystemHealth
from .route import MiddlewareEntry, Route, RouteCollector, RouteType, RouteURLGenerator

if TYPE_CHECKING:
    from ..foundation import Application

logger = logging.getLogger(__name__)


def _handler_name(handler: Any) -> str:
    if hasattr(handler, "__qualname__"):
        return handler.__qualname__
    if hasattr(handler, "__name__"):
        return handler.__name__
    return repr(handler)


class AdapterManager:
    """
    Manages framework adapters — Manager pattern.

    Holds all registered adapters (Litestar, Aiogram, etc.),
    distributes routes, and coordinates lifecycle.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}
        self._collectors: list[RouteCollector] = []
        self._app: Application | None = None
        self._configured: bool = False
        self._started: bool = False
        self._url_generator: RouteURLGenerator | None = None
        self._global_middleware: list[MiddlewareEntry] = []

    def register(self, adapter: BaseAdapter) -> AdapterManager:
        """Register a framework adapter."""
        if not adapter.name:
            raise ValueError(f"Adapter {adapter.__class__.__name__} has no name")
        self._adapters[adapter.name] = adapter
        logger.debug("Registered adapter: %s", adapter.name)
        return self

    async def health(self) -> SystemHealth:
        """Get health status of all adapters."""
        checks: list[HealthCheck] = []
        for adapter in self._adapters.values():
            check = await adapter.health_check()
            checks.append(check)
        from ..foundation import Application

        version = Application.VERSION if self._app else ""
        return SystemHealth.from_checks(checks, version)

    @property
    def urls(self) -> RouteURLGenerator:
        """Get URL generator for named routes."""
        if self._url_generator is None:
            self._url_generator = RouteURLGenerator(self.all_routes())
        return self._url_generator

    def url(self, name: str, **params: Any) -> str:
        """Shortcut: generate URL for a named route."""
        return self.urls.generate(name, **params)

    def add_global_middleware(self, middleware: Any, *, priority: int = 50, name: str = "") -> AdapterManager:
        """Add global middleware applied to all adapters."""
        self._global_middleware.append(MiddlewareEntry(middleware, priority, name))
        self._global_middleware.sort()
        return self

    def route_table(self) -> list[dict[str, Any]]:
        """
        Get route table — like Laravel's `route:list`.

        Returns list of dicts with route info for display.
        """
        rows = []
        for r in self.all_routes():
            rows.append(
                {
                    "methods": ",".join(r.methods),
                    "path": r.path,
                    "name": r.name or "",
                    "type": r.route_type.value,
                    "middleware": ",".join(str(m) for m in r.middleware) if r.middleware else "",
                    "handler": _handler_name(r.handler),  # ty:ignore[unresolved-reference]
                }
            )
        return rows

    def print_routes(self) -> None:
        """Print route table to stdout."""
        table = self.route_table()
        if not table:
            print("No routes registered.")
            return
        headers = ["Method", "Path", "Name", "Type", "Middleware", "Handler"]
        widths = [len(h) for h in headers]

        for row in table:
            vals = [
                row["methods"],
                row["path"],
                row["name"],
                row["type"],
                row["middleware"],
                row["handler"],
            ]
            for i, v in enumerate(vals):
                widths[i] = max(widths[i], len(v))

        sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        hdr = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=False)) + " |"
        print(sep)
        print(hdr)
        print(sep)

        for row in table:
            vals = [
                row["methods"],
                row["path"],
                row["name"],
                row["type"],
                row["middleware"],
                row["handler"],
            ]
            line = "| " + " | ".join(v.ljust(w) for v, w in zip(vals, widths, strict=False)) + " |"
            print(line)
        print(sep)

    @property
    def global_middleware(self) -> list[MiddlewareEntry]:
        return list(self._global_middleware)

    def get(self, name: str) -> BaseAdapter:
        """Get adapter by name."""
        if name not in self._adapters:
            available = list(self._adapters.keys())
            raise KeyError(f"Adapter '{name}' not found. Available: {available}")
        return self._adapters[name]

    def has(self, name: str) -> bool:
        return name in self._adapters

    @property
    def adapters(self) -> dict[str, BaseAdapter]:
        return dict(self._adapters)

    @property
    def adapter_names(self) -> list[str]:
        return list(self._adapters.keys())

    def add_routes(self, collector: RouteCollector) -> AdapterManager:
        """Add a route collector."""
        self._collectors.append(collector)
        return self

    def load_route_module(self, module: Any) -> AdapterManager:
        """
        Load routes from a module.
        Module should have a `register(routes: RouteCollector)` function
        or a `routes` RouteCollector attribute.
        """
        if hasattr(module, "register") and callable(module.register):
            collector = RouteCollector()
            module.register(collector)
            self._collectors.append(collector)
        elif hasattr(module, "routes"):
            routes = module.routes
            if isinstance(routes, RouteCollector):
                self._collectors.append(routes)
        else:
            raise ValueError(f"Module {module} has no 'register' function or 'routes' attribute")
        return self

    def all_routes(self) -> list[Route]:
        """Collect all routes from all collectors."""
        result: list[Route] = []
        for collector in self._collectors:
            result.extend(collector.collect())
        return result

    def routes_for(self, adapter_name: str) -> list[Route]:
        """Get routes matching an adapter's supported types."""
        adapter = self.get(adapter_name)
        return [r for r in self.all_routes() if adapter.accepts_route_type(r.route_type)]

    async def configure(self, app: Application) -> None:
        """Configure all adapters with the app."""
        self._app = app

        for name, adapter in self._adapters.items():
            config = self._get_adapter_config(app, name)
            try:
                await adapter.configure(app, config)
                logger.info("Adapter configured: %s", name)
            except Exception as e:
                adapter._state = AdapterState.ERROR
                logger.error("Failed to configure adapter %s: %s", name, e)
                raise

        self._configured = True

    async def start(self) -> None:
        """Compile routes and start all adapters."""
        if not self._configured:
            raise RuntimeError("AdapterManager not configured. Call configure() first.")

        routes = self.all_routes()
        logger.info("Total routes collected: %d", len(routes))

        for name, adapter in self._adapters.items():
            if adapter.state == AdapterState.ERROR:
                logger.warning("Skipping errored adapter: %s", name)
                continue

            matching = [r for r in routes if adapter.accepts_route_type(r.route_type)]
            if matching:
                adapter.compile_routes(matching)
                logger.info("Compiled %d routes for %s", len(matching), name)

            try:
                await adapter.start()
                logger.info("Adapter started: %s", name)
            except Exception as e:
                adapter._state = AdapterState.ERROR
                logger.error("Failed to start adapter %s: %s", name, e)
                raise
        self._started = True

    async def stop(self) -> None:
        """Stop all adapters."""
        for name, adapter in self._adapters.items():
            if adapter.is_started:
                try:
                    await adapter.stop()
                    logger.info("Adapter stopped: %s", name)
                except Exception as e:
                    logger.error("Error stopping adapter %s: %s", name, e)
        self._started = False

    def get_asgi_app(self) -> Any | None:
        """Get the ASGI app from the first HTTP adapter (usually Litestar)."""
        for adapter in self._adapters.values():
            if RouteType.HTTP in adapter.supported_route_types:
                return adapter.get_native_app()
        return None

    def get_bot_dispatcher(self) -> Any | None:
        """Get the bot dispatcher (usually Aiogram)."""
        for adapter in self._adapters.values():
            if RouteType.BOT_COMMAND in adapter.supported_route_types:
                return adapter.get_native_app()
        return None

    def _get_adapter_config(self, app: Application, adapter_name: str) -> dict[str, Any]:
        """Get adapter-specific config from ConfigurationManager."""
        try:
            # Try to get config synchronously from bindings
            if app.has("config"):
                binding = app._bindings.get("config")
                if binding and binding.instance:
                    config_manager = binding.instance
                    return config_manager.get(adapter_name, {}) or {}
        except Exception:
            pass
        return {}

    async def aclose(self) -> None:
        await self.stop()

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def is_started(self) -> bool:
        return self._started

    def __repr__(self) -> str:
        names = list(self._adapters.keys())
        routes = len(self.all_routes()) if self._collectors else 0
        return f"<AdapterManager adapters={names} routes={routes} started={self._started}>"
