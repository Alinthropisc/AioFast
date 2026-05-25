from __future__ import annotations

import contextlib
import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...foundation.application import Application


async def resolve_handler_dependencies(
    app: Application, handler: Callable, existing_data: dict[str, Any]
) -> dict[str, Any]:
    from typing import get_type_hints

    hints: dict[str, Any] = {}
    try:
        hints = get_type_hints(handler)
    except Exception:
        # Fallback: use raw annotations from signature
        # (handles local classes + from __future__ import annotations)
        sig = inspect.signature(handler)
        for name, param in sig.parameters.items():
            ann = param.annotation
            # Use the annotation only if it's already a type (not a string)
            if ann is not inspect.Parameter.empty and isinstance(ann, type):
                hints[name] = ann
    result = dict(existing_data)
    sig = inspect.signature(handler)
    SKIP = (str, int, float, bool, bytes, list, dict, tuple, set, type(None))

    for name, param in sig.parameters.items():
        if name in result:
            continue
        annotation = hints.get(name, param.annotation)

        if annotation is inspect.Parameter.empty:
            continue

        if annotation in SKIP:
            continue

        if not isinstance(annotation, type):
            continue

        with contextlib.suppress(Exception):
            result[name] = await app.make(annotation)

    return result


def build_bot_dependencies(app: Application) -> dict[str, Any]:
    """Build commonly used bot dependencies."""
    deps: dict[str, Any] = {
        "app": app,
        "container": app,
    }
    return deps
