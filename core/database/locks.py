from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseLock:
    """
    Advisory locks via database — distributed locking without Redis.

    PostgreSQL: pg_advisory_lock / pg_try_advisory_lock
    MySQL: GET_LOCK / RELEASE_LOCK
    SQLite: Not supported (uses file lock fallback)

    Usage:
        lock = DatabaseLock(manager)

        # Blocking lock:
        async with lock.acquire("process-invoices"):
            await process_invoices()

        # Non-blocking:
        acquired = await lock.try_acquire("send-emails")
        if acquired:
            try:
                await send_emails()
            finally:
                await lock.release("send-emails")

        # With timeout:
        async with lock.acquire("heavy-task", timeout=30):
            ...
    """

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager
        self._dialect: str | None = None

    def _get_dialect(self) -> str:
        if self._dialect is None:
            engine = self._manager.engine()
            url = str(engine.url)
            if "postgresql" in url or "postgres" in url:
                self._dialect = "postgresql"
            elif "mysql" in url or "mariadb" in url:
                self._dialect = "mysql"
            else:
                self._dialect = "other"
        return self._dialect

    def _lock_id(self, name: str) -> int:
        """Convert lock name to integer ID for pg_advisory_lock."""
        return int(hashlib.md5(name.encode()).hexdigest()[:15], 16) % (2**31)

    # ── Context Manager ───────────────────────────────────

    def acquire(self, name: str, timeout: int | None = None, connection: str | None = None) -> _LockContext:
        return _LockContext(self, name, timeout, connection)

    # ── Low-level ─────────────────────────────────────────

    async def try_acquire(self, name: str, connection: str | None = None) -> bool:
        """Try to acquire lock (non-blocking). Returns True if acquired."""
        dialect = self._get_dialect()

        async with self._manager.session(connection) as session:
            if dialect == "postgresql":
                lock_id = self._lock_id(name)
                result = await session.execute(text(f"SELECT pg_try_advisory_lock({lock_id})"))
                return result.scalar_one()

            elif dialect == "mysql":
                result = await session.execute(
                    text("SELECT GET_LOCK(:name, 0)"),
                    {"name": name},
                )
                return result.scalar_one() == 1

        return False

    async def acquire_blocking(self, name: str, timeout: int | None = None, connection: str | None = None) -> bool:
        """Acquire lock (blocking)."""
        dialect = self._get_dialect()

        async with self._manager.session(connection) as session:
            if dialect == "postgresql":
                lock_id = self._lock_id(name)
                await session.execute(text(f"SELECT pg_advisory_lock({lock_id})"))
                return True

            elif dialect == "mysql":
                t = timeout or 10
                result = await session.execute(text("SELECT GET_LOCK(:name, :timeout)"), {"name": name, "timeout": t})
                return result.scalar_one() == 1

        return False

    async def release(self, name: str, connection: str | None = None) -> bool:
        """Release a lock."""
        dialect = self._get_dialect()

        async with self._manager.session(connection) as session:
            if dialect == "postgresql":
                lock_id = self._lock_id(name)
                result = await session.execute(text(f"SELECT pg_advisory_unlock({lock_id})"))
                return result.scalar_one()

            elif dialect == "mysql":
                result = await session.execute(
                    text("SELECT RELEASE_LOCK(:name)"),
                    {"name": name},
                )
                return result.scalar_one() == 1

        return False

    def __repr__(self) -> str:
        return f"<DatabaseLock dialect={self._get_dialect()}>"


class _LockContext:
    """Async context manager for locks."""

    __slots__ = ("_acquired", "_connection", "_lock", "_name", "_timeout")

    def __init__(self, lock, name, timeout, connection):
        self._lock = lock
        self._name = name
        self._timeout = timeout
        self._connection = connection
        self._acquired = False

    async def __aenter__(self) -> _LockContext:
        self._acquired = await self._lock.acquire_blocking(self._name, self._timeout, self._connection)
        if not self._acquired:
            raise TimeoutError(f"Could not acquire lock: {self._name}")
        logger.debug("🔒 Lock acquired: %s", self._name)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._acquired:
            await self._lock.release(self._name, self._connection)
            logger.debug("🔓 Lock released: %s", self._name)
