from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# ── Event DTOs ────────────────────────────────────────────


@dataclass
class QueryExecuted:
    """Fired after every query."""

    sql: str
    params: Any
    duration: float  # seconds
    connection: str = "default"


@dataclass
class QueryFailed:
    """Fired when a query fails."""

    sql: str
    params: Any
    error: Exception
    connection: str = "default"


@dataclass
class TransactionBeginning:
    connection: str = "default"


@dataclass
class TransactionCommitted:
    connection: str = "default"


@dataclass
class TransactionRolledBack:
    connection: str = "default"


# ── Query Logger ──────────────────────────────────────────


class QueryLogger:
    """
    Logs all executed queries. Detects slow queries.

    Usage:
        query_logger = QueryLogger(slow_threshold=0.5)
        query_logger.attach(engine)

        # After queries...
        print(query_logger.summary())
        print(query_logger.slow_queries)
    """

    def __init__(self, slow_threshold: float = 1.0) -> None:
        self.slow_threshold = slow_threshold
        self.queries: list[QueryExecuted] = []
        self._listeners: list[Callable[[QueryExecuted], None]] = []

    def attach(self, engine: Any, connection_name: str = "default") -> None:
        """Attach to SQLAlchemy engine — intercept all queries."""
        from sqlalchemy import event as sa_event

        sync_engine = engine.sync_engine

        @sa_event.listens_for(sync_engine, "before_cursor_execute")
        def _before(conn, cursor, stmt, params, context, executemany):
            conn.info["_query_start"] = time.perf_counter()

        @sa_event.listens_for(sync_engine, "after_cursor_execute")
        def _after(conn, cursor, stmt, params, context, executemany):
            start = conn.info.pop("_query_start", None)
            duration = time.perf_counter() - start if start else 0.0
            event = QueryExecuted(sql=stmt, params=params, duration=duration, connection=connection_name)
            self.queries.append(event)

            if duration > self.slow_threshold:
                logger.warning("⚠️ SLOW QUERY (%.3fs): %s", duration, stmt[:200])

            for listener in self._listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error("Query listener error: %s", e)

        @sa_event.listens_for(sync_engine, "handle_error")
        def _error(exception_context):
            evt = QueryFailed(
                sql=str(exception_context.statement or ""),
                params=exception_context.parameters,
                error=exception_context.original_exception,
                connection=connection_name,
            )
            logger.error("❌ Query failed: %s — %s", evt.sql[:200], evt.error)

    def on_query(self, callback: Callable[[QueryExecuted], None]) -> None:
        """Register a listener for every executed query."""
        self._listeners.append(callback)

    @property
    def slow_queries(self) -> list[QueryExecuted]:
        return [q for q in self.queries if q.duration > self.slow_threshold]

    @property
    def total_time(self) -> float:
        return sum(q.duration for q in self.queries)

    @property
    def query_count(self) -> int:
        return len(self.queries)

    def reset(self) -> None:
        self.queries.clear()

    def summary(self) -> dict[str, Any]:
        return {
            "total_queries": self.query_count,
            "total_time": round(self.total_time, 4),
            "slow_queries": len(self.slow_queries),
            "avg_time": round(self.total_time / max(self.query_count, 1), 4),
        }

    def __repr__(self) -> str:
        return f"<QueryLogger queries={self.query_count} slow={len(self.slow_queries)}>"
