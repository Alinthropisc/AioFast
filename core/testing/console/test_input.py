from core.console.input import ArgvInput, Verbosity


class TestArgvInput:
    def test_empty_input(self):
        inp = ArgvInput([])
        assert inp.command == ""
        assert inp.arguments == []
        assert inp.options == {}

    def test_command_only(self):
        inp = ArgvInput(["migrate"])
        assert inp.command == "migrate"
        assert inp.arguments == []

    def test_command_with_args(self):
        inp = ArgvInput(["greet", "World", "extra"])
        assert inp.command == "greet"
        assert inp.arguments == ["World", "extra"]

    def test_long_option_flag(self):
        inp = ArgvInput(["test", "--force"])
        assert inp.options["force"] is True

    def test_long_option_with_value(self):
        inp = ArgvInput(["test", "--name=John"])
        assert inp.options["name"] == "John"

    def test_long_option_duplicate_becomes_list(self):
        inp = ArgvInput(["test", "--tag=a", "--tag=b"])
        assert inp.options["tag"] == ["a", "b"]

    def test_short_option_flag(self):
        inp = ArgvInput(["test", "-f"])
        assert inp.options["f"] is True

    def test_short_option_with_value(self):
        inp = ArgvInput(["test", "-n", "John"])
        assert inp.options["n"] == "John"

    def test_combined_short_flags(self):
        inp = ArgvInput(["test", "-abc"])
        assert inp.options["a"] is True
        assert inp.options["b"] is True
        assert inp.options["c"] is True

    def test_verbosity_default(self):
        inp = ArgvInput(["test"])
        assert inp.verbosity == Verbosity.NORMAL

    def test_verbosity_v(self):
        inp = ArgvInput(["test", "-v"])
        assert inp.verbosity == Verbosity.VERBOSE

    def test_verbosity_vv(self):
        inp = ArgvInput(["test", "-vv"])
        assert inp.verbosity == Verbosity.VERY_VERBOSE

    def test_verbosity_vvv(self):
        inp = ArgvInput(["test", "-vvv"])
        assert inp.verbosity == Verbosity.DEBUG

    def test_quiet(self):
        inp = ArgvInput(["test", "--quiet"])
        assert inp.verbosity == Verbosity.QUIET

    def test_no_interaction(self):
        inp = ArgvInput(["test", "--no-interaction"])
        assert inp.is_interactive is False

    def test_interactive_default(self):
        inp = ArgvInput(["test"])
        assert inp.is_interactive is True

    def test_format_option(self):
        inp = ArgvInput(["test", "--format=json"])
        assert inp.format == "json"

    def test_format_default(self):
        inp = ArgvInput(["test"])
        assert inp.format == "table"

    def test_format_invalid_falls_back(self):
        inp = ArgvInput(["test", "--format=invalid"])
        assert inp.format == "table"

    def test_double_dash_separator(self):
        inp = ArgvInput(["test", "--", "arg1", "--not-option"])
        assert inp.arguments == ["arg1", "--not-option"]

    def test_mixed_args_and_options(self):
        inp = ArgvInput(["deploy", "production", "--force", "--workers=4"])
        assert inp.command == "deploy"
        assert inp.arguments == ["production"]
        assert inp.options["force"] is True
        assert inp.options["workers"] == "4"

    def test_has_option(self):
        inp = ArgvInput(["test", "--force"])
        assert inp.has_option("force") is True
        assert inp.has_option("verbose") is False

    def test_get_option(self):
        inp = ArgvInput(["test", "--level=5"])
        assert inp.get_option("level") == "5"
        assert inp.get_option("missing", "default") == "default"

    def test_repr(self):
        inp = ArgvInput(["test", "arg", "--flag"])
        r = repr(inp)
        assert "test" in r
        assert "arg" in r

    def test_option_starts_with_dash_no_command(self):
        inp = ArgvInput(["--help"])
        assert inp.command == ""
        assert inp.options.get("help") is True
