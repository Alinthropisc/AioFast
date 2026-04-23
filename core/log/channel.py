from __future__ import annotations

import contextlib
import json
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class Channel(ABC):
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self._sink_id: int | None = None
        self._level: str = config.get("level", "DEBUG").upper()

    @abstractmethod
    def setup(self, log: Any) -> int:
        pass

    def teardown(self, log: Any) -> None:
        if self._sink_id is not None:
            with contextlib.suppress(ValueError):
                log.remove(self._sink_id)
            self._sink_id = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} level={self._level}>"


class ConsoleChannel(Channel):
    def setup(self, log: Any) -> int:
        stream = sys.stderr if self.config.get("stderr", False) else sys.stdout
        colorize = self.config.get("colorize", True)
        fmt = self.config.get(
            "format",
            "<green>{time:HH:mm:ss}</green> <level>[{level:<7}]</level> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — <level>{message}</level> {extra[context_str]}",
        )
        self._sink_id = log.add(stream, level=self._level, format=fmt, colorize=colorize, filter=self._make_filter())
        return self._sink_id

    def _make_filter(self) -> Callable | None:
        only = self.config.get("only")
        if only:
            modules = only if isinstance(only, list) else [only]
            return lambda record: any(record["name"].startswith(m) for m in modules)
        return None


class FileChannel(Channel):
    def setup(self, log: Any) -> int:
        path = self.config.get("path", "storage/logs/app.log")
        fmt = self.config.get(
            "format",
            "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level:<7}] {name}:{function}:{line} — {message} {extra[context_str]}",
        )
        self._sink_id = log.add(path, level=self._level, format=fmt, encoding="utf-8", enqueue=True)
        return self._sink_id


class RotatingChannel(Channel):
    def setup(self, log: Any) -> int:
        path = self.config.get("path", "storage/logs/app.log")
        rotation = self.config.get("rotation", "10 MB")
        retention = self.config.get("retention", "30 days")
        compression = self.config.get("compression", "zip")
        fmt = self.config.get(
            "format",
            "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level:<7}] {name}:{function}:{line} — {message} {extra[context_str]}",
        )
        self._sink_id = log.add(
            path,
            level=self._level,
            format=fmt,
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            enqueue=True,
        )
        return self._sink_id


class JsonChannel(Channel):
    def setup(self, log: Any) -> int:
        path = self.config.get("path", "storage/logs/app.json")
        rotation = self.config.get("rotation", "50 MB")
        retention = self.config.get("retention", "14 days")
        self._sink_id = log.add(
            path,
            level=self._level,
            format=self._json_format,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
            serialize=False,
        )
        return self._sink_id

    @staticmethod
    def _json_format(record: dict) -> str:
        ts = record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        entry = {
            "timestamp": ts,
            "level": record["level"].name,
            "message": record["message"],
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        # merge extra context
        ctx = record.get("extra", {})
        raw_ctx = ctx.get("context", {})
        if raw_ctx:
            entry["context"] = raw_ctx
        exc = record.get("exception")
        if exc:
            entry["exception"] = {
                "type": exc.type.__name__ if exc.type else None,
                "value": str(exc.value) if exc.value else None,
            }
        return json.dumps(entry, default=str, ensure_ascii=False) + "\n"


class CallbackChannel(Channel):
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._callback: Callable | None = config.get("callback")

    def setup(self, log: Any) -> int:
        if self._callback is None:
            raise ValueError(f"CallbackChannel '{self.name}' requires 'callback' in config")
        self._sink_id = log.add(
            self._callback, level=self._level, format=self.config.get("format", "{message}"), enqueue=True
        )
        return self._sink_id


class NullChannel(Channel):
    def setup(self, log: Any) -> int:
        import os

        self._sink_id = log.add(os.devnull, level="TRACE")
        return self._sink_id


CHANNEL_DRIVERS: dict[str, type[Channel]] = {
    "console": ConsoleChannel,
    "file": FileChannel,
    "rotating": RotatingChannel,
    "json": JsonChannel,
    "callback": CallbackChannel,
    "null": NullChannel,
}
