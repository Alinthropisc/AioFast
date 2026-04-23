from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command import Command


class CommandMiddleware(ABC):
    @abstractmethod
    async def handle(self, command: "Command", next_handler: Callable) -> int:
        pass


class MiddlewarePipeline:
    def __init__(self, middlewares: list[CommandMiddleware] | None = None) -> None:
        self._middlewares = middlewares or []

    def pipe(self, middleware: CommandMiddleware) -> "MiddlewarePipeline":
        self._middlewares.append(middleware)
        return self

    async def run(self, command: "Command", final: Callable) -> int:

        async def build_chain(index: int) -> int:
            if index >= len(self._middlewares):
                return await final(command)
            mw = self._middlewares[index]

            async def next_handler(cmd: "Command") -> int:
                return await build_chain(index + 1)

            return await mw.handle(command, next_handler)

        return await build_chain(0)
