from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, inspect
from sqlalchemy import event as sa_event
from sqlalchemy.orm import Mapped, mapped_column

from .model import Model

logger = logging.getLogger(__name__)


class AuditLog(Model):
    """
    Audit log table — tracks all changes to audited models.

    Stores: who, what, when, old values, new values.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(20))  # created, updated, deleted
    model_type: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str] = mapped_column(String(100))
    old_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Context holder ────────────────────────────────────────


class _AuditContext:
    """Thread/context-local storage for current user info."""

    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


_context = _AuditContext()


def set_audit_context(user_id: str | None = None, ip_address: str | None = None, user_agent: str | None = None) -> None:
    """Set current audit context (call from middleware)."""
    _context.user_id = user_id
    _context.ip_address = ip_address
    _context.user_agent = user_agent


def clear_audit_context() -> None:
    _context.user_id = None
    _context.ip_address = None
    _context.user_agent = None


# ── Auditable Mixin ──────────────────────────────────────


class AuditableMixin:
    """
    Add to models to auto-track changes.

    Usage:
        class User(AuditableMixin, BaseModel):
            __tablename__ = "users"
            __audit_fields__ = ["name", "email", "role"]  # optional: limit tracked fields

            name: Mapped[str]
            email: Mapped[str]

        # Changes are auto-logged to audit_logs table
    """

    __audit_fields__: list[str] | None = None  # None = track all
    __audit_exclude__: list[str] = ["updated_at", "created_at"]  # skip these


class AuditRegistry:
    """
    Central audit registry.

    Usage:
        AuditRegistry.register(User)
        AuditRegistry.register(Post)

        # Or auto-detect AuditableMixin models
        AuditRegistry.auto_register()
    """

    _registered: set = set()
    _enabled: bool = True
    _session_factory: Any | None = None

    @classmethod
    def configure(cls, session_factory: Any) -> None:
        """Set session factory for writing audit logs."""
        cls._session_factory = session_factory

    @classmethod
    def register(cls, model: type) -> None:
        """Register a model for auditing."""
        if model in cls._registered:
            return

        cls._setup_events(model)
        cls._registered.add(model)
        logger.debug("Audit registered: %s", model.__name__)

    @classmethod
    def disable(cls) -> None:
        cls._enabled = False

    @classmethod
    def enable(cls) -> None:
        cls._enabled = True

    @classmethod
    def _setup_events(cls, model: type) -> None:

        @sa_event.listens_for(model, "after_insert")
        def _after_insert(mapper, connection, target):
            if not cls._enabled:
                return
            new_vals = cls._get_values(target)
            cls._write_log(connection, "created", target, new_values=new_vals)

        @sa_event.listens_for(model, "after_update")
        def _after_update(mapper, connection, target):
            if not cls._enabled:
                return
            insp = inspect(target)
            old_vals = {}
            new_vals = {}
            for attr in insp.attrs:
                hist = attr.history
                if hist.has_changes():
                    key = attr.key
                    if cls._should_track(target, key):
                        old_vals[key] = hist.deleted[0] if hist.deleted else None
                        new_vals[key] = hist.added[0] if hist.added else None
            if old_vals:
                cls._write_log(
                    connection,
                    "updated",
                    target,
                    old_values=old_vals,
                    new_values=new_vals,
                )

        @sa_event.listens_for(model, "after_delete")
        def _after_delete(mapper, connection, target):
            if not cls._enabled:
                return
            old_vals = cls._get_values(target)
            cls._write_log(connection, "deleted", target, old_values=old_vals)

    @classmethod
    def _should_track(cls, target: Any, field: str) -> bool:
        """Check if field should be tracked."""
        exclude = getattr(target, "__audit_exclude__", [])
        if field in exclude:
            return False
        fields = getattr(target, "__audit_fields__", None)
        if fields is not None:
            return field in fields
        return True

    @classmethod
    def _get_values(cls, target: Any) -> dict:
        """Get trackable column values from model instance."""
        result = {}
        for col in target.__table__.columns:
            if cls._should_track(target, col.name):
                val = getattr(target, col.name, None)
                if isinstance(val, datetime):
                    val = val.isoformat()
                result[col.name] = val
        return result

    @classmethod
    def _write_log(
        cls, connection, action: str, target: Any, old_values: dict | None = None, new_values: dict | None = None
    ) -> None:
        """Write audit log entry synchronously (within event)."""
        pk = getattr(target, "id", "?")
        connection.execute(
            AuditLog.__table__.insert().values(  # ty:ignore[unresolved-attribute]
                user_id=_context.user_id,
                action=action,
                model_type=type(target).__name__,
                model_id=str(pk),
                old_values=json.dumps(old_values, default=str) if old_values else None,
                new_values=json.dumps(new_values, default=str) if new_values else None,
                ip_address=_context.ip_address,
                user_agent=_context.user_agent,
                created_at=datetime.now(timezone.utc),
            )
        )
