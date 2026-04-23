from __future__ import annotations

import pytest

from core.foundation import Application
from core.log import LogManager, LogServiceProvider


class TestLogServiceProvider:
    @pytest.mark.asyncio
    async def test_registers_log_manager(self):
        app = Application()
        provider = LogServiceProvider(app)
        await provider.register()
        log = await app.make("log")
        assert isinstance(log, LogManager)

    @pytest.mark.asyncio
    async def test_also_binds_class(self):
        app = Application()
        provider = LogServiceProvider(app)
        await provider.register()
        log = await app.make(LogManager)
        assert isinstance(log, LogManager)

    @pytest.mark.asyncio
    async def test_boot_configures(self):
        app = Application()
        provider = LogServiceProvider(app)
        await provider.register()
        await provider.boot()
        log: LogManager = await app.make("log")
        assert log._configured is True

    @pytest.mark.asyncio
    async def test_uses_config_if_available(self):
        from core.configuration import Repository

        app = Application()

        config = Repository(
            {
                "logging": {
                    "default": "console",
                    "channels": {
                        "console": {"driver": "console", "level": "WARNING"},
                    },
                },
            }
        )
        app.instance("config", config)
        provider = LogServiceProvider(app)
        await provider.register()
        log: LogManager = await app.make("log")
        assert log._config["default"] == "console"
        channel_cfg = log._config["channels"]["console"]
        assert channel_cfg["level"] == "WARNING"

    @pytest.mark.asyncio
    async def test_fallback_without_config(self):
        app = Application()
        provider = LogServiceProvider(app)
        await provider.register()
        log: LogManager = await app.make("log")
        assert log._config["default"] == "console"
