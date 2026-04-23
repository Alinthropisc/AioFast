from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Authenticatable:
    """
    Mixin for User model — authentication fields.

    Usage:
        class User(Authenticatable, BaseModel):
            __tablename__ = "users"
            name: Mapped[str] = mapped_column(String(100))
    """

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None

    def mark_verified(self) -> None:
        self.email_verified_at = datetime.now(timezone.utc)

    def record_login(self, ip: str | None = None) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        self.last_login_ip = ip


class HasMFA:
    """
    Mixin — MFA fields.

    Usage:
        class User(HasMFA, Authenticatable, BaseModel):
            ...
    """

    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_backup_codes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def has_mfa(self) -> bool:
        return self.mfa_enabled and bool(self.mfa_secret)


class HasApiTokens:
    """
    Mixin — API token fields.

    Usage:
        class User(HasApiTokens, Authenticatable, BaseModel):
            ...
    """

    api_token: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    api_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def has_valid_token(self) -> bool:
        if not self.api_token:
            return False
        if self.api_token_expires_at:
            return datetime.now(timezone.utc) < self.api_token_expires_at
        return True


class HasRoles:
    """
    Mixin — simple role field.

    For complex RBAC use CasbinGuard.

    Usage:
        class User(HasRoles, Authenticatable, BaseModel):
            ...

        user.role = "admin"
        if user.is_role("admin"):
            ...
    """

    role: Mapped[str] = mapped_column(String(50), default="user")

    def is_role(self, role: str) -> bool:
        return self.role == role

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "super_admin")

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"
