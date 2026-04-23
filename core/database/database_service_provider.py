from __future__ import annotations

import contextlib
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..foundation.service_provider import ServiceProvider
from .manager import DatabaseConfig, DatabaseManager
from .query import DB


class DatabaseServiceProvider(ServiceProvider):
    """
    Registers:
      - DatabaseManager → singleton
      - DB (query facade) → singleton
      - AsyncSession → scoped (per request)
      - UnitOfWork → transient
    """

    async def register(self) -> None:
        manager = DatabaseManager()

        self.app.instance("db.manager", manager)
        self.app.instance(DatabaseManager, manager)

        db = DB(manager)
        self.app.instance("db", db)
        self.app.instance(DB, db)

        async def session_factory(container: Any) -> AsyncSession:
            mgr: DatabaseManager = await container.make(DatabaseManager)
            return await mgr.create_session()

        self.app.scoped(AsyncSession, session_factory)

    async def boot(self) -> None:
        manager: DatabaseManager = await self.app.make(DatabaseManager)
        configs = await self._load_configs()

        for config in configs:
            manager.add_connection(config)

        if configs:
            await manager.connect_all()

            # Attach query logger if echo enabled
            if any(c.echo for c in configs):
                from .events import QueryLogger

                query_logger = QueryLogger()
                for name in manager.connections:
                    with contextlib.suppress(RuntimeError):
                        query_logger.attach(manager.engine(name), name)
                self.app.instance(QueryLogger, query_logger)

    async def _load_configs(self) -> list[DatabaseConfig]:
        configs: list[DatabaseConfig] = []

        config_manager = await self.app.make_or("config")
        if config_manager is not None:
            db_config = config_manager.get("database")
            if db_config is not None:
                return self._parse_config_manager(db_config)

        url = os.getenv("DATABASE_URL", "")
        if url:
            configs.append(
                DatabaseConfig(
                    name="default",
                    url=url,
                    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
                    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
                    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
                )
            )
        return configs

    def _parse_config_manager(self, db_config: Any) -> list[DatabaseConfig]:
        configs: list[DatabaseConfig] = []

        if hasattr(db_config, "to_dict"):
            data = db_config.to_dict()
        elif isinstance(db_config, dict):
            data = db_config
        else:
            return configs

        connections = data.get("connections", {})
        default = data.get("default", "default")

        for name, conn_data in connections.items():
            if isinstance(conn_data, dict):
                url = conn_data.get("url", "")
                if url:
                    configs.append(
                        DatabaseConfig(
                            name=name,
                            url=url,
                            echo=conn_data.get("echo", False),
                            pool_size=conn_data.get("pool_size", 5),
                            max_overflow=conn_data.get("max_overflow", 10),
                            pool_timeout=conn_data.get("pool_timeout", 30),
                            pool_recycle=conn_data.get("pool_recycle", 3600),
                            pool_pre_ping=conn_data.get("pool_pre_ping", True),
                        )
                    )

        if configs:
            manager: DatabaseManager = self.app._bindings[DatabaseManager].instance  # ty:ignore[invalid-assignment]
            manager.set_default(default)

        return configs
