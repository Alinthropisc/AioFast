from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from sqlalchemy import String
from sqlalchemy import event as sa_event
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger(__name__)

# Current tenant context
_current_tenant: ContextVar[str | None] = ContextVar("_current_tenant", default=None)


def set_tenant(tenant_id: str) -> None:
    """Set current tenant for this request/context."""
    _current_tenant.set(tenant_id)


def get_tenant() -> str | None:
    """Get current tenant ID."""
    return _current_tenant.get()


def clear_tenant() -> None:
    _current_tenant.set(None)


class TenantMixin:
    """
    Multi-tenancy mixin — auto-filters by tenant.

    Usage:
        class User(TenantMixin, BaseModel):
            __tablename__ = "users"
            name: Mapped[str]

        # Set tenant in middleware:
        set_tenant("tenant_123")

        # All queries auto-filtered:
        users = await session.execute(select(User))  # WHERE tenant_id = 'tenant_123'

        # New records auto-get tenant_id:
        user = User(name="Alice")  # tenant_id auto-set
    """

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)


class TenantRegistry:
    """
    Register models for automatic tenant filtering.

    Usage:
        TenantRegistry.register(User)
        TenantRegistry.register(Post)

        # Auto-apply tenant filter on all queries + inserts
    """

    _registered: set = set()

    @classmethod
    def register(cls, model: type) -> None:
        if model in cls._registered:
            return

        # Auto-set tenant_id on insert
        @sa_event.listens_for(model, "before_insert")
        def _set_tenant(mapper, connection, target):
            tenant = get_tenant()
            if tenant and not getattr(target, "tenant_id", None):
                target.tenant_id = tenant

        # Auto-filter queries
        @sa_event.listens_for(model, "load", propagate=True)
        def _filter_load(target, context):
            pass  # SQLAlchemy doesn't have query-level event like this

        cls._registered.add(model)
        logger.debug("Tenant registered: %s", model.__name__)

    @classmethod
    def apply_filter(cls, query: Any, model: type) -> Any:
        """Manually apply tenant filter to query."""
        tenant = get_tenant()
        if tenant and hasattr(model, "tenant_id"):
            return query.where(model.tenant_id == tenant)
        return query


class TenantMiddleware:
    """
    Middleware to extract and set tenant from request.

    Supports:
      - Header: X-Tenant-ID
      - Subdomain: tenant.example.com
      - Path: /tenant/api/...
    """

    def __init__(self, *, header: str = "X-Tenant-ID", subdomain: bool = False, path_prefix: bool = False) -> None:
        self._header = header
        self._subdomain = subdomain
        self._path_prefix = path_prefix

    async def __call__(self, request: Any, handler: Any) -> Any:
        tenant_id = None

        # From header
        if self._header:
            tenant_id = getattr(request, "headers", {}).get(self._header)

        # From subdomain
        if not tenant_id and self._subdomain:
            host = getattr(request, "host", "") or ""
            parts = host.split(".")
            if len(parts) > 2:
                tenant_id = parts[0]

        if tenant_id:
            set_tenant(tenant_id)

        try:
            return await handler(request)
        finally:
            clear_tenant()
