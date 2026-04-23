import pytest

from core.console.command import Command
from core.console.input import ArgvInput
from core.console.middleware import CommandMiddleware, MiddlewarePipeline
from core.console.output import ConsoleOutput

from .conftest import SimpleCommand


class PassthroughMiddleware(CommandMiddleware):
    async def handle(self, command, next_handler):
        return await next_handler(command)


class ModifyMiddleware(CommandMiddleware):
    def __init__(self):
        self.called = False

    async def handle(self, command, next_handler):
        self.called = True
        return await next_handler(command)


class AbortMiddleware(CommandMiddleware):
    async def handle(self, command, next_handler):
        return Command.FAILURE


class OrderTracker(CommandMiddleware):
    def __init__(self, name: str, log: list):
        self._name = name
        self._log = log

    async def handle(self, command, next_handler):
        self._log.append(f"before:{self._name}")
        result = await next_handler(command)
        self._log.append(f"after:{self._name}")
        return result


def _make_command():
    cmd = SimpleCommand()
    inp = ArgvInput(["simple"])
    out = ConsoleOutput(quiet=True)
    out.start_buffering()
    cmd.setup(inp, out)
    return cmd


class TestMiddlewarePipeline:
    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        cmd = _make_command()
        pipeline = MiddlewarePipeline()

        async def handler(c):
            return await c.handle()

        result = await pipeline.run(cmd, handler)
        assert result == Command.SUCCESS

    @pytest.mark.asyncio
    async def test_passthrough(self):
        cmd = _make_command()
        pipeline = MiddlewarePipeline([PassthroughMiddleware()])

        async def handler(c):
            return await c.handle()

        result = await pipeline.run(cmd, handler)
        assert result == Command.SUCCESS

    @pytest.mark.asyncio
    async def test_middleware_called(self):
        cmd = _make_command()
        mw = ModifyMiddleware()
        pipeline = MiddlewarePipeline([mw])

        async def handler(c):
            return await c.handle()

        await pipeline.run(cmd, handler)
        assert mw.called is True

    @pytest.mark.asyncio
    async def test_abort_middleware(self):
        cmd = _make_command()
        pipeline = MiddlewarePipeline([AbortMiddleware()])

        async def handler(c):
            return await c.handle()

        result = await pipeline.run(cmd, handler)
        assert result == Command.FAILURE

    @pytest.mark.asyncio
    async def test_middleware_order(self):
        cmd = _make_command()
        log = []
        pipeline = MiddlewarePipeline(
            [
                OrderTracker("first", log),
                OrderTracker("second", log),
            ]
        )

        async def handler(c):
            log.append("handle")
            return Command.SUCCESS

        await pipeline.run(cmd, handler)
        assert log == [
            "before:first",
            "before:second",
            "handle",
            "after:second",
            "after:first",
        ]

    @pytest.mark.asyncio
    async def test_pipe_method(self):
        cmd = _make_command()
        pipeline = MiddlewarePipeline()
        mw = ModifyMiddleware()
        pipeline.pipe(mw)

        async def handler(c):
            return await c.handle()

        await pipeline.run(cmd, handler)
        assert mw.called is True
