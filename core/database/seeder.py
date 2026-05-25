from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import delete as sa_delete

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Seeder(ABC):
    """
    Base seeder — like Laravel's Seeder.

    Usage:
        class UserSeeder(Seeder):
            async def run(self):
                await self.create(User, [
                    {"name": "Admin", "email": "admin@app.com"},
                    {"name": "User",  "email": "user@app.com"},
                ])

        class DatabaseSeeder(Seeder):
            async def run(self):
                await self.call(UserSeeder, PostSeeder)

        # Execute:
        async with manager.session() as session:
            seeder = DatabaseSeeder(session)
            await seeder.run()
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def run(self) -> None:
        """Override: seed the database."""

    async def call(self, *seeder_classes: type[Seeder]) -> None:
        """Run child seeders."""
        for cls in seeder_classes:
            seeder = cls(self._session)
            logger.info("🌱 Seeding: %s", cls.__name__)
            await seeder.run()

    async def create(self, model: type, data: dict[str, Any] | list[dict[str, Any]]) -> list[Any]:
        """Create multiple records from dicts."""
        if isinstance(data, dict):
            data = [data]
        instances = [model(**item) for item in data]
        self._session.add_all(instances)
        await self._session.flush()
        for inst in instances:
            await self._session.refresh(inst)
        logger.info("✅ Seeded %d %s records", len(instances), model.__name__)
        return instances

    async def create_one(self, model: type, **kwargs: Any) -> Any:
        """Create single record."""
        instance = model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def truncate(self, model: type) -> None:
        """Delete all records from table."""
        await self._session.execute(sa_delete(model))
        await self._session.flush()
        logger.info("  🗑️ Truncated: %s", model.__name__)


# ── Factory ───────────────────────────────────────────────


class Factory(Generic[T]):
    """
    Model factory with Faker — like Laravel's Factory.

    Usage:
        class UserFactory(Factory[User]):
            model = User

            def definition(self) -> dict:
                return {
                    "name": self.faker.name(),
                    "email": self.faker.unique.email(),
                }

        factory = UserFactory()

        # In-memory (no DB):
        user = factory.make()
        users = factory.make_many(5)

        # Persisted:
        user = await factory.create(session)
        users = await factory.create_many(session, 10)

        # With overrides:
        admin = await factory.create(session, name="Admin")

        # With state:
        factory.state(is_active=False)
        banned = await factory.create(session)
    """

    model: type[T]

    def __init__(self) -> None:
        self._states: dict[str, Any] = {}
        self._faker: Any = None

    @property
    def faker(self) -> Any:
        if self._faker is None:
            try:
                from faker import Faker

                self._faker = Faker()
            except ImportError as exc:
                raise ImportError("Install faker: pip install faker") from exc
        return self._faker

    def definition(self) -> dict[str, Any]:
        """Override: default attribute values."""
        raise NotImplementedError

    def state(self, **attrs: Any) -> Factory[T]:
        """Apply state overrides."""
        self._states.update(attrs)
        return self

    def reset_state(self) -> Factory[T]:
        self._states.clear()
        return self

    # ── Make (no DB) ──────────────────────────────────────

    def make(self, **overrides: Any) -> T:
        """Create instance without saving."""
        data = {**self.definition(), **self._states, **overrides}
        return self.model(**data)

    def make_many(self, count: int, **overrides: Any) -> list[T]:
        return [self.make(**overrides) for _ in range(count)]

    # ── Create (with DB) ──────────────────────────────────

    async def create(self, session: AsyncSession, **overrides: Any) -> T:
        """Create and persist."""
        instance = self.make(**overrides)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def create_many(self, session: AsyncSession, count: int, **overrides: Any) -> list[T]:
        """Create and persist multiple."""
        instances = self.make_many(count, **overrides)
        session.add_all(instances)
        await session.flush()
        for inst in instances:
            await session.refresh(inst)
        return instances

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model.__name__}>"
