from __future__ import annotations

import json
from pathlib import Path

import pytest
from loguru import logger as loguru_logger

from core.log import (
    CHANNEL_DRIVERS,
    CallbackChannel,
    ConsoleChannel,
    FileChannel,
    JsonChannel,
    NullChannel,
    RotatingChannel,
)


class TestChannelRegistry:
    def test_all_drivers_registered(self):
        assert "console" in CHANNEL_DRIVERS
        assert "file" in CHANNEL_DRIVERS
        assert "rotating" in CHANNEL_DRIVERS
        assert "json" in CHANNEL_DRIVERS
        assert "callback" in CHANNEL_DRIVERS
        assert "null" in CHANNEL_DRIVERS


class TestConsoleChannel:
    def test_setup(self):
        ch = ConsoleChannel("test", {"level": "DEBUG"})
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None
        assert ch._sink_id is not None

    def test_teardown(self):
        ch = ConsoleChannel("test", {"level": "DEBUG"})
        ch.setup(loguru_logger)
        ch.teardown(loguru_logger)
        assert ch._sink_id is None

    def test_repr(self):
        ch = ConsoleChannel("test", {"level": "INFO"})
        r = repr(ch)
        assert "ConsoleChannel" in r
        assert "INFO" in r

    def test_stderr(self):
        ch = ConsoleChannel("test", {"level": "DEBUG", "stderr": True})
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None

    def test_filter_only(self):
        ch = ConsoleChannel(
            "test",
            {
                "level": "DEBUG",
                "only": ["myapp"],
            },
        )
        flt = ch._make_filter()
        assert flt is not None


class TestFileChannel:
    def test_setup_creates_sink(self, tmp_log_dir):
        path = str(tmp_log_dir / "test.log")
        ch = FileChannel("file", {"level": "DEBUG", "path": path})
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None

    def test_writes_to_file(self, tmp_log_dir):
        path = str(tmp_log_dir / "test.log")
        ch = FileChannel(
            "file",
            {
                "level": "DEBUG",
                "path": path,
                "format": "{message}",
            },
        )
        ch.setup(loguru_logger)
        loguru_logger.info("file test message")
        import time

        time.sleep(0.1)
        content = Path(path).read_text()
        assert "file test message" in content


class TestRotatingChannel:
    def test_setup(self, tmp_log_dir):
        path = str(tmp_log_dir / "rotating.log")
        ch = RotatingChannel(
            "rotating",
            {
                "level": "INFO",
                "path": path,
                "rotation": "10 MB",
                "retention": "7 days",
            },
        )
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None


class TestJsonChannel:
    def test_setup(self, tmp_log_dir):
        path = str(tmp_log_dir / "app.json")
        ch = JsonChannel(
            "json",
            {
                "level": "WARNING",
                "path": path,
            },
        )
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None

    def test_json_format(self, tmp_log_dir):
        path = str(tmp_log_dir / "app.json")
        ch = JsonChannel(
            "json",
            {
                "level": "DEBUG",
                "path": path,
            },
        )
        ch.setup(loguru_logger)
        loguru_logger.warning("json test")
        import time

        time.sleep(0.1)
        content = Path(path).read_text().strip()
        if content:
            lines = content.split("\n")
            entry = json.loads(lines[-1])
            assert entry["level"] == "WARNING"
            assert "json test" in entry["message"]


class TestCallbackChannel:
    def test_requires_callback(self):
        ch = CallbackChannel("cb", {"level": "DEBUG"})
        with pytest.raises(ValueError, match="requires 'callback'"):
            ch.setup(loguru_logger)

    def test_with_callback(self):
        captured = []
        ch = CallbackChannel(
            "cb",
            {
                "level": "DEBUG",
                "callback": lambda m: captured.append(str(m)),
            },
        )
        ch.setup(loguru_logger)
        loguru_logger.info("callback test")
        import time

        time.sleep(0.1)
        assert len(captured) > 0


class TestNullChannel:
    def test_setup(self):
        ch = NullChannel("null", {"level": "DEBUG"})
        sink_id = ch.setup(loguru_logger)
        assert sink_id is not None

    def test_discards_messages(self):
        ch = NullChannel("null", {"level": "DEBUG"})
        ch.setup(loguru_logger)
        # Should not raise
        loguru_logger.info("discarded")
        loguru_logger.error("also discarded")
