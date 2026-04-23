import pytest

from core.console.command import Command
from core.console.input import ArgvInput
from core.console.output import ConsoleOutput

from .conftest import (
    ArgCommand,
    FailCommand,
    HiddenTestCommand,
    MultiArgCommand,
    SigCommand,
    SimpleCommand,
    ValidatedCommand,
)


class TestCommandDescriptorCollection:
    def test_collects_arguments(self):
        assert len(ArgCommand._arg_defs) == 1
        assert ArgCommand._arg_defs[0].attr_name == "username"

    def test_collects_options(self):
        assert len(ArgCommand._opt_defs) == 2
        names = [o.attr_name for o in ArgCommand._opt_defs]
        assert "shout" in names
        assert "times" in names

    def test_multi_arg(self):
        assert len(MultiArgCommand._arg_defs) == 2
        assert len(MultiArgCommand._opt_defs) == 2

    def test_signature_parsed(self):
        assert len(SigCommand._arg_defs) == 1
        assert len(SigCommand._opt_defs) == 2
        assert SigCommand._arg_defs[0].attr_name == "name"

    def test_no_descriptors(self):
        assert len(SimpleCommand._arg_defs) == 0
        assert len(SimpleCommand._opt_defs) == 0


class TestCommandSetup:
    def _setup(self, cmd_cls, argv):
        cmd = cmd_cls() if cmd_cls.__init__ is not Command.__init__ else cmd_cls()
        inp = ArgvInput(argv)
        out = ConsoleOutput(quiet=True)
        out.start_buffering()
        cmd.setup(inp, out)
        return cmd

    def test_bind_positional_argument(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice"])
        assert cmd.username == "Alice"

    def test_bind_option_flag(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice", "--shout"])
        assert cmd.shout is True

    def test_bind_option_with_value(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice", "--times=3"])
        assert cmd.times == 3

    def test_bind_short_option(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice", "-s"])
        assert cmd.shout is True

    def test_bind_default_option(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice"])
        assert cmd.times == 1
        assert cmd.shout is False

    def test_bind_multiple_args(self):
        cmd = self._setup(MultiArgCommand, ["multi", "hello", "42"])
        assert cmd.first == "hello"
        assert cmd.second == 42

    def test_bind_default_arg(self):
        cmd = self._setup(MultiArgCommand, ["multi", "hello"])
        assert cmd.first == "hello"
        assert cmd.second == 10

    def test_missing_required_arg_is_none(self):
        cmd = self._setup(ArgCommand, ["greet"])
        assert cmd.username is None


class TestCommandValidation:
    def _setup(self, cmd_cls, argv):
        cmd = cmd_cls() if cmd_cls.__init__ is not Command.__init__ else cmd_cls()
        inp = ArgvInput(argv)
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        return cmd

    def test_valid_passes(self):
        cmd = self._setup(ArgCommand, ["greet", "Alice"])
        errors = cmd.validate()
        assert errors == []

    def test_missing_required_fails(self):
        cmd = self._setup(ArgCommand, ["greet"])
        errors = cmd.validate()
        assert len(errors) >= 1
        assert "username" in errors[0].lower()

    def test_rule_validation_fails(self):
        cmd = self._setup(ValidatedCommand, ["validated", "10"])
        errors = cmd.validate()
        assert len(errors) >= 1
        assert "at least 18" in errors[0].lower()

    def test_rule_validation_passes(self):
        cmd = self._setup(ValidatedCommand, ["validated", "25"])
        errors = cmd.validate()
        assert errors == []


class TestCommandAccessors:
    def test_argument_method(self):
        cmd = ArgCommand()
        inp = ArgvInput(["greet", "Alice"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        assert cmd.argument("username") == "Alice"
        assert cmd.argument("missing", "default") == "default"

    def test_option_method(self):
        cmd = ArgCommand()
        inp = ArgvInput(["greet", "Alice", "--times=5"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        assert cmd.option("times") == 5
        assert cmd.option("missing", "x") == "x"

    def test_all_arguments(self):
        cmd = ArgCommand()
        inp = ArgvInput(["greet", "Bob"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        args = cmd.all_arguments()
        assert "username" in args

    def test_all_options(self):
        cmd = ArgCommand()
        inp = ArgvInput(["greet", "Bob"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        opts = cmd.all_options()
        assert "shout" in opts
        assert "times" in opts


class TestCommandOutput:
    def test_output_methods(self):
        cmd = SimpleCommand()
        out = ConsoleOutput(quiet=True)
        out.start_buffering()
        inp = ArgvInput(["simple"])
        cmd.setup(inp, out)

        cmd.info("info msg")
        cmd.success("success msg")
        cmd.warn("warn msg")
        cmd.error("error msg")
        cmd.comment("comment msg")

        result = out.stop_buffering()
        assert "info msg" in result
        assert "success msg" in result
        assert "warn msg" in result
        assert "error msg" in result
        assert "comment msg" in result


class TestCommandHandle:
    @pytest.mark.asyncio
    async def test_simple_handle(self):
        cmd = SimpleCommand()
        out = ConsoleOutput(quiet=True)
        out.start_buffering()
        inp = ArgvInput(["simple"])
        cmd.setup(inp, out)
        code = await cmd.handle()
        assert code == Command.SUCCESS

    @pytest.mark.asyncio
    async def test_fail_handle(self):
        cmd = FailCommand()
        out = ConsoleOutput(quiet=True)
        out.start_buffering()
        inp = ArgvInput(["fail"])
        cmd.setup(inp, out)
        code = await cmd.handle()
        assert code == Command.FAILURE


class TestCommandHelp:
    def test_get_help_basic(self):
        cmd = SimpleCommand()
        inp = ArgvInput(["simple"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        help_text = cmd.get_help()
        assert "simple" in help_text

    def test_get_help_with_args_and_opts(self):
        cmd = ArgCommand()
        inp = ArgvInput(["greet"])
        out = ConsoleOutput(quiet=True)
        cmd.setup(inp, out)
        help_text = cmd.get_help()
        assert "username" in help_text
        assert "--shout" in help_text
        assert "--times" in help_text
        assert "Aliases" in help_text

    def test_hidden_attribute(self):
        assert HiddenTestCommand.hidden is True
        assert SimpleCommand.hidden is False


class TestCommandRepr:
    def test_repr(self):
        assert "simple" in repr(SimpleCommand())
