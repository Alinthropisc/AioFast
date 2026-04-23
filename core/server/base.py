from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServerType(Enum):
    UVICORN = "uvicorn"
    GRANIAN = "granian"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"
    ssl_keyfile: str | None = None
    ssl_certfile: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseServer(ABC):
    """
    Base server abstraction.

    Server = process that listens on a port and
    forwards requests to an ASGI/RSGI app.

    NOT an adapter — servers don't handle routes.
    """

    name: str = ""
    server_type: ServerType = ServerType.UVICORN

    def __init__(self, config: ServerConfig | None = None) -> None:
        self._config = config or ServerConfig()
        self._running = False

    @abstractmethod
    async def serve(self, app: Any) -> None:
        """Start serving the ASGI/RSGI app (blocking)."""

    @abstractmethod
    def run(self, app: Any) -> None:
        """Synchronous entry point."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if this server is installed."""
        return False

    @property
    def config(self) -> ServerConfig:
        return self._config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._config.host}:{self._config.port} workers={self._config.workers}>"
