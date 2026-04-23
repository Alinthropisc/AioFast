from __future__ import annotations

import logging
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


def isolated(cls: type[T]) -> type[T]:
    cls.isolated = True  # ty:ignore[unresolved-attribute]
    return cls


def hidden(cls: type[T]) -> type[T]:
    cls.hidden = True  # ty:ignore[unresolved-attribute]
    return cls


def with_lock(key: str = "", timeout: int = 0):
    def decorator(cls: type[T]) -> type[T]:
        cls._lock_key = key  # ty:ignore[unresolved-attribute]
        cls._lock_timeout = timeout  # ty:ignore[unresolved-attribute]
        if not hasattr(cls, "lock") or not cls.lock:
            cls.lock = True  # ty:ignore[unresolved-attribute]
        return cls

    return decorator


def retry(times: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    def decorator(cls: type[T]) -> type[T]:
        cls._retry_times = times  # ty:ignore[unresolved-attribute]
        cls._retry_delay = delay  # ty:ignore[unresolved-attribute]
        cls._retry_exceptions = exceptions  # ty:ignore[unresolved-attribute]
        return cls

    return decorator


def timeout(seconds: int):
    def decorator(cls: type[T]) -> type[T]:
        cls._timeout_seconds = seconds  # ty:ignore[unresolved-attribute]
        return cls

    return decorator


def environments(*envs: str):
    def decorator(cls: type[T]) -> type[T]:
        cls._allowed_environments = list(envs)  # ty:ignore[unresolved-attribute]
        return cls

    return decorator


def log_execution(cls: type[T]) -> type[T]:
    cls._log_execution = True  # ty:ignore[unresolved-attribute]
    return cls


def production_guard(cls: type[T]) -> type[T]:
    cls.production_guard = True  # ty:ignore[unresolved-attribute]
    return cls
