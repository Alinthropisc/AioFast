import pytest

from core.console.descriptors import (
    MISSING,
    Argument,
    Email,
    InChoices,
    Max,
    MaxLength,
    Min,
    MinLength,
    Option,
    Regex,
    Required,
    ValidationError,
)

# ── Argument ──────────────────────────────────────────────


class TestArgument:
    def test_default_values(self):
        arg = Argument()
        assert arg.type is str
        assert arg.default is MISSING
        assert arg.description == ""
        assert arg.rules == []

    def test_is_required_when_no_default(self):
        arg = Argument()
        assert arg.is_required is True

    def test_is_not_required_with_default(self):
        arg = Argument(default="hello")
        assert arg.is_required is False

    def test_cast_str(self):
        arg = Argument(type=str)
        assert arg.cast("hello") == "hello"

    def test_cast_int(self):
        arg = Argument(type=int)
        assert arg.cast("42") == 42

    def test_cast_float(self):
        arg = Argument(type=float)
        assert arg.cast("3.14") == 3.14

    def test_cast_bool_true(self):
        arg = Argument(type=bool)
        for val in ("true", "1", "yes", "y"):
            assert arg.cast(val) is True

    def test_cast_bool_false(self):
        arg = Argument(type=bool)
        for val in ("false", "0", "no", "n"):
            assert arg.cast(val) is False

    def test_set_name(self):
        arg = Argument()

        class Dummy:
            pass

        arg.__set_name__(Dummy, "my_arg")
        assert arg.attr_name == "my_arg"

    def test_validate_passes(self):
        arg = Argument(rules=[])
        arg.attr_name = "test"
        assert arg.validate("value") == []

    def test_validate_fails(self):
        arg = Argument(rules=[Required()])
        arg.attr_name = "test"
        errors = arg.validate(None)
        assert len(errors) == 1
        assert "required" in errors[0].lower()

    def test_repr(self):
        arg = Argument(type=int)
        arg.attr_name = "count"
        r = repr(arg)
        assert "count" in r
        assert "int" in r


# ── Option ────────────────────────────────────────────────


class TestOption:
    def test_default_values(self):
        opt = Option()
        assert opt.type is bool
        assert opt.default is MISSING
        assert opt.long == ""
        assert opt.short == ""

    def test_set_name_auto_long(self):
        opt = Option()

        class Dummy:
            pass

        opt.__set_name__(Dummy, "force_run")
        assert opt.attr_name == "force_run"
        assert opt.long == "--force-run"

    def test_set_name_preserves_explicit_long(self):
        opt = Option("--custom")

        class Dummy:
            pass

        opt.__set_name__(Dummy, "something")
        assert opt.long == "--custom"

    def test_is_flag(self):
        opt = Option(type=bool)
        assert opt.is_flag is True

    def test_is_not_flag_with_default(self):
        opt = Option(type=bool, default=True)
        assert opt.is_flag is False

    def test_effective_default_flag(self):
        opt = Option(type=bool)
        assert opt.effective_default is False

    def test_effective_default_explicit(self):
        opt = Option(type=int, default=42)
        assert opt.effective_default == 42

    def test_effective_default_none(self):
        opt = Option(type=str)
        assert opt.effective_default is None

    def test_effective_default_list(self):
        opt = Option(type=str, is_list=True)
        assert opt.effective_default == []

    def test_cast_bool(self):
        opt = Option(type=bool)
        assert opt.cast(True) is True
        assert opt.cast("true") is True
        assert opt.cast("false") is False

    def test_cast_int(self):
        opt = Option(type=int)
        assert opt.cast("42") == 42

    def test_cast_float(self):
        opt = Option(type=float)
        assert opt.cast("3.14") == 3.14

    def test_cast_str(self):
        opt = Option(type=str)
        assert opt.cast("hello") == "hello"

    def test_matches_long(self):
        opt = Option("--verbose")
        opt.attr_name = "verbose"
        assert opt.matches("--verbose") is True
        assert opt.matches("--other") is False

    def test_matches_short(self):
        opt = Option("--verbose", "-v")
        opt.attr_name = "verbose"
        assert opt.matches("-v") is True

    def test_matches_with_value(self):
        opt = Option("--level")
        opt.attr_name = "level"
        assert opt.matches("--level=5") is True

    def test_validate_passes(self):
        opt = Option(type=int, rules=[Min(0)])
        opt.attr_name = "count"
        assert opt.validate(5) == []

    def test_validate_fails(self):
        opt = Option(type=int, rules=[Min(10)])
        opt.attr_name = "count"
        errors = opt.validate(3)
        assert len(errors) == 1


# ── Rules ─────────────────────────────────────────────────


class TestRequired:
    def test_passes_with_value(self):
        Required().validate("field", "hello")

    def test_fails_with_none(self):
        with pytest.raises(ValidationError, match="required"):
            Required().validate("field", None)

    def test_fails_with_empty(self):
        with pytest.raises(ValidationError, match="required"):
            Required().validate("field", "")


class TestEmail:
    def test_valid_email(self):
        Email().validate("email", "user@example.com")

    def test_invalid_email(self):
        with pytest.raises(ValidationError, match="email"):
            Email().validate("email", "not-an-email")

    def test_none_passes(self):
        Email().validate("email", None)


class TestMin:
    def test_int_passes(self):
        Min(5).validate("age", 10)

    def test_int_fails(self):
        with pytest.raises(ValidationError, match="at least 5"):
            Min(5).validate("age", 3)

    def test_str_length_passes(self):
        Min(3).validate("name", "John")

    def test_str_length_fails(self):
        with pytest.raises(ValidationError, match="at least 3"):
            Min(3).validate("name", "ab")

    def test_none_passes(self):
        Min(5).validate("field", None)


class TestMax:
    def test_int_passes(self):
        Max(100).validate("score", 50)

    def test_int_fails(self):
        with pytest.raises(ValidationError, match="not exceed 100"):
            Max(100).validate("score", 150)

    def test_str_length_passes(self):
        Max(5).validate("code", "abc")

    def test_str_length_fails(self):
        with pytest.raises(ValidationError, match="not exceed 3"):
            Max(3).validate("code", "abcdef")


class TestInChoices:
    def test_valid_choice(self):
        InChoices(["a", "b", "c"]).validate("pick", "b")

    def test_invalid_choice(self):
        with pytest.raises(ValidationError, match="one of"):
            InChoices(["a", "b"]).validate("pick", "z")

    def test_none_passes(self):
        InChoices(["a"]).validate("pick", None)


class TestRegex:
    def test_matches(self):
        Regex(r"^\d{3}$").validate("code", "123")

    def test_not_matches(self):
        with pytest.raises(ValidationError):
            Regex(r"^\d{3}$").validate("code", "abc")

    def test_custom_message(self):
        with pytest.raises(ValidationError, match="Must be digits"):
            Regex(r"^\d+$", "Must be digits").validate("code", "abc")


class TestMinLength:
    def test_passes(self):
        MinLength(3).validate("name", "John")

    def test_fails(self):
        with pytest.raises(ValidationError, match="at least 3"):
            MinLength(3).validate("name", "ab")


class TestMaxLength:
    def test_passes(self):
        MaxLength(5).validate("code", "abc")

    def test_fails(self):
        with pytest.raises(ValidationError, match="not exceed 3"):
            MaxLength(3).validate("code", "abcdef")
