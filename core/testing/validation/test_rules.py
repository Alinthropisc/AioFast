from __future__ import annotations

import pytest

from core.validation.rules import (
    Alpha,
    AlphaNumeric,
    Between,
    Confirmed,
    Email,
    Equals,
    In,
    Integer,
    IsBool,
    IsDict,
    IsList,
    Max,
    MaxLength,
    Min,
    MinLength,
    NotIn,
    Numeric,
    Positive,
    Regex,
    Required,
    Slug,
    StringRule,
    Url,
    parse_rule_string,
    parse_rules,
    rule,
)


class TestRequired:
    def test_passes_with_value(self):
        assert Required().passes("f", "hello") is True
        assert Required().passes("f", 0) is True
        assert Required().passes("f", False) is True

    def test_fails_none(self):
        assert Required().passes("f", None) is False

    def test_fails_empty_string(self):
        assert Required().passes("f", "") is False
        assert Required().passes("f", "   ") is False


class TestStringRule:
    def test_passes(self):
        assert StringRule().passes("f", "hello") is True

    def test_fails(self):
        assert StringRule().passes("f", 123) is False
        assert StringRule().passes("f", None) is False


class TestEmail:
    def test_valid(self):
        assert Email().passes("f", "user@example.com") is True
        assert Email().passes("f", "a.b+c@d.co") is True

    def test_invalid(self):
        assert Email().passes("f", "not-email") is False
        assert Email().passes("f", "@no.com") is False
        assert Email().passes("f", "a@") is False
        assert Email().passes("f", 123) is False


class TestUrl:
    def test_valid(self):
        assert Url().passes("f", "https://example.com") is True
        assert Url().passes("f", "http://localhost:8000/path") is True

    def test_invalid(self):
        assert Url().passes("f", "not-a-url") is False
        assert Url().passes("f", "ftp://file.com") is False


class TestMinLength:
    def test_passes(self):
        assert MinLength(3).passes("f", "abc") is True
        assert MinLength(3).passes("f", "abcd") is True

    def test_fails(self):
        assert MinLength(3).passes("f", "ab") is False
        assert MinLength(3).passes("f", "") is False

    def test_list(self):
        assert MinLength(2).passes("f", [1, 2]) is True
        assert MinLength(2).passes("f", [1]) is False


class TestMaxLength:
    def test_passes(self):
        assert MaxLength(5).passes("f", "abc") is True
        assert MaxLength(5).passes("f", "abcde") is True

    def test_fails(self):
        assert MaxLength(5).passes("f", "abcdef") is False


class TestBetween:
    def test_passes(self):
        assert Between(2, 5).passes("f", "abc") is True

    def test_fails(self):
        assert Between(2, 5).passes("f", "a") is False
        assert Between(2, 5).passes("f", "abcdef") is False


class TestNumeric:
    def test_passes(self):
        assert Numeric().passes("f", 42) is True
        assert Numeric().passes("f", 3.14) is True

    def test_fails(self):
        assert Numeric().passes("f", "42") is False
        assert Numeric().passes("f", True) is False


class TestInteger:
    def test_passes(self):
        assert Integer().passes("f", 42) is True

    def test_fails(self):
        assert Integer().passes("f", 3.14) is False
        assert Integer().passes("f", True) is False


class TestMin:
    def test_passes(self):
        assert Min(18).passes("f", 18) is True
        assert Min(18).passes("f", 25) is True

    def test_fails(self):
        assert Min(18).passes("f", 17) is False


class TestMax:
    def test_passes(self):
        assert Max(100).passes("f", 100) is True
        assert Max(100).passes("f", 50) is True

    def test_fails(self):
        assert Max(100).passes("f", 101) is False


class TestPositive:
    def test_passes(self):
        assert Positive().passes("f", 1) is True

    def test_fails(self):
        assert Positive().passes("f", 0) is False
        assert Positive().passes("f", -1) is False


class TestIn:
    def test_passes(self):
        assert In(["a", "b", "c"]).passes("f", "a") is True

    def test_fails(self):
        assert In(["a", "b", "c"]).passes("f", "d") is False


class TestNotIn:
    def test_passes(self):
        assert NotIn(["x", "y"]).passes("f", "a") is True

    def test_fails(self):
        assert NotIn(["x", "y"]).passes("f", "x") is False


class TestAlpha:
    def test_passes(self):
        assert Alpha().passes("f", "hello") is True

    def test_fails(self):
        assert Alpha().passes("f", "hello123") is False


class TestAlphaNumeric:
    def test_passes(self):
        assert AlphaNumeric().passes("f", "hello123") is True

    def test_fails(self):
        assert AlphaNumeric().passes("f", "hello 123") is False


class TestSlug:
    def test_passes(self):
        assert Slug().passes("f", "hello-world") is True
        assert Slug().passes("f", "post123") is True

    def test_fails(self):
        assert Slug().passes("f", "Hello World") is False
        assert Slug().passes("f", "has spaces") is False


class TestRegex:
    def test_passes(self):
        assert Regex(r"^\d{3}-\d{4}$").passes("f", "123-4567") is True

    def test_fails(self):
        assert Regex(r"^\d{3}-\d{4}$").passes("f", "abc") is False


class TestEquals:
    def test_passes(self):
        assert Equals("yes").passes("f", "yes") is True

    def test_fails(self):
        assert Equals("yes").passes("f", "no") is False


class TestConfirmed:
    def test_passes(self):
        r = Confirmed()
        r.set_data({"password": "abc", "password_confirmation": "abc"})
        assert r.passes("password", "abc") is True

    def test_fails(self):
        r = Confirmed()
        r.set_data({"password": "abc", "password_confirmation": "xyz"})
        assert r.passes("password", "abc") is False


class TestTypeRules:
    def test_is_list(self):
        assert IsList().passes("f", [1, 2]) is True
        assert IsList().passes("f", "not list") is False

    def test_is_dict(self):
        assert IsDict().passes("f", {"a": 1}) is True
        assert IsDict().passes("f", []) is False

    def test_is_bool(self):
        assert IsBool().passes("f", True) is True
        assert IsBool().passes("f", 1) is False


class TestCallableRule:
    def test_passes(self):
        r = rule(lambda v: v > 0, "Must be positive")
        assert r.passes("f", 5) is True
        assert r.passes("f", -1) is False


class TestParseRuleString:
    def test_simple(self):
        r = parse_rule_string("required")
        assert isinstance(r, Required)

    def test_with_param(self):
        r = parse_rule_string("min_length:3")
        assert isinstance(r, MinLength)

    def test_with_multiple_params(self):
        r = parse_rule_string("between:1,10")
        assert isinstance(r, Between)

    def test_in_rule(self):
        r = parse_rule_string("in:active,inactive,pending")
        assert isinstance(r, In)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            parse_rule_string("nonexistent_rule")


class TestParseRules:
    def test_pipe_string(self):
        rules = parse_rules("required|email|max_length:255")
        assert len(rules) == 3
        assert isinstance(rules[0], Required)
        assert isinstance(rules[1], Email)
        assert isinstance(rules[2], MaxLength)

    def test_list_of_strings(self):
        rules = parse_rules(["required", "string"])
        assert len(rules) == 2

    def test_list_of_objects(self):
        rules = parse_rules([Required(), Email()])
        assert len(rules) == 2

    def test_mixed(self):
        rules = parse_rules(["required", Email(), "min_length:5"])
        assert len(rules) == 3

    def test_get_message(self):
        r = Required()
        msg = r.get_message("email", None)
        assert "email" in msg
