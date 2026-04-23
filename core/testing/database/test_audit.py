from __future__ import annotations

import pytest
from sqlalchemy import select

from core.database.audit import (
    AuditLog,
    AuditRegistry,
    clear_audit_context,
    set_audit_context,
)
from core.database.model import BaseModel
from core.testing.database.conftest import AuditedUser


@pytest.fixture(autouse=True)
async def _setup_audit(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    AuditRegistry.register(AuditedUser)
    AuditRegistry.enable()
    yield
    clear_audit_context()


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_insert_creates_log(self, session):
        set_audit_context(user_id="admin_1", ip_address="127.0.0.1")

        user = AuditedUser(name="Alice", email="alice@audit.com")
        session.add(user)
        await session.flush()

        # Check audit log
        result = await session.execute(select(AuditLog).where(AuditLog.action == "created"))
        logs = result.scalars().all()
        assert len(logs) >= 1

        log = logs[-1]
        assert log.model_type == "AuditedUser"
        assert log.action == "created"
        assert log.user_id == "admin_1"
        assert log.ip_address == "127.0.0.1"
        assert '"name"' in log.new_values
        assert '"Alice"' in log.new_values

    @pytest.mark.asyncio
    async def test_update_creates_log(self, session):
        set_audit_context(user_id="admin_1")

        user = AuditedUser(name="Bob", email="bob@audit.com")
        session.add(user)
        await session.flush()

        user.name = "Bob Updated"
        await session.flush()

        result = await session.execute(select(AuditLog).where(AuditLog.action == "updated"))
        logs = result.scalars().all()
        assert len(logs) >= 1

        log = logs[-1]
        assert '"Bob"' in (log.old_values or "")
        assert '"Bob Updated"' in (log.new_values or "")

    @pytest.mark.asyncio
    async def test_delete_creates_log(self, session):
        set_audit_context(user_id="admin_1")

        user = AuditedUser(name="Charlie", email="charlie@audit.com")
        session.add(user)
        await session.flush()

        await session.delete(user)
        await session.flush()

        result = await session.execute(select(AuditLog).where(AuditLog.action == "deleted"))
        logs = result.scalars().all()
        assert len(logs) >= 1

    @pytest.mark.asyncio
    async def test_audit_fields_filter(self, session):
        """secret field should NOT be tracked."""
        set_audit_context(user_id="admin_1")

        user = AuditedUser(name="Diana", email="diana@audit.com", secret="top_secret")
        session.add(user)
        await session.flush()

        result = await session.execute(select(AuditLog).where(AuditLog.action == "created"))
        log = result.scalars().all()[-1]
        assert "secret" not in (log.new_values or "")
        assert "top_secret" not in (log.new_values or "")

    @pytest.mark.asyncio
    async def test_disable_audit(self, session):
        AuditRegistry.disable()

        user = AuditedUser(name="NoAudit", email="noaudit@test.com")
        session.add(user)
        await session.flush()

        result = await session.execute(select(AuditLog).where(AuditLog.model_id == str(user.id)))
        assert len(result.scalars().all()) == 0

        AuditRegistry.enable()

    @pytest.mark.asyncio
    async def test_no_context(self, session):
        """Audit should work even without context (user_id=None)."""
        clear_audit_context()

        user = AuditedUser(name="NoCtx", email="noctx@test.com")
        session.add(user)
        await session.flush()

        result = await session.execute(select(AuditLog).where(AuditLog.action == "created"))
        logs = result.scalars().all()
        last = logs[-1]
        assert last.user_id is None
