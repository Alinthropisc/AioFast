from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class ReplicaManager:
    """
    Read/Write splitting — route reads to replicas, writes to master.

    Usage:
        replica = ReplicaManager(db_manager)
        replica.set_write("master")
        replica.add_read("replica1")
        replica.add_read("replica2")

        # Auto-routing:
        async with replica.read_session() as session:
            users = await session.execute(select(User))  # → replica

        async with replica.write_session() as session:
            session.add(user)  # → master

        # Strategy:
        replica.strategy = "round_robin"  # or "random", "least_connections"
    """

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager
        self._write_conn: str = "default"
        self._read_conns: list[str] = []
        self._strategy: str = "random"
        self._rr_index: int = 0

    # ── Config ────────────────────────────────────────────

    def set_write(self, connection: str) -> ReplicaManager:
        """Set the write (master) connection."""
        self._write_conn = connection
        return self

    def add_read(self, connection: str) -> ReplicaManager:
        """Add a read (replica) connection."""
        if connection not in self._read_conns:
            self._read_conns.append(connection)
        return self

    @property
    def strategy(self) -> str:
        return self._strategy

    @strategy.setter
    def strategy(self, value: str) -> None:
        if value not in ("random", "round_robin", "first"):
            raise ValueError(f"Unknown strategy: {value}")
        self._strategy = value

    # ── Sessions ──────────────────────────────────────────

    def write_session(self):
        """Get session for write operations (master)."""
        return self._manager.session(self._write_conn)

    def read_session(self):
        """Get session for read operations (replica)."""
        conn = self._pick_read()
        return self._manager.session(conn)

    def session(self, *, write: bool = False):
        """Get session, auto-routing by intent."""
        if write:
            return self.write_session()
        return self.read_session()

    # ── Pick strategy ─────────────────────────────────────

    def _pick_read(self) -> str:
        """Pick a read connection based on strategy."""
        if not self._read_conns:
            return self._write_conn

        if self._strategy == "random":
            return random.choice(self._read_conns)

        if self._strategy == "round_robin":
            conn = self._read_conns[self._rr_index % len(self._read_conns)]
            self._rr_index += 1
            return conn

        if self._strategy == "first":
            return self._read_conns[0]

        return self._read_conns[0]

    # ── Health ────────────────────────────────────────────

    async def healthy_read(self) -> str | None:
        """Get first healthy read connection."""
        for conn in self._read_conns:
            if await self._manager.ping(conn):
                return conn
        logger.warning("No healthy replicas, falling back to master")
        return self._write_conn

    async def status(self) -> dict:
        """Status of all connections."""
        result = {
            "write": {
                "connection": self._write_conn,
                "healthy": await self._manager.ping(self._write_conn),
            },
            "read": [],
        }
        for conn in self._read_conns:
            result["read"].append({"connection": conn, "healthy": await self._manager.ping(conn)})
        return result

    def __repr__(self) -> str:
        return f"<ReplicaManager write={self._write_conn} reads={self._read_conns} strategy={self._strategy}>"
