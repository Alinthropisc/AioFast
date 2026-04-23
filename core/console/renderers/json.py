import json as json_module
from typing import Any

from .base import Renderer


class JsonRenderer(Renderer):
    def __init__(self, indent: int = 2) -> None:
        self._indent = indent

    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        data = [dict(zip(headers, row, strict=False)) for row in rows]
        return json_module.dumps(data, indent=self._indent, default=str, ensure_ascii=False)
