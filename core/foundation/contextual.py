from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .container import Container


class ContextualBindingBuilder:
    def __init__(self, container: Container, concrete: Any) -> None:
        self._container = container
        self._concrete = concrete
        self._abstract: Any = None

    def needs(self, abstract: Any) -> ContextualBindingBuilder:
        self._abstract = abstract
        return self

    def give(self, implementation: Any) -> Container:
        if self._concrete not in self._container._contextual:
            self._container._contextual[self._concrete] = {}
        self._container._contextual[self._concrete][self._abstract] = implementation
        return self._container
