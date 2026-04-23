from __future__ import annotations

import asyncio
import time

import pytest
from loguru import logger as loguru_logger

from core.log import log_call, log_errors, log_slow


class TestLogCall:
    @pytest.mark.asyncio
    async def test_async_function_logged(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_call()
        async def greet(name: str):
            return f"hello {name}"

        result = await greet("world")
        assert result == "hello world"
        assert any("greet" in msg for msg in sink_capture["messages"])

    def test_sync_function_logged(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_call()
        def add(a: int, b: int):
            return a + b

        result = add(1, 2)
        assert result == 3
        assert any("add" in msg for msg in sink_capture["messages"])

    @pytest.mark.asyncio
    async def test_show_result(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_call(show_result=True)
        async def get_value():
            return {"key": "value"}

        await get_value()
        assert any("returned" in msg for msg in sink_capture["messages"])

    @pytest.mark.asyncio
    async def test_logs_exception(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_call()
        async def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await failing()
        assert any("raised" in msg for msg in sink_capture["messages"])

    @pytest.mark.asyncio
    async def test_custom_name(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_call(name="my.custom.name")
        async def func():
            pass

        await func()
        assert any("my.custom.name" in msg for msg in sink_capture["messages"])


class TestLogErrors:
    @pytest.mark.asyncio
    async def test_logs_error(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_errors()
        async def bad():
            raise RuntimeError("oops")

        with pytest.raises(RuntimeError):
            await bad()
        assert any("failed" in msg for msg in sink_capture["messages"])

    @pytest.mark.asyncio
    async def test_no_reraise(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_errors(reraise=False)
        async def bad():
            raise RuntimeError("swallowed")

        result = await bad()
        assert result is None

    @pytest.mark.asyncio
    async def test_no_log_on_success(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_errors()
        async def good():
            return "ok"

        result = await good()
        assert result == "ok"
        assert not any("failed" in msg for msg in sink_capture["messages"])

    def test_sync_errors(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_errors()
        def bad_sync():
            raise TypeError("sync fail")

        with pytest.raises(TypeError):
            bad_sync()
        assert any("failed" in msg for msg in sink_capture["messages"])


class TestLogSlow:
    @pytest.mark.asyncio
    async def test_logs_slow_call(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_slow(threshold_ms=10)
        async def slow():
            await asyncio.sleep(0.02)
            return "done"

        result = await slow()
        assert result == "done"
        assert any("🐌" in msg for msg in sink_capture["messages"])

    @pytest.mark.asyncio
    async def test_no_log_fast_call(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_slow(threshold_ms=5000)
        async def fast():
            return "quick"

        result = await fast()
        assert result == "quick"
        assert not any("🐌" in msg for msg in sink_capture["messages"])

    def test_sync_slow(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")

        @log_slow(threshold_ms=10)
        def slow_sync():
            time.sleep(0.02)

        slow_sync()
        assert any("🐌" in msg for msg in sink_capture["messages"])
