import functools
import inspect
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def injectable(cls: type[T]) -> type[T]:
    cls.__injectable__ = True  # ty:ignore[unresolved-attribute]
    return cls


def service(name: str | None = None, singleton: bool = False, tags: list | None = None):

    def decorator(cls: type[T]) -> type[T]:
        cls.__service_meta__ = {  # ty:ignore[unresolved-attribute]
            "name": name or cls.__name__,
            "singleton": singleton,
            "tags": tags or [],
        }
        return cls

    return decorator


def inject(func: Callable) -> Callable:

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        container = kwargs.pop("_container", None)

        if container is None:
            # Try to find container from 'self' (first arg)
            if args and hasattr(args[0], "app"):
                container = args[0].app.container
            elif args and hasattr(args[0], "container"):
                container = args[0].container

        if container is not None:
            return await container.call(func, *args, **kwargs)

        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    return wrapper
