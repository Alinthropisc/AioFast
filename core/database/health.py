from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Database health monitoring — auto retry, circuit breaker.

    Usage:
        monitor = HealthMonitor(manager)

        # Periodic health check:
        status = await monitor.check()
        # {"default": {"healthy": True, "latency_ms": 2.3, "pool": {...}}}

        # Auto-reconnect:
        await monitor.ensure_connected()

        # Detailed report:
        report = await monitor.full_report()
    """

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager
        self._last_check: dict[str, float] = {}
        self._failures: dict[str, int] = {}

    async def check(self) -> dict[str, dict[str, Any]]:
        """Check health of all connections."""
        result = {}
        for name in self._manager.connections:
            result[name] = await self._check_one(name)
        return result

    async def _check_one(self, name: str) -> dict[str, Any]:
        """Check single connection health."""
        start = time.perf_counter()
        try:
            healthy = await self._manager.ping(name)
            latency = (time.perf_counter() - start) * 1000

            if healthy:
                self._failures[name] = 0
            else:
                self._failures[name] = self._failures.get(name, 0) + 1

            pool = self._manager.pool_status(name)

            return {
                "healthy": healthy,
                "latency_ms": round(latency, 2),
                "pool": pool,
                "consecutive_failures": self._failures.get(name, 0),
            }
        except Exception as e:
            self._failures[name] = self._failures.get(name, 0) + 1
            return {
                "healthy": False,
                "error": str(e),
                "consecutive_failures": self._failures[name],
            }

    async def ensure_connected(self, max_retries: int = 3, delay: float = 1.0) -> bool:
        """Ensure all connections are alive. Retry if needed."""
        for name in self._manager.connections:
            for attempt in range(max_retries):
                if await self._manager.ping(name):
                    break
                logger.warning("Connection '%s' failed (attempt %d/%d), retrying...", name, attempt + 1, max_retries)
                await asyncio.sleep(delay * (attempt + 1))

                # Try reconnect
                try:
                    await self._manager.disconnect(name)
                    await self._manager.connect(name)
                except Exception as e:
                    logger.error("Reconnect failed: %s", e)
            else:
                logger.error("Connection '%s' failed after %d retries", name, max_retries)
                return False

        return True

    async def full_report(self) -> dict[str, Any]:
        """Full health report."""
        checks = await self.check()
        return {
            "connections": checks,
            "all_healthy": all(c["healthy"] for c in checks.values()),
            "total_connections": len(checks),
            "manager": repr(self._manager),
        }


async def with_retry(
    fn: Callable, *args: Any, max_retries: int = 3, delay: float = 0.5, retry_on: tuple = (Exception,), **kwargs: Any
) -> Any:
    """
    Retry a database operation on failure.

    Usage:
        result = await with_retry(
            repo.create,
            name="Alice",
            email="a@t.com",
            max_retries=3,
        )
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except retry_on as e:
            last_error = e
            logger.warning("Retry %d/%d for %s: %s", attempt + 1, max_retries, fn.__name__, e)  # ty:ignore[unresolved-attribute]
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))
    raise last_error  # ty:ignore[invalid-raise]
