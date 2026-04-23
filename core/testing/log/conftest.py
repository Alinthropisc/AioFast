from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from loguru import logger as loguru_logger

from core.log import LogContext, LogManager

root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "sourcefiles"))


@pytest.fixture(autouse=True)
def _clean_loguru():
    """Remove all loguru sinks before/after each test."""
    loguru_logger.remove()
    yield
    loguru_logger.remove()


@pytest.fixture(autouse=True)
def _clean_context():
    """Clear log context before/after each test."""
    LogContext.clear()
    yield
    LogContext.clear()


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """Temp directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def sink_capture() -> dict[str, list[str]]:
    """Capture sink — collects log messages as strings."""
    return {"messages": []}


@pytest.fixture
def capture_sink(sink_capture):
    """Callable sink for loguru that captures messages."""

    def _sink(message: Any) -> None:
        sink_capture["messages"].append(str(message).rstrip())

    return _sink


@pytest.fixture
def console_config() -> dict:
    return {
        "default": "console",
        "channels": {
            "console": {
                "driver": "console",
                "level": "DEBUG",
            },
        },
    }


@pytest.fixture
def full_config(tmp_log_dir: Path) -> dict:
    return {
        "default": "stack",
        "channels": {
            "stack": {
                "driver": "stack",
                "channels": ["console", "daily"],
            },
            "console": {
                "driver": "console",
                "level": "DEBUG",
            },
            "daily": {
                "driver": "rotating",
                "path": str(tmp_log_dir / "app.log"),
                "level": "INFO",
                "rotation": "10 MB",
                "retention": "7 days",
            },
            "json": {
                "driver": "json",
                "path": str(tmp_log_dir / "app.json"),
                "level": "WARNING",
            },
            "null": {
                "driver": "null",
            },
        },
    }


@pytest.fixture
def manager(console_config) -> LogManager:
    m = LogManager(console_config)
    m.configure()
    return m
