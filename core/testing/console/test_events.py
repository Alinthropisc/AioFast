import pytest

from core.console.events import (
    CommandFailed,
    CommandFinished,
    CommandSkipped,
    CommandStarting,
    EventDispatcher,
)

from .conftest import SimpleCommand


class TestEventDispatcher:
    @pytest.mark.asyncio
    async def test_listen_and_dispatch(self):
        d = EventDispatcher()
        received = []
        d.listen(CommandStarting, lambda e: received.append(e))
        event = CommandStarting(command=SimpleCommand())
        await d.dispatch(event)
        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_multiple_listeners(self):
        d = EventDispatcher()
        count = []
        d.listen(CommandFinished, lambda e: count.append(1))
        d.listen(CommandFinished, lambda e: count.append(2))
        await d.dispatch(CommandFinished(command=SimpleCommand(), exit_code=0))
        assert count == [1, 2]

    @pytest.mark.asyncio
    async def test_on_any(self):
        d = EventDispatcher()
        events = []
        d.on_any(lambda e: events.append(type(e).__name__))
        await d.dispatch(CommandStarting(command=SimpleCommand()))
        await d.dispatch(CommandFinished(command=SimpleCommand(), exit_code=0))
        assert events == ["CommandStarting", "CommandFinished"]

    @pytest.mark.asyncio
    async def test_async_callback(self):
        d = EventDispatcher()
        received = []

        async def handler(e):
            received.append(e.exit_code)

        d.listen(CommandFinished, handler)
        await d.dispatch(CommandFinished(command=SimpleCommand(), exit_code=42))
        assert received == [42]

    @pytest.mark.asyncio
    async def test_forget(self):
        d = EventDispatcher()
        d.listen(CommandStarting, lambda e: None)
        d.forget(CommandStarting)
        assert CommandStarting not in d._listeners

    @pytest.mark.asyncio
    async def test_flush(self):
        d = EventDispatcher()
        d.listen(CommandStarting, lambda e: None)
        d.on_any(lambda e: None)
        d.flush()
        assert len(d._listeners) == 0
        assert len(d._wildcard) == 0

    @pytest.mark.asyncio
    async def test_listener_error_does_not_crash(self):
        d = EventDispatcher()
        d.listen(CommandStarting, lambda e: 1 / 0)
        # Should not raise
        await d.dispatch(CommandStarting(command=SimpleCommand()))

    @pytest.mark.asyncio
    async def test_no_listeners(self):
        d = EventDispatcher()
        # Should not raise
        await d.dispatch(CommandStarting(command=SimpleCommand()))

    def test_repr(self):
        d = EventDispatcher()
        d.listen(CommandStarting, lambda e: None)
        assert "1" in repr(d)


class TestEventDataclasses:
    def test_command_starting(self):
        cmd = SimpleCommand()
        e = CommandStarting(command=cmd)
        assert e.command is cmd
        assert e.input is None

    def test_command_finished(self):
        e = CommandFinished(command=SimpleCommand(), exit_code=0, elapsed=1.5)
        assert e.exit_code == 0
        assert e.elapsed == 1.5

    def test_command_failed(self):
        err = RuntimeError("fail")
        e = CommandFailed(command=SimpleCommand(), exception=err)
        assert e.exception is err
        assert e.exit_code == 1

    def test_command_skipped(self):
        e = CommandSkipped(command_name="test", reason="guard")
        assert e.command_name == "test"
        assert e.reason == "guard"
