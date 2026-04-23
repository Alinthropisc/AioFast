from __future__ import annotations

import pytest
from sqlalchemy import select

from core.database.model import BaseModel
from core.database.tenant import (
    TenantRegistry,
    clear_tenant,
    get_tenant,
    set_tenant,
)
from core.testing.database.conftest import TenantPost


@pytest.fixture(autouse=True)
async def _create_tenant_table(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    TenantRegistry.register(TenantPost)
    yield
    clear_tenant()


class TestTenantContext:
    def test_set_and_get(self):
        set_tenant("tenant_1")
        assert get_tenant() == "tenant_1"

    def test_clear(self):
        set_tenant("tenant_1")
        clear_tenant()
        assert get_tenant() is None

    def test_default_none(self):
        clear_tenant()
        assert get_tenant() is None


class TestTenantMixin:
    @pytest.mark.asyncio
    async def test_auto_set_tenant_on_insert(self, session):
        set_tenant("company_a")

        post = TenantPost(title="Hello")
        session.add(post)
        await session.flush()
        await session.refresh(post)

        assert post.tenant_id == "company_a"

    @pytest.mark.asyncio
    async def test_manual_tenant_id(self, session):
        """If tenant_id is set manually, don't override."""
        set_tenant("company_a")

        post = TenantPost(title="Manual", tenant_id="company_b")
        session.add(post)
        await session.flush()
        await session.refresh(post)

        assert post.tenant_id == "company_b"

    @pytest.mark.asyncio
    async def test_filter_by_tenant(self, session):
        # Create posts for different tenants
        set_tenant("tenant_1")
        p1 = TenantPost(title="T1 Post 1")
        p2 = TenantPost(title="T1 Post 2")
        session.add_all([p1, p2])
        await session.flush()

        clear_tenant()
        p3 = TenantPost(title="T2 Post 1", tenant_id="tenant_2")
        session.add(p3)
        await session.flush()

        # Apply filter
        query = TenantRegistry.apply_filter(select(TenantPost), TenantPost)
        # Without tenant set — no filter applied
        clear_tenant()
        result = await session.execute(select(TenantPost))
        all_posts = result.scalars().all()
        assert len(all_posts) == 3

        # With tenant set — filtered
        set_tenant("tenant_1")
        query = TenantRegistry.apply_filter(select(TenantPost), TenantPost)
        result = await session.execute(query)
        filtered = result.scalars().all()
        assert len(filtered) == 2
        assert all(p.tenant_id == "tenant_1" for p in filtered)
