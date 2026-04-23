from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...foundation.application import Application


def build_container_dependencies(app: Application) -> dict[str, Any]:
    """
    Build Litestar Provide() dependencies from AIoFast container.
    """
    from litestar.di import Provide

    deps: dict[str, Any] = {}

    # Always provide the app
    async def provide_app() -> Any:  # ← Any вместо "Application"
        return app

    deps["app"] = Provide(provide_app)

    # Create providers for class-based bindings
    for abstract, _binding in app.get_bindings().items():
        if not isinstance(abstract, type):
            continue
        if abstract.__module__.startswith(("aiofast.foundation", "builtins")):
            continue

        dep_name = _type_to_dep_name(abstract)
        if dep_name in deps:
            continue

        deps[dep_name] = _make_provider(app, abstract)

    return deps


def make_dependency(app: Application, abstract: Any, name: str | None = None) -> Any:
    """Create a single Litestar Provide for a container binding."""
    from litestar.di import Provide

    dep_name = name or _type_to_dep_name(abstract)
    return dep_name, Provide(_make_factory(app, abstract))


def _make_provider(app: Application, abstract: Any) -> Any:
    from litestar.di import Provide

    return Provide(_make_factory(app, abstract))


def _make_factory(app: Application, abstract: Any) -> Callable:
    async def _resolver() -> Any:  # ← Any вместо неявного
        return await app.make(abstract)

    _resolver.__qualname__ = f"provide_{abstract.__name__}"
    return _resolver


def _type_to_dep_name(cls: type) -> str:
    """Convert class name to dependency name: UserService → user_service."""
    name = cls.__name__
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
