from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .binding import BindingType

if TYPE_CHECKING:
    from .container import Container


class ScopedContainer:
    def __init__(self, parent: Container, name: str = "request") -> None:
        self._parent = parent
        self._name = name
        self._instances: dict[Any, Any] = {}

    async def make(self, abstract: Any, *args: Any, **kwargs: Any) -> Any:
        if abstract in self._instances:
            return self._instances[abstract]

        if abstract in self._parent._bindings:
            binding = self._parent._bindings[abstract]
            if binding.binding_type == BindingType.SCOPED:
                obj = await self._parent._resolve_binding(binding, *args, **kwargs)
                self._instances[abstract] = obj
                return obj
        return await self._parent.make(abstract, *args, **kwargs)

    def has(self, abstract: Any) -> bool:
        return abstract in self._instances or self._parent.has(abstract)

    async def close(self) -> None:
        for instance in self._instances.values():
            await self._parent._try_close(instance)
        self._instances.clear()

    async def __aenter__(self) -> ScopedContainer:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"<ScopedContainer name={self._name!r} instances={len(self._instances)}>"
