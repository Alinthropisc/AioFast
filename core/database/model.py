from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Model(DeclarativeBase):
    """
    Base model for all database models.

    Usage:
        class User(Model):
            __tablename__ = "users"

            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str]
            email: Mapped[str] = mapped_column(unique=True)
    """

    pass


class TimestampMixin:
    """
    Adds created_at and updated_at columns.

    Usage:
        class User(TimestampMixin, Model):
            __tablename__ = "users"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str]
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=func.now(), server_onupdate=func.now()
    )


class SoftDeleteMixin:
    """
    Soft delete — mark as deleted instead of removing.

    Usage:
        class User(SoftDeleteMixin, TimestampMixin, Model):
            __tablename__ = "users"
            id: Mapped[int] = mapped_column(primary_key=True)

        # Soft delete:
        user.deleted_at = datetime.now(timezone.utc)

        # Query only active:
        select(User).where(User.deleted_at.is_(None))
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.deleted_at = None


class IDMixin:
    """Auto-increment integer primary key."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class BaseModel(IDMixin, TimestampMixin, Model):
    """
    Full-featured base model with id + timestamps.

    Usage:
        class User(BaseModel):
            __tablename__ = "users"
            name: Mapped[str]
            email: Mapped[str] = mapped_column(unique=True)
    """

    __abstract__ = True

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def update(self, **kwargs: Any) -> None:
        """Update model attributes from kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        pk = getattr(self, "id", "?")
        return f"<{self.__class__.__name__} id={pk}>"
