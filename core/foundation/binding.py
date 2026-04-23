from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class BindingType(Enum):
    TRANSIENT = auto()
    SINGLETON = auto()
    SCOPED = auto()
    INSTANCE = auto()


@dataclass
class Binding:
    abstract: Any
    concrete: Any
    binding_type: BindingType
    instance: Any | None = None
    tags: set[str] = field(default_factory=set)

    @property
    def is_resolved(self) -> bool:
        return self.instance is not None

    @property
    def is_shared(self) -> bool:
        return self.binding_type in (BindingType.SINGLETON, BindingType.INSTANCE)

    def reset(self) -> None:
        if self.binding_type != BindingType.INSTANCE:
            self.instance = None

    def __repr__(self) -> str:
        status = "resolved" if self.is_resolved else "pending"
        return f"<Binding {self.abstract!r} -> {self.concrete!r} [{self.binding_type.name}] ({status})>"
