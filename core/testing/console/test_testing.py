import pytest

from core.console.command import Command
from core.console.testing import CommandResult, ConsoleTester

from .conftest import ArgCommand, FailCommand, SimpleCommand


class TestCommandResult:
    def test_successful(self):
        r = CommandResult(exit_code=0, output="ok", command_name="test")
        assert r.was_successful is True
        assert r.was_failure is False

    def test_failure(self):
        r = CommandResult(exit_code=1, output="err", command_name="test")
        assert r.was_successful is False
        assert r.was_failure is True

    def test_assert_successful(self):
        r = CommandResult(exit_code=0, output="ok", command_name="test")
        r.assert_successful()

    def test_assert_successful_fails(self):
        r = CommandResult(exit_code=1, output="err", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_successful()

    def test_assert_failed(self):
        r = CommandResult(exit_code=1, output="err", command_name="test")
        r.assert_failed()

    def test_assert_failed_fails(self):
        r = CommandResult(exit_code=0, output="ok", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_failed()

    def test_assert_exit_code(self):
        r = CommandResult(exit_code=2, output="", command_name="test")
        r.assert_exit_code(2)

    def test_assert_exit_code_fails(self):
        r = CommandResult(exit_code=0, output="", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_exit_code(1)

    def test_assert_output_contains(self):
        r = CommandResult(exit_code=0, output="hello world", command_name="test")
        r.assert_output_contains("world")

    def test_assert_output_contains_fails(self):
        r = CommandResult(exit_code=0, output="hello", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_output_contains("world")

    def test_assert_output_not_contains(self):
        r = CommandResult(exit_code=0, output="hello", command_name="test")
        r.assert_output_not_contains("world")

    def test_assert_output_not_contains_fails(self):
        r = CommandResult(exit_code=0, output="hello world", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_output_not_contains("world")

    def test_assert_output_empty(self):
        r = CommandResult(exit_code=0, output="", command_name="test")
        r.assert_output_empty()

    def test_assert_output_empty_fails(self):
        r = CommandResult(exit_code=0, output="content", command_name="test")
        with pytest.raises(AssertionError):
            r.assert_output_empty()

    def test_chained_assertions(self):
        r = CommandResult(exit_code=0, output="done", command_name="test")
        r.assert_successful().assert_exit_code(0).assert_output_contains("done")

    def test_repr(self):
        r = CommandResult(exit_code=0, output="", command_name="test")
        assert "OK" in repr(r)
        r2 = CommandResult(exit_code=1, output="", command_name="fail")
        assert "FAIL" in repr(r2)


class TestConsoleTester:
    @pytest.mark.asyncio
    async def test_call_command_class(self):
        tester = ConsoleTester()
        result = await tester.call(SimpleCommand)
        result.assert_successful()

    @pytest.mark.asyncio
    async def test_call_with_app(self, app):
        await app.kernel.bootstrap()
        tester = ConsoleTester(app=app)
        result = await tester.call("simple")
        result.assert_successful()

    @pytest.mark.asyncio
    async def test_call_fail_command(self):
        tester = ConsoleTester()
        result = await tester.call(FailCommand)
        result.assert_failed()

    @pytest.mark.asyncio
    async def test_call_with_arguments(self):
        tester = ConsoleTester()
        result = await tester.call(ArgCommand, arguments=["Alice"])
        result.assert_successful()

    @pytest.mark.asyncio
    async def test_call_missing_required(self):
        tester = ConsoleTester()
        result = await tester.call(ArgCommand)
        assert result.exit_code == Command.INVALID

    @pytest.mark.asyncio
    async def test_call_unknown_command(self, app):
        await app.kernel.bootstrap()
        tester = ConsoleTester(app=app)
        result = await tester.call("nonexistent")
        result.assert_failed()

    @pytest.mark.asyncio
    async def test_call_with_options(self):
        tester = ConsoleTester()
        result = await tester.call(
            ArgCommand,
            arguments=["Bob"],
            options={"shout": True, "times": 2},
        )
        result.assert_successful()

    @pytest.mark.asyncio
    async def test_call_no_app_no_class(self):
        tester = ConsoleTester()
        result = await tester.call("just_a_string")
        result.assert_failed()
