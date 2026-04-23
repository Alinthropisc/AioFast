from __future__ import annotations

import pytest

from core.validation.errors import ErrorBag, FieldError, ValidationError


class TestValidationError:
    def test_from_dict(self):
        e = ValidationError({"name": ["Required"], "email": ["Invalid"]})
        assert len(e.errors) == 2

    def test_from_string(self):
        e = ValidationError("Something went wrong")
        assert "_general" in e.errors
        assert "Something went wrong" in e.errors["_general"]

    def test_from_list(self):
        e = ValidationError(["Error 1", "Error 2"])
        assert len(e.errors["_general"]) == 2

    def test_failed_fields(self):
        e = ValidationError({"name": ["Required"], "email": ["Invalid"]})
        assert "name" in e.failed_fields
        assert "email" in e.failed_fields

    def test_all_messages(self):
        e = ValidationError({"a": ["E1", "E2"], "b": ["E3"]})
        assert len(e.all_messages) == 3

    def test_first(self):
        e = ValidationError({"name": ["Required", "Too short"]})
        assert e.first() == "Required"
        assert e.first("name") == "Required"
        assert e.first("missing") is None

    def test_has(self):
        e = ValidationError({"name": ["Required"]})
        assert e.has("name") is True
        assert e.has("email") is False

    def test_get(self):
        e = ValidationError({"name": ["A", "B"]})
        assert e.get("name") == ["A", "B"]
        assert e.get("missing") == []

    def test_to_dict(self):
        e = ValidationError({"name": ["Required"]})
        d = e.to_dict()
        assert d["message"] == "Validation failed"
        assert d["errors"]["name"] == ["Required"]

    def test_to_response(self):
        e = ValidationError({"x": ["Bad"]})
        r = e.to_response()
        assert r["success"] is False
        assert r["status"] == 422

    def test_merge(self):
        e1 = ValidationError({"a": ["E1"]})
        e2 = ValidationError({"a": ["E2"], "b": ["E3"]})
        e1.merge(e2)
        assert len(e1.errors["a"]) == 2
        assert "b" in e1.errors

    def test_bool(self):
        assert bool(ValidationError({"a": ["E"]})) is True
        assert bool(ValidationError({})) is False

    def test_len(self):
        e = ValidationError({"a": ["1", "2"], "b": ["3"]})
        assert len(e) == 3

    def test_repr(self):
        e = ValidationError({"a": ["1"]})
        assert "ValidationError" in repr(e)


class TestErrorBag:
    def test_add(self):
        bag = ErrorBag()
        bag.add("name", "Required")
        assert bag.has_errors is True
        assert "name" in bag.errors

    def test_add_many(self):
        bag = ErrorBag()
        bag.add_many("name", ["Too short", "Invalid chars"])
        assert len(bag.errors["name"]) == 2

    def test_merge(self):
        bag = ErrorBag()
        bag.merge({"a": ["E1"], "b": ["E2"]})
        assert len(bag.errors) == 2

    def test_first(self):
        bag = ErrorBag()
        bag.add("x", "First error")
        bag.add("x", "Second error")
        assert bag.first("x") == "First error"
        assert bag.first() == "First error"

    def test_to_exception(self):
        bag = ErrorBag()
        bag.add("name", "Required")
        exc = bag.to_exception()
        assert isinstance(exc, ValidationError)

    def test_raise_if_errors(self):
        bag = ErrorBag()
        bag.raise_if_errors()  # should not raise

        bag.add("x", "Error")
        with pytest.raises(ValidationError):
            bag.raise_if_errors()

    def test_clear(self):
        bag = ErrorBag()
        bag.add("x", "Error")
        bag.clear()
        assert bag.has_errors is False

    def test_bool(self):
        bag = ErrorBag()
        assert bool(bag) is False
        bag.add("x", "E")
        assert bool(bag) is True

    def test_len(self):
        bag = ErrorBag()
        bag.add("a", "1")
        bag.add("a", "2")
        bag.add("b", "3")
        assert len(bag) == 3


class TestFieldError:
    def test_basic(self):
        fe = FieldError("name")
        fe.add("Required")
        fe.add("Too short")
        assert fe.field == "name"
        assert len(fe.messages) == 2
        assert fe.has_errors is True

    def test_no_errors(self):
        fe = FieldError("name")
        assert fe.has_errors is False
