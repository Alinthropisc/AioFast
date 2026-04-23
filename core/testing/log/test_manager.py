from __future__ import annotations

import pytest
from loguru import logger as loguru_logger

from core.log import ChannelLogger, LogManager


class TestLogManagerInit:
    def test_default_config(self):
        m = LogManager()
        assert m._config["default"] == "console"
        assert "console" in m._config["channels"]

    def test_custom_config(self, full_config):
        m = LogManager(full_config)
        assert m._config["default"] == "stack"

    def test_not_configured_initially(self):
        m = LogManager()
        assert m._configured is False

    def test_repr(self, manager):
        r = repr(manager)
        assert "LogManager" in r
        assert "channels=" in r


class TestLogManagerConfigure:
    def test_configure_sets_flag(self):
        m = LogManager()
        m.configure()
        assert m._configured is True

    def test_double_configure_idempotent(self):
        m = LogManager()
        m.configure()
        m.configure()
        assert m._configured is True

    def test_configure_creates_default_channel(self, manager):
        assert "console" in manager._channels

    def test_configure_stack_resolves_sub_channels(self, full_config):
        m = LogManager(full_config)
        m.configure()
        assert "console" in m._channels
        assert "daily" in m._channels


class TestLogManagerLogging:
    def test_debug(self, manager, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        manager.debug("test debug {}", 123)
        assert any("test debug 123" in msg for msg in sink_capture["messages"])

    def test_info(self, manager, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        manager.info("hello world")
        assert any("hello world" in msg for msg in sink_capture["messages"])

    def test_warning(self, manager, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        manager.warning("warn msg")
        assert any("warn msg" in msg for msg in sink_capture["messages"])

    def test_error(self, manager, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        manager.error("err msg")
        assert any("err msg" in msg for msg in sink_capture["messages"])

    def test_critical(self, manager, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        manager.critical("crit msg")
        assert any("crit msg" in msg for msg in sink_capture["messages"])

    def test_auto_configure_on_first_log(self, capture_sink, sink_capture):
        m = LogManager()
        assert m._configured is False
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        m.info("auto configure")
        assert m._configured is True


class TestLogManagerChannels:
    def test_channel_returns_channel_logger(self, manager):
        ch = manager.channel("console")
        assert isinstance(ch, ChannelLogger)

    def test_channel_unknown_raises(self, manager):
        with pytest.raises(ValueError, match="not configured"):
            manager.channel("nonexistent")

    def test_stack_returns_channel_logger(self, full_config):
        m = LogManager(full_config)
        m.configure()
        ch = m.stack("console", "daily")
        assert isinstance(ch, ChannelLogger)

    def test_channel_logger_repr(self, manager):
        ch = manager.channel("console")
        assert "ChannelLogger" in repr(ch)


class TestLogManagerExtend:
    def test_extend_custom_driver(self, manager):
        from core.log import Channel

        class MyChannel(Channel):
            def setup(self, log):
                self._sink_id = log.add(lambda m: None, level="DEBUG")
                return self._sink_id

        manager.extend("custom", MyChannel)
        assert "custom" in manager._custom_drivers

    def test_extend_and_use(self):
        from core.log import Channel

        captured = []

        class MemChannel(Channel):
            def setup(self, log):
                self._sink_id = log.add(lambda m: captured.append(str(m).rstrip()), level="DEBUG", format="{message}")
                return self._sink_id

        m = LogManager(
            {
                "default": "mem",
                "channels": {
                    "mem": {"driver": "mem", "level": "DEBUG"},
                },
            }
        )
        m.extend("mem", MemChannel)
        m.configure()
        m.info("custom channel works")
        assert any("custom channel works" in msg for msg in captured)


class TestLogManagerShutdown:
    def test_shutdown_clears_channels(self, manager):
        assert len(manager._channels) > 0
        manager.shutdown()
        assert len(manager._channels) == 0
        assert manager._configured is False

    @pytest.mark.asyncio
    async def test_aclose(self, manager):
        await manager.aclose()
        assert manager._configured is False

    def test_raw_property(self, manager):
        assert manager.raw is not None
