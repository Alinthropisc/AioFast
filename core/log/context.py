from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


class LogContext:
    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs
        self._previous: dict[str, Any] = {}

    def __enter__(self) -> LogContext:
        self._previous = _log_context.get().copy()
        merged = {**self._previous, **self._data}
        _log_context.set(merged)
        return self

    def __exit__(self, *exc: Any) -> None:
        _log_context.set(self._previous)

    @staticmethod
    def push(**kwargs: Any) -> None:
        current = _log_context.get().copy()
        current.update(kwargs)
        _log_context.set(current)

    @staticmethod
    def get() -> dict[str, Any]:
        return _log_context.get().copy()

    @staticmethod
    def clear() -> None:
        _log_context.set({})

    @staticmethod
    def forget(*keys: str) -> None:
        current = _log_context.get().copy()
        for k in keys:
            current.pop(k, None)
        _log_context.set(current)


def context_patcher(record: dict) -> None:
    ctx = _log_context.get()
    record["extra"]["context"] = ctx
    # Build string for text formatters
    if ctx:
        parts = " ".join(f"{k}={v!r}" for k, v in ctx.items())
        record["extra"]["context_str"] = f" [{parts}]"
    else:
        record["extra"]["context_str"] = ""
