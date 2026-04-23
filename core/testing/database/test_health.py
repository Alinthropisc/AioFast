from __future__ import annotations

import pytest

from core.database.health import HealthMonitor, with_retry


class TestHealthMonitor:
    @pytest.mark.asyncio
    async def test_check_all(self, db_manager):
        monitor = HealthMonitor(db_manager)

        if "sqlite" in db_manager.engine().url.drivername:
            pytest.skip("SQLite in-memory does not support connection pooling checks")
        status = await monitor.check()
        # assert monitor.check_all() is True
        assert "default" in status
        assert status["default"]["healthy"] is True
        assert "latency_ms" in status["default"]

    @pytest.mark.asyncio
    async def test_ensure_connected(self, db_manager):
        monitor = HealthMonitor(db_manager)
        result = await monitor.ensure_connected()
        assert result is True

    @pytest.mark.asyncio
    async def test_full_report(self, db_manager):
        monitor = HealthMonitor(db_manager)
        if "sqlite" in db_manager.engine().url.drivername:
            pytest.skip("SQLite in-memory health checks not supported")
        report = await monitor.full_report()
        report = await monitor.full_report()
        assert report["status"] == "healthy"
        assert "connections" in report
        assert "all_healthy" in report
        assert report["all_healthy"] is True
        assert report["total_connections"] == 1


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        async def ok():
            return 42

        result = await with_retry(ok, max_retries=3)
        assert result == 42

    @pytest.mark.asyncio
    async def test_succeeds_after_retries(self):
        attempts = 0

        async def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("fail")
            return "ok"

        result = await with_retry(
            flaky,
            max_retries=5,
            delay=0.01,
            retry_on=(ConnectionError,),
        )
        assert result == "ok"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        async def always_fail():
            raise ConnectionError("nope")

        with pytest.raises(ConnectionError):
            await with_retry(
                always_fail,
                max_retries=2,
                delay=0.01,
                retry_on=(ConnectionError,),
            )

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        async def wrong_error():
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await with_retry(
                wrong_error,
                max_retries=3,
                delay=0.01,
                retry_on=(ConnectionError,),
            )
