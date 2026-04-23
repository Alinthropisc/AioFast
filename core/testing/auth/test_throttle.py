from __future__ import annotations

from core.auth.throttle import LoginThrottle


class TestLoginThrottle:
    def test_no_lockout_initially(self):
        t = LoginThrottle(max_attempts=3)
        assert not t.is_locked("user@test.com")
        assert t.remaining_attempts("user@test.com") == 3

    def test_hit_and_lockout(self):
        t = LoginThrottle(max_attempts=3, lockout_seconds=60)
        t.hit("user@test.com")
        t.hit("user@test.com")
        assert not t.is_locked("user@test.com")

        t.hit("user@test.com")
        assert t.is_locked("user@test.com")
        assert t.seconds_remaining("user@test.com") > 0

    def test_clear(self):
        t = LoginThrottle(max_attempts=2)
        t.hit("user@test.com")
        t.hit("user@test.com")
        assert t.is_locked("user@test.com")

        t.clear("user@test.com")
        assert not t.is_locked("user@test.com")
        assert t.attempts("user@test.com") == 0

    def test_remaining(self):
        t = LoginThrottle(max_attempts=5)
        t.hit("x")
        t.hit("x")
        assert t.remaining_attempts("x") == 3
