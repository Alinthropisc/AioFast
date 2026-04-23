from __future__ import annotations

from ..foundation.service_provider import ServiceProvider
from .manager import LogManager


class LogServiceProvider(ServiceProvider):
    """
    Register LogManager in container.

    Config (config/logging.py):
        config = {
            "default": "stack",
            "channels": {
                "stack": {"driver": "stack", "channels": ["console", "daily"]},
                "console": {"driver": "console", "level": "DEBUG"},
                "daily": {
                    "driver": "rotating",
                    "path": "storage/logs/app.log",
                    "rotation": "00:00",
                    "retention": "30 days",
                    "level": "INFO",
                },
            },
        }
    """

    async def register(self) -> None:
        cfg = await self._load_config()
        manager = LogManager(cfg)
        self.app.instance("log", manager)
        self.app.instance(LogManager, manager)

    async def boot(self) -> None:
        manager: LogManager = await self.app.make("log")
        manager.configure()

    async def _load_config(self) -> dict:
        repo = await self.app.make_or("config")
        if repo is not None:
            cfg = repo.get("logging")
            if cfg:
                return cfg
        return LogManager._default_config()
