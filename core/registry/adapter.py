from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from .health import HealthCheck, HealthStatus

if TYPE_CHECKING:
    from ..foundation import Application
    from .route import Route, RouteType


class AdapterState(Enum):
    CREATED = auto()
    CONFIGURED = auto()
    STARTED = auto()
    STOPPED = auto()
    ERROR = auto()


class BaseAdapter(ABC):
    """
    Base adapter — Strategy pattern.

    Each adapter bridges AIoFast with a specific framework.
    Declares which route types it handles.
    Compiles abstract Route definitions into native framework format.
    """

    name: str = ""
    supported_route_types: set[RouteType] = set()

    def __init__(self) -> None:
        self._state: AdapterState = AdapterState.CREATED
        self._app: Application | None = None
        self._config: dict[str, Any] = {}
        self._route_count: int = 0
        self._started_at: float | None = None
        self._error: Exception | None = None

    @abstractmethod
    async def configure(self, app: Application, config: dict[str, Any]) -> None:
        """Configure the adapter with app reference and config."""

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter — create native app, register handlers."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop and clean up."""

    @abstractmethod
    def compile_routes(self, routes: list[Route]) -> None:
        """Compile abstract routes into native framework format."""

    def get_native_app(self) -> Any | None:
        """Return the native framework app instance (Litestar, Dispatcher, etc.)."""
        return None

    def accepts_route_type(self, route_type: RouteType) -> bool:
        return route_type in self.supported_route_types

    async def health_check(self) -> HealthCheck:
        """Override for custom health checks."""
        if self._state == AdapterState.ERROR:
            return HealthCheck(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(self._error) if self._error else "Adapter error",
            )
        if self._state == AdapterState.STARTED:
            uptime = time.time() - self._started_at if self._started_at else 0
            return HealthCheck(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Running",
                details={"uptime_seconds": round(uptime, 1), "routes": self._route_count},
            )  # ty:ignore[unresolved-attribute]
        return HealthCheck(name=self.name, status=HealthStatus.UNKNOWN, message=f"State: {self._state.name}")

    def mark_started(self) -> None:
        self._state = AdapterState.STARTED
        self._started_at = time.time()

    def mark_stopped(self) -> None:
        self._state = AdapterState.STOPPED

    def mark_error(self, error: Exception) -> None:
        self._state = AdapterState.ERROR
        self._error = error

    @property
    def state(self) -> AdapterState:
        return self._state

    @property
    def is_configured(self) -> bool:
        return self._state in (AdapterState.CONFIGURED, AdapterState.STARTED)

    @property
    def is_started(self) -> bool:
        return self._state == AdapterState.STARTED

    @property
    def uptime_seconds(self) -> float:
        if self._started_at and self._state == AdapterState.STARTED:
            return time.time() - self._started_at
        return 0.0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} state={self._state.name} routes={self._route_count}>"  # ty:ignore[unresolved-attribute]
