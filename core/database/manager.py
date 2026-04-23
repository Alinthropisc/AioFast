from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, StaticPool

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for a single database connection."""

    __slots__ = (
        "connect_args",
        "echo",
        "execution_options",
        "max_overflow",
        "name",
        "pool_pre_ping",
        "pool_recycle",
        "pool_size",
        "pool_timeout",
        "url",
    )

    def __init__(
        self,
        name: str = "default",
        url: str = "sqlite+aiosqlite:///db.sqlite3",
        *,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        connect_args: dict[str, Any] | None = None,
        execution_options: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.url = url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.connect_args = connect_args or {}
        self.execution_options = execution_options or {}

    def __repr__(self) -> str:
        # Mask password in URL
        import re

        safe_url = re.sub(r"://[^:]+:[^@]+@", "://***:***@", self.url)
        return f"<DatabaseConfig name={self.name!r} url={safe_url!r}>"


class DatabaseManager:
    """
    Manages database engines and session factories.

    Like Laravel's DatabaseManager — handles multiple connections,
    provides session factory, manages lifecycle.

    Usage:
        manager = DatabaseManager()
        manager.add_connection(DatabaseConfig(
            name="default",
            url="postgresql+asyncpg://user:pass@localhost/mydb",
        ))
        await manager.connect_all()

        # Get session
        async with manager.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

        # Multiple databases
        async with manager.session("analytics") as session:
            ...

        await manager.disconnect_all()
    """

    def __init__(self) -> None:
        self._configs: dict[str, DatabaseConfig] = {}
        self._engines: dict[str, AsyncEngine] = {}
        self._session_factories: dict[str, async_sessionmaker[AsyncSession]] = {}
        self._default: str = "default"
        self._connected: bool = False

    # ── configuration ─────────────────────────────────────

    def add_connection(self, config: DatabaseConfig, *, default: bool = False) -> DatabaseManager:
        """Add a database connection configuration."""
        self._configs[config.name] = config
        if default or len(self._configs) == 1:
            self._default = config.name
        logger.debug("Added connection: %s", config.name)
        return self

    def set_default(self, name: str) -> DatabaseManager:
        if name not in self._configs:
            raise KeyError(f"Connection '{name}' not configured")
        self._default = name
        return self

    @property
    def default_connection(self) -> str:
        return self._default

    @property
    def connections(self) -> list[str]:
        return list(self._configs.keys())

    # ── lifecycle ─────────────────────────────────────────

    async def connect(self, name: str | None = None) -> AsyncEngine:
        conn_name = name or self._default
        if conn_name in self._engines:
            return self._engines[conn_name]

        config = self._configs.get(conn_name)
        if config is None:
            raise KeyError(f"Connection '{conn_name}' not configured")

        is_sqlite = "sqlite" in config.url

        # Базовые аргументы
        kwargs = {
            "echo": config.echo,
            "connect_args": config.connect_args,
            "execution_options": config.execution_options,
        }

        if is_sqlite:
            # Для SQLite не передаём параметры пула
            kwargs["poolclass"] = NullPool
        else:
            # Для других БД передаём все параметры пула
            kwargs.update(
                {
                    "pool_size": config.pool_size,
                    "max_overflow": config.max_overflow,
                    "pool_timeout": config.pool_timeout,
                    "pool_recycle": config.pool_recycle,
                    "pool_pre_ping": config.pool_pre_ping,
                    "poolclass": AsyncAdaptedQueuePool,
                }
            )

        engine = create_async_engine(config.url, **kwargs)

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        self._engines[conn_name] = engine
        self._session_factories[conn_name] = factory

        logger.info("Connected to database: %s", conn_name)
        return engine

    async def connect_all(self) -> None:
        """Connect all configured databases."""
        for name in self._configs:
            await self.connect(name)
        self._connected = True

    async def disconnect(self, name: str | None = None) -> None:
        """Disconnect a specific database."""
        conn_name = name or self._default
        engine = self._engines.pop(conn_name, None)
        self._session_factories.pop(conn_name, None)
        if engine is not None:
            await engine.dispose()
            logger.info("Disconnected from database: %s", conn_name)

    async def disconnect_all(self) -> None:
        """Disconnect all databases."""
        for name in list(self._engines.keys()):
            await self.disconnect(name)
        self._connected = False

    async def aclose(self) -> None:
        """Alias for container cleanup."""
        await self.disconnect_all()

    # ── session management ────────────────────────────────

    def session(self, connection: str | None = None) -> _SessionContext:
        """
        Get an async session context manager.

        Usage:
            async with manager.session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        conn_name = connection or self._default
        return _SessionContext(self, conn_name)

    def session_factory(self, connection: str | None = None) -> async_sessionmaker[AsyncSession]:
        """Get raw session factory for a connection."""
        conn_name = connection or self._default
        factory = self._session_factories.get(conn_name)
        if factory is None:
            raise RuntimeError(f"Connection '{conn_name}' not connected. Call connect() first.")
        return factory

    async def create_session(self, connection: str | None = None) -> AsyncSession:
        """Create a new session (caller must close it)."""
        factory = self.session_factory(connection)
        return factory()

    # ── engine access ─────────────────────────────────────

    def engine(self, connection: str | None = None) -> AsyncEngine:
        """Get engine for a connection."""
        conn_name = connection or self._default
        engine = self._engines.get(conn_name)
        if engine is None:
            raise RuntimeError(f"Connection '{conn_name}' not connected")
        return engine

    # ── raw execution ─────────────────────────────────────

    async def execute(self, statement: Any, connection: str | None = None) -> Any:
        """Execute a raw statement."""
        async with self.session(connection) as session:
            result = await session.execute(statement)
            await session.commit()
            return result

    # ── health check ──────────────────────────────────────

    async def ping(self, connection: str | None = None) -> bool:
        """Check if database is reachable."""
        try:
            conn_name = connection or self._default
            engine = self.engine(conn_name)
            async with engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database ping failed: %s", e)
            return False

    async def ping_all(self) -> dict[str, bool]:
        """Ping all connections."""
        return {name: await self.ping(name) for name in self._engines}

    # ── info ──────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected and bool(self._engines)

    def pool_status(self, connection: str | None = None) -> dict[str, Any]:
        """Get connection pool status."""
        conn_name = connection or self._default
        engine = self._engines.get(conn_name)
        if engine is None:
            return {}
        pool = engine.pool
        # StaticPool / NullPool не имеют метрик пула
        if isinstance(pool, (NullPool, StaticPool)):
            return {
                "pool": type(pool).__name__,
                "size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
            }
        return {
            "pool": type(pool).__name__,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }

    def __repr__(self) -> str:
        names = list(self._configs.keys())
        status = "connected" if self._connected else "disconnected"
        return f"<DatabaseManager connections={names} [{status}]>"


class _SessionContext:
    """Async context manager for sessions with auto-commit/rollback."""

    __slots__ = ("_connection", "_manager", "_session")

    def __init__(self, manager: DatabaseManager, connection: str) -> None:
        self._manager = manager
        self._connection = connection
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        factory = self._manager.session_factory(self._connection)
        self._session = factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
            self._session = None
