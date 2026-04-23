from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any

from .base import Controller, ResourceController
from .decorators import get_route_meta

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..foundation.application import Application
    from ..registry.route import Route, RouteCollector


def compile_controller(controller_class: type[Controller], container: Application | None = None) -> list[Route]:
    """Compile a decorator-based Controller into Route objects."""
    from ..registry.route import Route, RouteType

    routes: list[Route] = []
    base_path = controller_class.path.rstrip("/")
    name_prefix = controller_class.get_name_prefix()
    class_middleware = list(controller_class.middleware)
    class_tags = list(controller_class.tags)

    for attr_name in dir(controller_class):
        if attr_name.startswith("_"):
            continue
        method = getattr(controller_class, attr_name, None)

        if method is None or not callable(method):
            continue
        meta = get_route_meta(method)

        if meta is None:
            continue
        method_path = meta["path"]
        full_path = base_path + method_path if method_path else base_path

        if not full_path:
            full_path = "/"
        route_name = None

        route_name = name_prefix + meta["name"] if meta.get("name") else name_prefix + attr_name
        all_middleware = class_middleware + meta.get("middleware", [])
        all_tags = class_tags + meta.get("tags", [])
        handler = _make_handler(controller_class, attr_name, container)
        routes.append(
            Route(
                path=full_path,
                handler=handler,
                methods=meta["methods"],
                name=route_name,
                title=meta.get("summary"),
                description=meta.get("description"),
                middleware=all_middleware,
                tags=all_tags,
                route_type=RouteType.HTTP,
            )
        )
    return routes


def compile_resource(
    controller_class: type[ResourceController],
    container: Application | None = None,
    *,
    path: str | None = None,
    methods: list[str] | None = None,
) -> list[Route]:
    """
    Compile a ResourceController into CRUD Route objects.

    Args:
        controller_class: The ResourceController subclass
        container: Optional container for DI
        path: Override the controller's path
        methods: Only include these methods (overrides only/exclude)
    """
    from ..registry.route import Route, RouteType

    routes: list[Route] = []
    base_path = (path or controller_class.path).rstrip("/")
    name_prefix = controller_class.get_name_prefix()
    class_middleware = list(controller_class.middleware)
    class_tags = list(controller_class.tags)
    id_param = controller_class.id_param
    id_type = controller_class.id_type

    if methods is not None:
        available = [m for m in methods if hasattr(controller_class, m)]
    else:
        available = controller_class.get_resource_methods()

    for method_name in available:
        if method_name not in ResourceController.RESOURCE_MAP:
            continue
        http_method, path_suffix, name_suffix = ResourceController.RESOURCE_MAP[method_name]
        method_path = path_suffix.replace("{id_param}", f"{{{id_param}:{id_type}}}")
        full_path = base_path + method_path

        if not full_path:
            full_path = "/"
        route_name = name_prefix + name_suffix
        handler = _make_handler(controller_class, method_name, container)
        routes.append(
            Route(
                path=full_path,
                handler=handler,
                methods=[http_method],
                name=route_name,
                middleware=class_middleware,
                tags=class_tags,
                route_type=RouteType.HTTP,
            )
        )
    return routes


def _make_handler(
    controller_class: type[Controller], method_name: str, container: Application | None = None
) -> Callable:
    """
    Create handler that:
      1. Resolves controller from container (DI)
      2. Calls before_action()
      3. Calls authorize() — returns 403 if False
      4. Calls validate() for store/update
      5. Calls the action method
      6. Calls after_action()
    """
    original_method = getattr(controller_class, method_name)

    # Actions that receive data (trigger validate)
    DATA_ACTIONS = {"store", "create", "update"}

    @functools.wraps(original_method)
    async def handler(*args: Any, **kwargs: Any) -> Any:

        from ..validation.errors import ValidationError as AppValidationError

        try:
            from pydantic import ValidationError as PydanticValidationError

            _validation_errors = (ValueError, TypeError, AppValidationError, PydanticValidationError)
        except ImportError:
            _validation_errors = (ValueError, TypeError, AppValidationError)
        # 1. Resolve controller
        if container is not None:
            ctrl = await container.make(controller_class)
        else:
            ctrl = controller_class()
        # 2. before_action
        await ctrl.before_action(method_name, **kwargs)
        # 3. authorize
        authorized = await ctrl.authorize(method_name, **kwargs)

        if not authorized:
            return ctrl.forbidden()

        # 4. validate (for data actions)
        if method_name in DATA_ACTIONS:
            data = kwargs.get("data")
            try:
                validated = await ctrl.validate(method_name, data)
                if validated is not None and data is not None:
                    kwargs["data"] = validated
            except (ValueError, TypeError) as e:
                return ctrl.error(message="Validation Error", status=422, errors=str(e))
            except _validation_errors as e:  # ← все типы
                return ctrl.error(
                    message="Validation Error",
                    status=422,
                    errors=str(e),
                )
        # 5. Call action
        result = await getattr(ctrl, method_name)(*args, **kwargs)
        # 6. after_action
        result = await ctrl.after_action(method_name, result, **kwargs)

        return result

    # Fix signature: remove 'self'
    try:
        sig = inspect.signature(original_method)
        params = [p for name, p in sig.parameters.items() if name != "self"]
        handler.__signature__ = sig.replace(parameters=params)  # ty:ignore[unresolved-attribute]
    except (ValueError, TypeError):
        pass

    handler.__controller__ = controller_class  # ty:ignore[unresolved-attribute]
    handler.__method_name__ = method_name  # ty:ignore[unresolved-attribute]
    handler.__qualname__ = f"{controller_class.__name__}.{method_name}"
    return handler


def register_controller(
    collector: RouteCollector, controller_class: type[Controller], container: Application | None = None
) -> list[Route]:
    routes = compile_controller(controller_class, container)
    for r in routes:
        collector._routes.append(r)
    return routes


def register_resource(
    collector: RouteCollector,
    controller_class: type[ResourceController],
    container: Application | None = None,
    *,
    path: str | None = None,
    methods: list[str] | None = None,
) -> list[Route]:
    routes = compile_resource(controller_class, container, path=path, methods=methods)  # ty:ignore[unknown-argument, unused-ignore-comment]
    for r in routes:
        collector._routes.append(r)
    return routes
