from typing import Any

from core.console.command import Command
from core.console.decorators import (
    environments,
    hidden,
    isolated,
    log_execution,
    production_guard,
    retry,
    timeout,
    with_lock,
)


class TestIsolated:
    def test_sets_isolated(self):
        @isolated
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd.isolated is True


class TestHidden:
    def test_sets_hidden(self):
        @hidden
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd.hidden is True


class TestWithLock:
    def test_sets_lock(self):
        @with_lock("my:key", timeout=30)
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd.lock is True
        assert Cmd._lock_key == "my:key"  # ty:ignore[unresolved-attribute]
        assert Cmd._lock_timeout == 30  # ty:ignore[unresolved-attribute]


class TestRetry:
    def test_sets_retry(self):
        @retry(times=5, delay=2.0)
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd._retry_times == 5  # ty:ignore[unresolved-attribute]
        assert Cmd._retry_delay == 2.0  # ty:ignore[unresolved-attribute]
        assert Cmd._retry_exceptions == (Exception,)  # ty:ignore[unresolved-attribute]

    def test_custom_exceptions(self):
        @retry(times=3, exceptions=(ValueError, IOError))
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd._retry_exceptions == (ValueError, IOError)  # ty:ignore[unresolved-attribute]


class TestTimeout:
    def test_sets_timeout(self):
        @timeout(60)
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd._timeout_seconds == 60  # ty:ignore[unresolved-attribute]


class TestEnvironments:
    def test_sets_environments(self):
        @environments("local", "testing")
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd._allowed_environments == ["local", "testing"]  # ty:ignore[unresolved-attribute]


class TestLogExecution:
    def test_sets_log_flag(self):
        @log_execution
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd._log_execution is True  # ty:ignore[unresolved-attribute]


class TestProductionGuard:
    def test_sets_production_guard(self):
        @production_guard
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd.production_guard is True  # ty:ignore[unresolved-attribute]


class TestCombinedDecorators:
    def test_multiple_decorators(self):
        @isolated
        @hidden
        @retry(times=2)
        @timeout(30)
        class Cmd(Command):
            name = "test"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        assert Cmd.isolated is True
        assert Cmd.hidden is True
        assert Cmd._retry_times == 2  # ty:ignore[unresolved-attribute]
        assert Cmd._timeout_seconds == 30  # ty:ignore[unresolved-attribute]
