from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins

logger = logging.getLogger(__name__)


@dataclass
class DeviceSession:
    """Represents a user login session on a device."""

    id: str
    user_id: str
    ip_address: str | None = None
    user_agent: str | None = None
    device_name: str | None = None
    last_active_at: float = 0.0
    created_at: float = 0.0
    is_current: bool = False

    @property
    def last_active_ago(self) -> str:
        """Human-readable last active time."""
        diff = time.time() - self.last_active_at
        if diff < 60:
            return "just now"
        if diff < 3600:
            return f"{int(diff / 60)} minutes ago"
        if diff < 86400:
            return f"{int(diff / 3600)} hours ago"
        return f"{int(diff / 86400)} days ago"


class SessionManager:
    """
    Multi-device session management.

    Usage:
        sm = SessionManager()

        # Create session on login:
        session = await sm.create("user_123", request)

        # List all sessions:
        sessions = await sm.list("user_123")

        # Activity:
        await sm.touch(session_id)

        # Revoke specific device:
        await sm.revoke(session_id)

        # Revoke all except current:
        await sm.revoke_others("user_123", current_session_id)

        # Revoke all:
        await sm.revoke_all("user_123")
    """

    def __init__(self, ttl: int = 86400 * 30) -> None:
        self._ttl = ttl
        self._sessions: dict[str, DeviceSession] = {}

    async def create(self, user_id: str, request: Any | None = None, device_name: str | None = None) -> DeviceSession:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        now = time.time()

        ip = None
        ua = None
        if request:
            ip = getattr(request, "client", {})
            ip = ip.host if hasattr(ip, "host") else str(ip) if ip else None

            headers = getattr(request, "headers", {})
            ua = headers.get("user-agent") or headers.get("User-Agent")

        session = DeviceSession(
            id=session_id,
            user_id=str(user_id),
            ip_address=ip,  # ty:ignore[invalid-argument-type]
            user_agent=ua,
            device_name=device_name or self._detect_device(ua),
            last_active_at=now,
            created_at=now,
        )

        self._sessions[session_id] = session
        logger.info("Session created for user %s from %s", user_id, ip)
        return session

    async def get(self, session_id: str) -> DeviceSession | None:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        if session and self._is_expired(session):
            del self._sessions[session_id]
            return None
        return session

    async def touch(self, session_id: str) -> None:
        """Update last active time."""
        session = self._sessions.get(session_id)
        if session:
            session.last_active_at = time.time()

    async def list(self, user_id: str, current_session_id: str | None = None) -> builtins.list[DeviceSession]:
        """List all active sessions for a user."""
        sessions = []
        expired = []

        for sid, session in self._sessions.items():
            if session.user_id != str(user_id):
                continue
            if self._is_expired(session):
                expired.append(sid)
                continue
            session.is_current = sid == current_session_id
            sessions.append(session)

        # Cleanup expired
        for sid in expired:
            del self._sessions[sid]

        # Sort by last active
        sessions.sort(key=lambda s: s.last_active_at, reverse=True)
        return sessions

    async def revoke(self, session_id: str) -> bool:
        """Revoke (delete) a specific session."""
        session = self._sessions.pop(session_id, None)
        if session:
            logger.info("Session revoked: %s (user: %s)", session_id, session.user_id)
            return True
        return False

    async def revoke_others(self, user_id: str, current_session_id: str) -> int:
        """Revoke all sessions except current."""
        to_remove = [
            sid for sid, s in self._sessions.items() if s.user_id == str(user_id) and sid != current_session_id
        ]
        for sid in to_remove:
            del self._sessions[sid]
        logger.info("Revoked %d other sessions for user %s", len(to_remove), user_id)
        return len(to_remove)

    async def revoke_all(self, user_id: str) -> int:
        """Revoke all sessions for user."""
        to_remove = [sid for sid, s in self._sessions.items() if s.user_id == str(user_id)]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    async def active_count(self, user_id: str) -> int:
        """Count active sessions."""
        return sum(1 for s in self._sessions.values() if s.user_id == str(user_id) and not self._is_expired(s))

    def _is_expired(self, session: DeviceSession) -> bool:
        return time.time() - session.last_active_at > self._ttl

    def _detect_device(self, user_agent: str | None) -> str:
        """Simple device detection from user-agent."""
        if not user_agent:
            return "Unknown"
        ua = user_agent.lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            return "Mobile"
        if "tablet" in ua or "ipad" in ua:
            return "Tablet"
        if "bot" in ua or "spider" in ua or "crawl" in ua:
            return "Bot"
        return "Desktop"

    def __repr__(self) -> str:
        return f"<SessionManager sessions={len(self._sessions)} ttl={self._ttl}s>"
