from __future__ import annotations

import asyncio
import time

import pytest

from core.log import Profiler, Timer


class TestTimer:
    def test_start_stop(self):
        captured = []

        class FakeProfiler:
            def _log_result(self, label, elapsed, success, extra):
                captured.append((label, elapsed, success))

        t = Timer("test", FakeProfiler(), {})  # ty:ignore[invalid-argument-type]
        t.start()
        time.sleep(0.01)
        elapsed = t.stop()
        assert elapsed > 0
        assert len(captured) == 1
        assert captured[0][0] == "test"
        assert captured[0][2] is True  # success

    def test_elapsed_during(self):
        t = Timer("test", Profiler(), {})
        t.start()
        time.sleep(0.01)
        mid = t.elapsed_ms
        assert mid > 0  # ty:ignore[unsupported-operator]
        assert mid is not None

    def test_repr(self):
        t = Timer("test", Profiler(), {})
        t.start()
        r = repr(t)
        assert "Timer" in r
        assert "test" in r


class TestProfilerMeasure:
    def test_sync_measure(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        with p.measure("my.operation"):
            time.sleep(0.01)
        assert len(captured) == 1
        assert captured[0][0] == "my.operation"
        assert captured[0][1] > 0
        assert captured[0][2] is True

    def test_measure_failure(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        with pytest.raises(ValueError), p.measure("failing"):
            raise ValueError("boom")
        assert len(captured) == 1
        assert captured[0][2] is False  # success=False

    @pytest.mark.asyncio
    async def test_async_measure(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        async with p.ameasure("async.op"):
            await asyncio.sleep(0.01)
        assert len(captured) == 1
        assert captured[0][0] == "async.op"
        assert captured[0][2] is True


class TestProfilerTrack:
    def test_sync_decorator(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        @p.track
        def my_func():
            time.sleep(0.01)
            return 42

        result = my_func()
        assert result == 42
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        @p.track
        async def my_async_func():
            await asyncio.sleep(0.01)
            return "ok"

        result = await my_async_func()
        assert result == "ok"
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_decorator_with_label(self):
        captured = []
        p = Profiler()
        p._log_result = lambda l, e, s, x: captured.append((l, e, s))  # ty:ignore[invalid-assignment]

        @p.track(label="custom.label")
        async def something():
            pass

        await something()
        assert captured[0][0] == "custom.label"


class TestProfilerSlowThreshold:
    def test_slow_detection(self):
        results = []
        p = Profiler(slow_threshold_ms=10)

        def spy(l, e, s, x):
            results.append({"label": l, "elapsed": e, "success": s})

        p._log_result = spy  # ty:ignore[invalid-assignment]

        with p.measure("fast"):
            pass  # instant

        with p.measure("slow"):
            time.sleep(0.02)  # >10ms
        assert results[0]["elapsed"] < 10
        assert results[1]["elapsed"] >= 10
