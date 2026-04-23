from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class LoginThrottle:
    """
    Login rate limiting — protect against brute force.

    Usage:
        throttle = LoginThrottle(max_attempts=5, lockout_seconds=300)

        # Before login attempt:
        if throttle.is_locked(key="user@example.com"):
            remaining = throttle.seconds_remaining("user@example.com")
            raise TooManyAttemptsError(f"Try again in {remaining}s")

        # On failed attempt:
        throttle.hit("user@example.com")

        # On success:
        throttle.clear("user@example.com")

        # With IP:
        key = f"{email}|{ip_address}"
        throttle.hit(key)
    """

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 300, decay_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.decay_seconds = decay_seconds
        self._attempts: dict[str, list] = {}  # key → [timestamp, ...]
        self._lockouts: dict[str, float] = {}  # key → locked_until

    def hit(self, key: str) -> int:
        """Record a failed attempt. Returns current count."""
        now = time.time()
        self._cleanup(key, now)

        if key not in self._attempts:
            self._attempts[key] = []

        self._attempts[key].append(now)
        count = len(self._attempts[key])

        if count >= self.max_attempts:
            self._lockouts[key] = now + self.lockout_seconds
            logger.warning(
                "🔒 Login throttle: %s locked for %ds (%d attempts)",
                key,
                self.lockout_seconds,
                count,
            )

        return count

    def is_locked(self, key: str) -> bool:
        """Check if key is currently locked out."""
        locked_until = self._lockouts.get(key, 0)
        if time.time() < locked_until:
            return True
        # Clear expired lockout
        self._lockouts.pop(key, None)
        return False

    def seconds_remaining(self, key: str) -> int:
        """Seconds remaining on lockout."""
        locked_until = self._lockouts.get(key, 0)
        remaining = locked_until - time.time()
        return max(0, int(remaining))

    def attempts(self, key: str) -> int:
        """Current attempt count."""
        self._cleanup(key, time.time())
        return len(self._attempts.get(key, []))

    def remaining_attempts(self, key: str) -> int:
        """Remaining attempts before lockout."""
        return max(0, self.max_attempts - self.attempts(key))

    def clear(self, key: str) -> None:
        """Clear attempts and lockout (on successful login)."""
        self._attempts.pop(key, None)
        self._lockouts.pop(key, None)

    def _cleanup(self, key: str, now: float) -> None:
        """Remove attempts older than decay window."""
        if key in self._attempts:
            cutoff = now - self.decay_seconds
            self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

    async def cleanup_all(self) -> int:
        """Cleanup all expired data."""
        now = time.time()
        removed = 0

        # Clean attempts
        for key in list(self._attempts.keys()):
            self._cleanup(key, now)
            if not self._attempts[key]:
                del self._attempts[key]
                removed += 1

        # Clean lockouts
        for key in list(self._lockouts.keys()):
            if now > self._lockouts[key]:
                del self._lockouts[key]
                removed += 1

        return removed

    def __repr__(self) -> str:
        return f"<LoginThrottle max={self.max_attempts} lockout={self.lockout_seconds}s tracked={len(self._attempts)}>"
