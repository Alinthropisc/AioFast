from __future__ import annotations

import pytest

from core.validation.sanitizer import Sanitizer


class TestSanitizerBasic:
    def test_trim(self):
        s = Sanitizer({"name": ["trim"]})
        result = s.sanitize({"name": "  hello  "})
        assert result["name"] == "hello"

    def test_lowercase(self):
        s = Sanitizer({"email": ["lowercase"]})
        result = s.sanitize({"email": "John@Example.COM"})
        assert result["email"] == "john@example.com"

    def test_uppercase(self):
        s = Sanitizer({"code": ["uppercase"]})
        result = s.sanitize({"code": "abc"})
        assert result["code"] == "ABC"

    def test_title_case(self):
        s = Sanitizer({"name": ["title_case"]})
        result = s.sanitize({"name": "john doe"})
        assert result["name"] == "John Doe"

    def test_capitalize(self):
        s = Sanitizer({"name": ["capitalize"]})
        result = s.sanitize({"name": "hello world"})
        assert result["name"] == "Hello world"


class TestSanitizerStripping:
    def test_strip_tags(self):
        s = Sanitizer({"bio": ["strip_tags"]})
        result = s.sanitize({"bio": "<b>Hello</b> <script>alert('xss')</script>"})
        assert "<" not in result["bio"]
        assert "Hello" in result["bio"]

    def test_escape_html(self):
        s = Sanitizer({"text": ["escape_html"]})
        result = s.sanitize({"text": '<script>alert("xss")</script>'})
        assert "&lt;script&gt;" in result["text"]

    def test_strip_non_digits(self):
        s = Sanitizer({"phone": ["strip_non_digits"]})
        result = s.sanitize({"phone": "+1 (555) 123-4567"})
        assert result["phone"] == "15551234567"


class TestSanitizerSlug:
    def test_slug(self):
        s = Sanitizer({"slug": ["slug"]})
        result = s.sanitize({"slug": "Hello World! 123"})
        assert result["slug"] == "hello-world-123"


class TestSanitizerChaining:
    def test_multiple_sanitizers(self):
        s = Sanitizer({"email": ["trim", "lowercase"]})
        result = s.sanitize({"email": "  John@Example.COM  "})
        assert result["email"] == "john@example.com"

    def test_trim_then_title(self):
        s = Sanitizer({"name": ["trim", "title_case"]})
        result = s.sanitize({"name": "  john DOE  "})
        assert result["name"] == "John Doe"


class TestSanitizerNullify:
    def test_nullify_empty(self):
        s = Sanitizer({"bio": ["trim", "nullify_empty"]})
        result = s.sanitize({"bio": "   "})
        assert result["bio"] is None

    def test_nullify_non_empty(self):
        s = Sanitizer({"bio": ["trim", "nullify_empty"]})
        result = s.sanitize({"bio": "Hello"})
        assert result["bio"] == "Hello"


class TestSanitizerCustom:
    def test_callable_sanitizer(self):
        s = Sanitizer({"age": [lambda v: abs(v) if isinstance(v, int) else v]})
        result = s.sanitize({"age": -5})
        assert result["age"] == 5

    def test_non_string_passthrough(self):
        s = Sanitizer({"count": ["trim"]})  # trim on int
        result = s.sanitize({"count": 42})
        assert result["count"] == 42  # unchanged


class TestSanitizerGlobal:
    def test_global_sanitizer(self):
        s = Sanitizer(global_sanitizers=["trim"])
        result = s.sanitize({"a": "  x  ", "b": "  y  "})
        assert result["a"] == "x"
        assert result["b"] == "y"


class TestSanitizerUnknown:
    def test_unknown_raises(self):
        s = Sanitizer({"name": ["nonexistent_sanitizer"]})
        with pytest.raises(ValueError, match="Unknown"):
            s.sanitize({"name": "test"})
