from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class AuthEvent:
    """Base auth event."""

    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoginEvent(AuthEvent):
    """User successfully logged in."""

    guard: str = "default"


@dataclass
class LogoutEvent(AuthEvent):
    """User logged out."""

    pass


@dataclass
class FailedLoginEvent(AuthEvent):
    """Login attempt failed."""

    email: str = ""
    reason: str = ""


@dataclass
class LockoutEvent(AuthEvent):
    """User locked out due to too many attempts."""

    email: str = ""
    locked_until: datetime | None = None


@dataclass
class PasswordResetEvent(AuthEvent):
    """Password was reset."""

    pass


@dataclass
class TokenIssuedEvent(AuthEvent):
    """Token was issued."""

    token_type: str = "access"


@dataclass
class TokenRevokedEvent(AuthEvent):
    """Token was revoked."""

    token_id: str | None = None


@dataclass
class MFAEnabledEvent(AuthEvent):
    """MFA was enabled."""

    pass


@dataclass
class MFAVerifiedEvent(AuthEvent):
    """MFA code verified during login."""

    method: str = "totp"


class AuthEventDispatcher:
    """
    Dispatch and listen to auth events.

    Usage:
        dispatcher = AuthEventDispatcher()

        # Listen:
        dispatcher.on(LoginEvent, lambda e: log_login(e))
        dispatcher.on(FailedLoginEvent, lambda e: alert_admin(e))
        dispatcher.on(LockoutEvent, lambda e: send_email(e))

        # Dispatch:
        await dispatcher.dispatch(LoginEvent(user_id="123", guard="jwt"))
        await dispatcher.dispatch(FailedLoginEvent(email="bad@test.com", reason="wrong password"))
    """

    def __init__(self) -> None:
        self._listeners: dict[type, list[Callable]] = {}

    def on(self, event_type: type, callback: Callable) -> AuthEventDispatcher:
        """Register event listener."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        return self

    async def dispatch(self, event: AuthEvent) -> None:
        """Dispatch event to all listeners."""
        import asyncio

        listeners = self._listeners.get(type(event), [])
        # Also trigger listeners for base AuthEvent
        listeners += self._listeners.get(AuthEvent, [])

        for listener in listeners:
            try:
                result = listener(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("Auth event listener error: %s", e)

    def clear(self) -> None:
        self._listeners.clear()

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values())
        return f"<AuthEventDispatcher listeners={total}>"
