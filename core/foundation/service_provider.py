from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .application import Application


class ServiceProvider:
    def __init__(self, app: Application) -> None:
        self.app = app

    async def register(self) -> None:
        pass

    async def boot(self) -> None:
        pass

    def provides(self) -> list[Any]:
        return []

    @property
    def deferred(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
