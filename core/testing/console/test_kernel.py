import pytest

from core.console.kernel import ConsoleKernel
from core.console.middleware import CommandMiddleware

from .conftest import ArgCommand, HiddenTestCommand, SimpleCommand


class TestConsoleKernel:
    def test_register(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        assert k.has("simple")

    def test_register_many(self):
        k = ConsoleKernel()
        k.register_many(SimpleCommand, ArgCommand)
        assert k.has("simple")
        assert k.has("greet")

    def test_find(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        assert k.find("simple") is SimpleCommand
        assert k.find("nonexistent") is None

    def test_all(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        k.register(ArgCommand)
        all_cmds = k.all()
        assert len(all_cmds) == 2

    def test_grouped(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        k.register(HiddenTestCommand)
        groups = k.grouped()
        assert "" in groups
        assert "debug" in groups

    @pytest.mark.asyncio
    async def test_bootstrap(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        await k.bootstrap()
        assert k._bootstrapped is True

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(self):
        k = ConsoleKernel()
        await k.bootstrap()
        await k.bootstrap()  # should not fail

    def test_use_middleware(self):
        k = ConsoleKernel()

        class DummyMW(CommandMiddleware):
            async def handle(self, command, next_handler):
                return await next_handler(command)

        mw = DummyMW()
        k.use(mw)
        assert len(k.global_middleware) == 1

    def test_add_path(self):
        k = ConsoleKernel()
        k.add_path("/some/path", "some.module")
        assert len(k._command_paths) == 1

    def test_events(self):
        k = ConsoleKernel()
        assert k.events is not None

    def test_repr(self):
        k = ConsoleKernel()
        k.register(SimpleCommand)
        assert "1" in repr(k)
