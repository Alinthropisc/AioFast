from typing import Any

from .base import Renderer
from .csv import CsvRenderer
from .json import JsonRenderer
from .plain import PlainRenderer
from .table import TableRenderer
from .xml import XmlRenderer
from .yaml import YamlRenderer


class RendererManager:
    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {
            "table": TableRenderer(),
            "json": JsonRenderer(),
            "csv": CsvRenderer(),
            "plain": PlainRenderer(),
            "yaml": YamlRenderer(),
            "xml": XmlRenderer(),
        }
        self._default = "table"

    def register(self, name: str, renderer: Renderer) -> None:
        self._renderers[name] = renderer

    def get(self, name: str) -> Renderer:
        return self._renderers.get(name, self._renderers[self._default])

    def has(self, name: str) -> bool:
        return name in self._renderers

    def available(self) -> list[str]:
        return list(self._renderers.keys())

    def render(self, name: str, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        renderer = self.get(name)
        return renderer.render(headers, rows, title)

    @property
    def default(self) -> str:
        return self._default

    @default.setter
    def default(self, name: str) -> None:
        if name in self._renderers:
            self._default = name
