from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .command import Command
    from .input import ArgvInput

logger = logging.getLogger(__name__)


@dataclass
class CommandStarting:
    command: Command
    input: ArgvInput | None = None


@dataclass
class CommandFinished:
    command: Command
    exit_code: int
    elapsed: float = 0.0


@dataclass
class CommandFailed:
    command: Command
    exception: Exception
    exit_code: int = 1


@dataclass
class CommandSkipped:
    command_name: str
    reason: str = ""


class EventDispatcher:
    def __init__(self) -> None:
        self._listeners: dict[type, list[Callable]] = {}
        self._wildcard: list[Callable] = []

    def listen(self, event_type: type, callback: Callable) -> EventDispatcher:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        return self

    def on_any(self, callback: Callable) -> EventDispatcher:
        self._wildcard.append(callback)
        return self

    async def dispatch(self, event: Any) -> None:
        event_type = type(event)

        for cb in self._wildcard:
            await self._invoke(cb, event)

        for cb in self._listeners.get(event_type, []):
            await self._invoke(cb, event)

    def forget(self, event_type: type) -> None:
        self._listeners.pop(event_type, None)

    def flush(self) -> None:
        self._listeners.clear()
        self._wildcard.clear()

    @staticmethod
    async def _invoke(callback: Callable, event: Any) -> None:
        try:
            result = callback(event)
            if inspect.isawaitable(result):
                await result
        except Exception as e:
            logger.warning("Event listener error: %s", e)

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values()) + len(self._wildcard)
        return f"<EventDispatcher listeners={total}>"
