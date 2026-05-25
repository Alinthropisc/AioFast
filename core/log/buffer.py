from __future__ import annotations

import asyncio
import threading
from collections import deque
from typing import TYPE_CHECKING, Any

from .channel import Channel

if TYPE_CHECKING:
    from collections.abc import Callable


class BufferedChannel(Channel):
    """
    Buffer log messages and flush in batches.

    Useful for external services (Elasticsearch, HTTP APIs)
    where sending each log individually is expensive.

    Config:
        {
            "driver": "buffered",
            "buffer_size": 100,
            "flush_interval": 5.0,
            "on_flush": callable_that_receives_list_of_records,
        }
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._buffer: deque[str] = deque()
        self._buffer_size: int = config.get("buffer_size", 100)
        self._flush_interval: float = config.get("flush_interval", 5.0)
        self._on_flush: Callable | None = config.get("on_flush")
        self._lock = threading.Lock()
        self._flush_task: asyncio.Task | None = None

    def setup(self, log: Any) -> int:
        self._sink_id = log.add(
            self._collect,
            level=self._level,
            format=self.config.get("format", "{time:YYYY-MM-DDTHH:mm:ss.SSSZ} [{level}] {message}"),
        )
        self._start_flush_timer()
        return self._sink_id

    def _collect(self, message: str) -> None:
        with self._lock:
            self._buffer.append(str(message).rstrip())
            if len(self._buffer) >= self._buffer_size:
                self._do_flush()

    def _do_flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()

        if self._on_flush:
            try:
                result = self._on_flush(batch)
                if asyncio.iscoroutine(result):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(result)  # noqa: RUF006  (fire-and-forget flush)
                    else:
                        loop.run_until_complete(result)
            except Exception:
                pass  # Don't let flush errors crash the app

    def flush(self) -> None:
        """Manual flush."""
        self._do_flush()

    def _start_flush_timer(self) -> None:
        """Start periodic flush in background."""
        import threading

        def _timer():
            while True:
                import time

                time.sleep(self._flush_interval)
                self._do_flush()

        t = threading.Thread(target=_timer, daemon=True)
        t.start()

    def teardown(self, log: Any) -> None:
        self._do_flush()
        super().teardown(log)

    def __repr__(self) -> str:
        return f"<BufferedChannel name={self.name!r} buffered={len(self._buffer)} size={self._buffer_size}>"
