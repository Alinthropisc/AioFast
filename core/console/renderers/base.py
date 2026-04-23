from abc import ABC, abstractmethod
from typing import Any


class Renderer(ABC):
    @abstractmethod
    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        pass
