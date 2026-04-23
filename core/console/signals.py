from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class SignalManager:
    _instance: SignalManager | None = None

    def __init__(self) -> None:
        self._running = True
        self._shutting_down = False
        self._callbacks: list[Callable] = []
        self._installed = False

    @classmethod
    def get_instance(cls) -> SignalManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def on_shutdown(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def install(self) -> None:
        if self._installed:
            return
        self._installed = True

        if sys.platform == "win32":
            signal.signal(signal.SIGINT, self._sync_handler)
            signal.signal(signal.SIGBREAK, self._sync_handler)
        else:
            try:
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, lambda s=sig: self._handle(s))
            except RuntimeError:
                signal.signal(signal.SIGINT, self._sync_handler)
                signal.signal(signal.SIGTERM, self._sync_handler)
        logger.debug("Signal handlers installed")

    def stop(self) -> None:
        self._running = False
        self._shutting_down = True

    def reset(self) -> None:
        self._running = True
        self._shutting_down = False

    def _handle(self, sig: signal.Signals) -> None:
        logger.info("Received signal %s, shutting down gracefully...", sig.name)
        self.stop()
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                logger.warning("Shutdown callback error: %s", e)

    def _sync_handler(self, signum: int, frame: Any) -> None:
        self._handle(signal.Signals(signum))

    def __repr__(self) -> str:
        state = "running" if self._running else "stopping"
        return f"<SignalManager {state}>"
