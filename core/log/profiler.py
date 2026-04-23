from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .manager import LogManager


class Profiler:
    """
    Performance measurement for logging.

    Usage:
        profiler = Profiler(log_manager)

        # Context manager
        with profiler.measure("db.query"):
            await db.execute(...)
        # → [PERF] db.query completed in 12.34ms

        # Async context manager
        async with profiler.ameasure("api.call"):
            await httpx.get(...)

        # Decorator
        @profiler.track
        async def fetch_users():
            ...

        # Manual
        timer = profiler.start("process")
        ...
        elapsed = timer.stop()  # logs automatically
    """

    def __init__(self, manager: LogManager | None = None, *, slow_threshold_ms: float = 1000.0) -> None:
        self._manager = manager
        self._slow_threshold = slow_threshold_ms

    @contextmanager
    def measure(self, label: str, **extra: Any):
        """Sync context manager for timing."""
        timer = Timer(label, self, extra)
        timer.start()
        try:
            yield timer
        except Exception:
            timer.stop(success=False)
            raise
        else:
            timer.stop(success=True)

    class _AsyncMeasure:
        def __init__(self, label: str, profiler: Profiler, extra: dict):
            self._timer = Timer(label, profiler, extra)

        async def __aenter__(self) -> Timer:
            self._timer.start()
            return self._timer

        async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
            self._timer.stop(success=exc_type is None)

    def ameasure(self, label: str, **extra: Any) -> _AsyncMeasure:
        """Async context manager for timing."""
        return self._AsyncMeasure(label, self, extra)

    def track(
        self,
        func: Callable | None = None,
        *,
        label: str | None = None,
    ) -> Callable:
        """Decorator to track function execution time."""

        def decorator(fn: Callable) -> Callable:
            name = label or f"{fn.__module__}.{fn.__qualname__}"  # ty:ignore[unresolved-attribute]

            if _is_async(fn):

                @functools.wraps(fn)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    async with self.ameasure(name):
                        return await fn(*args, **kwargs)

                return async_wrapper
            else:

                @functools.wraps(fn)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self.measure(name):
                        return fn(*args, **kwargs)

                return sync_wrapper

        if func is not None:
            return decorator(func)
        return decorator

    def _log_result(self, label: str, elapsed_ms: float, success: bool, extra: dict) -> None:
        is_slow = elapsed_ms >= self._slow_threshold
        status = "✓" if success else "✗"

        if is_slow:
            level = "warning"
            tag = "SLOW"
        elif not success:
            level = "error"
            tag = "FAIL"
        else:
            level = "debug"
            tag = "PERF"

        msg = f"[{tag}] {label} {status} {elapsed_ms:.2f}ms"
        if extra:
            parts = " ".join(f"{k}={v}" for k, v in extra.items())
            msg += f" ({parts})"

        if self._manager:
            getattr(self._manager, level)(msg)
        else:
            from loguru import logger

            getattr(logger.opt(depth=2), level)(msg)


class Timer:
    """Individual timer instance."""

    __slots__ = ("_elapsed", "_start", "extra", "label", "profiler")

    def __init__(self, label: str, profiler: Profiler, extra: dict) -> None:
        self.label = label
        self.profiler = profiler
        self.extra = extra
        self._start: float = 0.0
        self._elapsed: float | None = None

    def start(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def stop(self, *, success: bool = True) -> float:
        self._elapsed = (time.perf_counter() - self._start) * 1000
        self.profiler._log_result(self.label, self._elapsed, success, self.extra)
        return self._elapsed

    @property
    def elapsed_ms(self) -> float | None:
        if self._elapsed is not None:
            return self._elapsed
        return (time.perf_counter() - self._start) * 1000

    def __repr__(self) -> str:
        ms = self.elapsed_ms
        return f"<Timer {self.label!r} {ms:.2f}ms>"


def _is_async(fn: Any) -> bool:
    import asyncio

    return asyncio.iscoroutinefunction(fn)
