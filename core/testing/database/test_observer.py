from __future__ import annotations

import pytest

from core.database.model import BaseModel
from core.database.observer import ModelObserver, ObserverRegistry
from core.testing.database.conftest import ObsUser


@pytest.fixture(autouse=True)
def _clean_observers():
    ObserverRegistry.clear()
    yield
    ObserverRegistry.clear()


@pytest.fixture(autouse=True)
async def _create_obs_table(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield


class TrackingObserver(ModelObserver):
    def __init__(self):
        self.events = []

    def creating(self, instance):
        self.events.append("creating")

    def created(self, instance):
        self.events.append("created")

    def updating(self, instance):
        self.events.append("updating")

    def updated(self, instance):
        self.events.append("updated")

    def deleting(self, instance):
        self.events.append("deleting")

    def deleted(self, instance):
        self.events.append("deleted")

    def saving(self, instance):
        self.events.append("saving")

    def saved(self, instance):
        self.events.append("saved")


class TestObserver:
    @pytest.mark.asyncio
    async def test_creating_created(self, session):
        obs = TrackingObserver()
        ObserverRegistry.observe(ObsUser, obs)

        user = ObsUser(name="Alice", email="a@t.com")
        session.add(user)
        await session.flush()

        assert "saving" in obs.events
        assert "creating" in obs.events
        assert "created" in obs.events
        assert "saved" in obs.events

    @pytest.mark.asyncio
    async def test_updating_updated(self, session):
        obs = TrackingObserver()
        ObserverRegistry.observe(ObsUser, obs)

        user = ObsUser(name="Bob", email="b@t.com")
        session.add(user)
        await session.flush()

        obs.events.clear()

        user.name = "Updated"
        await session.flush()

        assert "updating" in obs.events
        assert "updated" in obs.events

    @pytest.mark.asyncio
    async def test_deleting_deleted(self, session):
        obs = TrackingObserver()
        ObserverRegistry.observe(ObsUser, obs)

        user = ObsUser(name="Charlie", email="c@t.com")
        session.add(user)
        await session.flush()

        obs.events.clear()

        await session.delete(user)
        await session.flush()

        assert "deleting" in obs.events
        assert "deleted" in obs.events

    @pytest.mark.asyncio
    async def test_multiple_observers(self, session):
        obs1 = TrackingObserver()
        obs2 = TrackingObserver()
        ObserverRegistry.observe(ObsUser, obs1)
        ObserverRegistry.observe(ObsUser, obs2)

        user = ObsUser(name="Dave", email="d@t.com")
        session.add(user)
        await session.flush()

        assert "creating" in obs1.events
        assert "creating" in obs2.events
