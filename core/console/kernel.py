from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from .events import EventDispatcher
from .loader import CommandLoader

if TYPE_CHECKING:
    from .command import Command
    from .middleware import CommandMiddleware

logger = logging.getLogger(__name__)


class ConsoleKernel:
    def __init__(self, app: Any = None) -> None:
        self._app = app
        self._loader = CommandLoader()
        self._global_middleware: list[CommandMiddleware] = []
        self._command_paths: list[tuple[str, str]] = []
        self._events = EventDispatcher()
        self._bootstrapped = False

    # ── Registration ──────────────────────────────────────

    def register(self, command_cls: type[Command]) -> ConsoleKernel:
        self._loader.register(command_cls)
        return self

    def register_many(self, *command_classes: type[Command]) -> ConsoleKernel:
        for cls in command_classes:
            self.register(cls)
        return self

    def add_path(self, path: str, base_module: str = "") -> ConsoleKernel:
        self._command_paths.append((path, base_module))
        return self

    def use(self, middleware: CommandMiddleware) -> ConsoleKernel:
        self._global_middleware.append(middleware)
        return self

    # ── Discovery & Bootstrap ─────────────────────────────

    def discover(self) -> ConsoleKernel:
        for path, base_module in self._command_paths:
            if os.path.exists(path):
                logger.debug("Discovering commands in: %s", path)
                self._loader.discover(path, base_module)
        return self

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        self.discover()
        self._bootstrapped = True
        logger.info("Console kernel bootstrapped: %d commands", len(self._loader))

    # ── Access ────────────────────────────────────────────

    def find(self, name: str) -> type[Command] | None:
        return self._loader.get(name)

    def all(self) -> dict[str, type[Command]]:
        return self._loader.all()

    def grouped(self) -> dict[str, list[type[Command]]]:
        return self._loader.grouped()

    def has(self, name: str) -> bool:
        return self._loader.has(name)

    @property
    def global_middleware(self) -> list[CommandMiddleware]:
        return list(self._global_middleware)

    @property
    def loader(self) -> CommandLoader:
        return self._loader

    @property
    def events(self) -> EventDispatcher:
        return self._events

    def __repr__(self) -> str:
        return f"<ConsoleKernel commands={len(self._loader)}>"
