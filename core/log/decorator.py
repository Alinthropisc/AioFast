from __future__ import annotations

import asyncio
import functools
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable


def log_call(
    *, level: str = "DEBUG", show_args: bool = True, show_result: bool = False, name: str | None = None
) -> Callable:
    """
    Log every call to a function.

    @log_call()
    async def create_user(name: str, email: str):
        ...
    # → [DEBUG] → create_user(name='John', email='john@x.com')
    # → [DEBUG] ← create_user returned {...}
    """

    def decorator(func: Callable) -> Callable:
        fn_name = name or func.__qualname__  # ty:ignore[unresolved-attribute]

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                _log_entry(fn_name, level, args, kwargs, show_args)
                try:
                    result = await func(*args, **kwargs)
                    if show_result:
                        logger.opt(depth=1).log(level, "← {} returned {}", fn_name, _truncate(result))
                    return result
                except Exception as e:
                    logger.opt(depth=1).error("✗ {} raised {}: {}", fn_name, type(e).__name__, e)
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                _log_entry(fn_name, level, args, kwargs, show_args)
                try:
                    result = func(*args, **kwargs)
                    if show_result:
                        logger.opt(depth=1).log(level, "← {} returned {}", fn_name, _truncate(result))
                    return result
                except Exception as e:
                    logger.opt(depth=1).error("✗ {} raised {}: {}", fn_name, type(e).__name__, e)
                    raise

            return sync_wrapper

    return decorator


def log_errors(*, level: str = "ERROR", reraise: bool = True, name: str | None = None) -> Callable:
    """
    Log only when function raises exception.

    @log_errors()
    async def risky_operation():
        ...
    """

    def decorator(func: Callable) -> Callable:
        fn_name = name or func.__qualname__  # ty:ignore[unresolved-attribute]

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.opt(depth=1, exception=True).log(level, "✗ {} failed: {}", fn_name, e)
                    if reraise:
                        raise
                    return None

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.opt(depth=1, exception=True).log(level, "✗ {} failed: {}", fn_name, e)
                    if reraise:
                        raise
                    return None

            return sync_wrapper

    return decorator


def log_slow(threshold_ms: float = 500.0, *, level: str = "WARNING", name: str | None = None) -> Callable:
    """
    Log only when function takes longer than threshold.

    @log_slow(threshold_ms=200)
    async def fetch_data():
        ...
    # Only logs if takes >200ms
    """

    def decorator(func: Callable) -> Callable:
        fn_name = name or func.__qualname__  # ty:ignore[unresolved-attribute]

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                if elapsed >= threshold_ms:
                    logger.opt(depth=1).log(
                        level, "🐌 {} took {:.2f}ms (threshold: {:.0f}ms)", fn_name, elapsed, threshold_ms
                    )
                return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                if elapsed >= threshold_ms:
                    logger.opt(depth=1).log(
                        level, "🐌 {} took {:.2f}ms (threshold: {:.0f}ms)", fn_name, elapsed, threshold_ms
                    )
                return result

            return sync_wrapper

    return decorator


def _log_entry(fn_name: str, level: str, args: tuple, kwargs: dict, show: bool) -> None:
    if show:
        # Skip 'self' for methods
        display_args = args[1:] if args and hasattr(args[0], fn_name.split(".")[0] if "." in fn_name else "") else args
        parts = [repr(a) for a in display_args[:5]]
        parts += [f"{k}={v!r}" for k, v in list(kwargs.items())[:5]]
        sig = ", ".join(parts)
        logger.opt(depth=2).log(level, "→ {}({})", fn_name, sig)
    else:
        logger.opt(depth=2).log(level, "→ {}", fn_name)


def _truncate(obj: Any, max_len: int = 200) -> str:
    s = repr(obj)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s
