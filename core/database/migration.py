from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Alembic wrapper + quick helpers.

    Usage:
        mgr = MigrationManager(db_manager)

        # Quick (dev/testing) — no Alembic needed:
        await mgr.create_tables()
        await mgr.drop_tables()
        await mgr.fresh()           # drop + create

        # Production — Alembic:
        mgr.init()                   # init migration dir
        mgr.make("create users")     # autogenerate revision
        await mgr.migrate()          # upgrade head
        await mgr.rollback()         # downgrade -1
        await mgr.reset()            # downgrade base
    """

    def __init__(self, manager: DatabaseManager, directory: str = "migrations") -> None:
        self._manager = manager
        self._directory = Path(directory)

    # ── Quick helpers (no Alembic) ────────────────────────

    async def create_tables(self) -> None:
        """Create all tables from registered models."""
        from .model import Model

        engine = self._manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(Model.metadata.create_all)
        logger.info("✅ All tables created")

    async def drop_tables(self) -> None:
        """Drop all tables."""
        from .model import Model

        engine = self._manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(Model.metadata.drop_all)
        logger.info("🗑️ All tables dropped")

    async def fresh(self) -> None:
        """Drop all tables + create fresh."""
        await self.drop_tables()
        await self.create_tables()
        logger.info("🔄 Database refreshed")

    # ── Alembic wrappers ──────────────────────────────────

    def _get_config(self):
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(self._directory))

        # Получаем sync URL для Alembic
        engine = self._manager.engine()
        url = str(engine.url)
        config.set_main_option("sqlalchemy.url", url)

        return config

    def init(self) -> None:
        """Initialize Alembic migration directory."""
        from alembic import command

        if self._directory.exists():
            logger.warning("Directory exists: %s", self._directory)
            return

        config = self._get_config()
        command.init(config, str(self._directory))
        self._write_async_env()
        logger.info("✅ Migrations initialized: %s", self._directory)

    def make(self, message: str, *, autogenerate: bool = True) -> str:
        """Create a new migration revision."""
        from alembic import command

        config = self._get_config()
        rev = command.revision(config, message=message, autogenerate=autogenerate)
        logger.info("✅ Migration created: %s", message)
        return str(rev)

    async def migrate(self, revision: str = "head") -> None:
        """Run pending migrations (upgrade)."""
        from alembic import command

        config = self._get_config()

        engine = self._manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: command.upgrade(config, revision))
        logger.info("✅ Migrated to: %s", revision)

    async def rollback(self, steps: int = 1) -> None:
        """Rollback N migration steps."""
        from alembic import command

        config = self._get_config()
        target = f"-{steps}"

        engine = self._manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: command.downgrade(config, target))
        logger.info("✅ Rolled back %d step(s)", steps)

    async def reset(self) -> None:
        """Rollback ALL migrations."""
        from alembic import command

        config = self._get_config()
        engine = self._manager.engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: command.downgrade(config, "base"))
        logger.info("✅ All migrations rolled back")

    async def status(self) -> dict:
        """Get migration status info."""
        from alembic.script import ScriptDirectory

        config = self._get_config()
        script = ScriptDirectory.from_config(config)

        return {
            "directory": str(self._directory),
            "heads": list(script.get_heads()),
            "revisions": [
                {
                    "revision": rev.revision,
                    "message": rev.doc,
                    "down": rev.down_revision,
                }
                for rev in script.walk_revisions()
            ],
        }

    def _write_async_env(self) -> None:
        """Generate async-compatible env.py."""
        env_path = self._directory / "env.py"
        env_path.write_text(_ASYNC_ENV_TEMPLATE.strip(), encoding="utf-8")


_ASYNC_ENV_TEMPLATE = """
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from aiofast.database.model import Model

target_metadata = Model.metadata
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
