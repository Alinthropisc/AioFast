import inspect
from typing import Any

import pytest

from core.console.command import Command
from core.console.console_application import ConsoleApplication
from core.console.descriptors import Argument, Min, Option, Required
from core.console.kernel import ConsoleKernel
from core.console.output import ConsoleOutput

# ── Test Commands ─────────────────────────────────────────


class SimpleCommand(Command):
    name = "simple"
    description = "Simple test command"

    async def handle(self, **kwargs: Any) -> int:
        self.info("simple executed")
        return self.SUCCESS


class ArgCommand(Command):
    name = "greet"
    description = "Greet someone"
    aliases = ["hello", "hi"]

    username = Argument(type=str, description="Username", rules=[Required()])
    shout = Option("--shout", "-s", type=bool, description="Shout")
    times = Option("--times", "-t", type=int, default=1, description="Repeat")

    async def handle(self, **kwargs: Any) -> int:
        msg = f"Hello, {self.username}!"
        if self.shout:
            msg = msg.upper()
        for _ in range(self.times):  # ty:ignore[invalid-argument-type]
            self.info(msg)
        return self.SUCCESS


class FailCommand(Command):
    name = "fail"
    description = "Always fails"

    async def handle(self, **kwargs: Any) -> int:
        self.error("Failed!")
        return self.FAILURE


class LifecycleCommand(Command):
    name = "lifecycle"
    description = "Tracks lifecycle"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def before(self) -> bool:
        self.calls.append("before")
        return True

    async def handle(self, **kwargs: Any) -> int:
        self.calls.append("handle")
        return self.SUCCESS

    async def after(self, exit_code: int) -> None:
        self.calls.append(f"after:{exit_code}")

    async def on_success(self) -> None:
        self.calls.append("on_success")

    async def on_failure(self, exit_code: int) -> None:
        self.calls.append(f"on_failure:{exit_code}")


class AbortCommand(Command):
    name = "abort"
    description = "Aborts in before()"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def before(self) -> bool:
        self.calls.append("before")
        return False

    async def handle(self, **kwargs: Any) -> int:
        self.calls.append("handle")
        return self.SUCCESS

    async def after(self, exit_code: int) -> None:
        self.calls.append(f"after:{exit_code}")


class ErrorCommand(Command):
    name = "error"
    description = "Throws error"

    async def handle(self, **kwargs: Any) -> int:
        raise RuntimeError("Test error")

    async def on_error(self, error: Exception) -> int:
        return self.FAILURE


class ErrorNoRecoverCommand(Command):
    name = "error:norecov"
    description = "Error without recovery"

    async def handle(self, **kwargs: Any) -> int:
        raise RuntimeError("Unrecoverable")


class IsolatedTestCommand(Command):
    name = "iso"
    description = "Isolated"
    isolated = True

    async def handle(self, **kwargs: Any) -> int:
        self.success("isolated ok")
        return self.SUCCESS


class HiddenTestCommand(Command):
    name = "debug:internal"
    description = "Hidden"
    hidden = True

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


class SigCommand(Command):
    name = "sig"
    signature = "{name} {--loud|-l} {--count=3}"
    description = "Signature test"

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


class MultiArgCommand(Command):
    name = "multi"
    description = "Multiple args"

    first = Argument(type=str, description="First")
    second = Argument(type=int, default=10, description="Second")
    flag = Option("--flag", "-f", type=bool)
    level = Option("--level", "-l", type=int, default=5)

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


class ValidatedCommand(Command):
    name = "validated"
    description = "With validation"

    age = Argument(type=int, description="Age", rules=[Required(), Min(18)])

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


class ProductionCommand(Command):
    name = "danger"
    description = "Dangerous"
    production_guard = True

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


class LockCommand(Command):
    name = "locked"
    description = "Locked command"
    lock = True

    async def handle(self, **kwargs: Any) -> int:
        return self.SUCCESS


# ── Mock Container ────────────────────────────────────────


class MockContainer:
    def __init__(self) -> None:
        self._bindings: dict = {}

    def bind(self, abstract: Any, instance: Any) -> None:
        self._bindings[abstract] = instance

    async def make(self, abstract: Any, *args: Any, **kwargs: Any) -> Any:
        if abstract in self._bindings:
            obj = self._bindings[abstract]
            return obj() if inspect.isclass(obj) else obj
        if inspect.isclass(abstract):
            return abstract()
        raise Exception(f"Not found: {abstract}")

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


# ── Fixtures ──────────────────────────────────────────────

ALL_COMMANDS = [
    SimpleCommand,
    ArgCommand,
    FailCommand,
    LifecycleCommand,
    AbortCommand,
    ErrorCommand,
    ErrorNoRecoverCommand,
    IsolatedTestCommand,
    HiddenTestCommand,
    SigCommand,
    MultiArgCommand,
    ValidatedCommand,
    ProductionCommand,
    LockCommand,
]


@pytest.fixture
def output():
    o = ConsoleOutput(quiet=True)
    o.start_buffering()
    return o


@pytest.fixture
def kernel():
    k = ConsoleKernel()
    for cmd in ALL_COMMANDS:
        k.register(cmd)
    return k


@pytest.fixture
def app(kernel, tmp_path):
    return ConsoleApplication(
        name="TestApp", version="0.1.0", kernel=kernel, binary="testcraft", locks_dir=str(tmp_path / "locks")
    )


@pytest.fixture
def app_with_container(kernel, tmp_path):
    container = MockContainer()
    return ConsoleApplication(
        name="TestApp",
        version="0.1.0",
        kernel=kernel,
        container=container,
        binary="testcraft",
        locks_dir=str(tmp_path / "locks"),
    )


@pytest.fixture
def mock_container():
    return MockContainer()
