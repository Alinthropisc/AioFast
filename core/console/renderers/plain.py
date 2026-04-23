from typing import Any

from .base import Renderer


class PlainRenderer(Renderer):
    def __init__(self, separator: str = "\t") -> None:
        self._sep = separator

    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        lines = [self._sep.join(headers)]
        for row in rows:
            lines.append(self._sep.join(str(c) for c in row))
        return "\n".join(lines)
