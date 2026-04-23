from core.console.descriptors.argument import MISSING
from core.console.signature_parser import SignatureParser


class TestSignatureParser:
    def test_required_argument(self):
        args, _opts = SignatureParser.parse("{name}")
        assert len(args) == 1
        assert args[0].attr_name == "name"
        assert args[0].is_required is True

    def test_optional_argument(self):
        args, _opts = SignatureParser.parse("{name?}")
        assert len(args) == 1
        assert args[0].attr_name == "name"
        assert args[0].default is None
        assert args[0].is_required is False

    def test_argument_with_default(self):
        args, _opts = SignatureParser.parse("{direction=up}")
        assert args[0].attr_name == "direction"
        assert args[0].default == "up"

    def test_argument_with_description(self):
        args, _opts = SignatureParser.parse("{name : The username}")
        assert args[0].attr_name == "name"
        assert args[0].description == "The username"

    def test_boolean_option(self):
        _args, opts = SignatureParser.parse("{--force}")
        assert len(opts) == 1
        assert opts[0].attr_name == "force"
        assert opts[0].type is bool
        assert opts[0].default is False

    def test_option_with_shortcut(self):
        _args, opts = SignatureParser.parse("{--force|-f}")
        assert opts[0].long == "--force"
        assert opts[0].short == "-f"

    def test_option_with_value(self):
        _args, opts = SignatureParser.parse("{--level=}")
        assert opts[0].attr_name == "level"
        assert opts[0].type is str
        assert opts[0].default is MISSING

    def test_option_with_default_value(self):
        _args, opts = SignatureParser.parse("{--count=3}")
        assert opts[0].attr_name == "count"
        assert opts[0].default == "3"

    def test_option_with_description(self):
        _args, opts = SignatureParser.parse("{--force : Force execution}")
        assert opts[0].description == "Force execution"

    def test_complex_signature(self):
        sig = "{name} {age?} {--force|-f} {--env=local : Environment}"
        args, opts = SignatureParser.parse(sig)
        assert len(args) == 2
        assert len(opts) == 2
        assert args[0].attr_name == "name"
        assert args[0].is_required is True
        assert args[1].attr_name == "age"
        assert args[1].is_required is False
        assert opts[0].attr_name == "force"
        assert opts[0].short == "-f"
        assert opts[1].attr_name == "env"
        assert opts[1].default == "local"

    def test_empty_signature(self):
        args, opts = SignatureParser.parse("")
        assert args == []
        assert opts == []

    def test_option_hyphenated_name(self):
        _args, opts = SignatureParser.parse("{--dry-run}")
        assert opts[0].attr_name == "dry_run"
        assert opts[0].long == "--dry-run"
