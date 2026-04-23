from __future__ import annotations

import pytest

from core.validation.errors import ValidationError
from core.validation.validator import Validator, validate


class TestValidatorPasses:
    def test_valid_data(self, user_data):
        v = Validator(
            user_data,
            {
                "name": "required|string",
                "email": "required|email",
                "age": "required|integer|min:18",
            },
        )
        assert v.passes() is True
        assert v.fails() is False

    def test_validated_data(self, user_data):
        v = Validator(
            user_data,
            {
                "name": "required|string",
                "email": "required|email",
            },
        )
        clean = v.validated()
        # assert clean["name"] == "Alice"
        assert clean["name"] == "John"
        # assert clean["email"] == "alice@example.com"
        assert clean["email"] == "john@example.com"

    def test_only_rule_fields(self, user_data):
        v = Validator(user_data, {"name": "required"})
        clean = v.validated()
        assert "name" in clean
        assert "email" not in clean  # no rule for email


class TestValidatorFails:
    def test_invalid_data(self, invalid_data):
        v = Validator(
            invalid_data,
            {
                "name": "required",
                "email": "required|email",
                "age": "required|integer|min:18",
            },
        )
        assert v.fails() is True

    def test_error_messages(self, invalid_data):
        v = Validator(
            invalid_data,
            {
                "name": "required",
                "email": "required|email",
            },
        )
        v.fails()
        errors = v.error_messages()
        assert "name" in errors
        assert "email" in errors

    def test_error_response(self, invalid_data):
        v = Validator(invalid_data, {"email": "required|email"})
        v.fails()
        resp = v.error_response()
        assert resp["success"] is False
        assert resp["status"] == 422
        assert "errors" in resp


class TestValidatorValidate:
    def test_validate_returns_clean(self, user_data):
        clean = Validator(
            user_data,
            {
                "name": "required|string",
            },
        ).validate()
        # assert clean["name"] == "Alice"
        assert clean["name"] == "John"

    def test_validate_raises(self, invalid_data):
        with pytest.raises(ValidationError) as exc_info:
            Validator(
                invalid_data,
                {
                    "name": "required",
                    "email": "email",
                },
            ).validate()
        assert exc_info.value.has("name")


class TestValidatorCustomMessages:
    def test_custom_message(self):
        v = Validator(
            {"email": "bad"},
            {"email": "required|email"},
            messages={"email.email": "Please enter a valid email"},
        )
        v.fails()
        msgs = v.errors.get("email")  # ty:ignore[unresolved-attribute]
        assert "Please enter a valid email" in msgs

    def test_field_level_message(self):
        v = Validator(
            {"name": ""},
            {"name": "required"},
            messages={"name": "Name cannot be empty"},
        )
        v.fails()
        assert "Name cannot be empty" in v.errors.get("name")  # ty:ignore[unresolved-attribute]


class TestValidatorStopOnFirst:
    def test_stop_on_first(self):
        v = Validator(
            {"name": ""},
            {"name": "required|string|min_length:5"},
            stop_on_first=True,
        )
        v.fails()
        assert len(v.errors.get("name")) == 1  # only first error  # ty:ignore[unresolved-attribute]


class TestValidatorDotNotation:
    def test_nested_data(self):
        data = {
            "user": {
                "profile": {
                    "name": "Alice",
                },
            },
        }
        v = Validator(data, {"user.profile.name": "required|string"})
        assert v.passes() is True

    def test_nested_missing(self):
        v = Validator({}, {"user.profile.name": "required"})
        assert v.fails() is True


class TestValidateFunction:
    def test_valid(self, user_data):
        clean = validate(user_data, {"name": "required|string"})
        # assert clean["name"] == "Alice"
        assert clean["name"] == "John"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate({}, {"name": "required"})


class TestValidatorRepr:
    def test_repr(self):
        v = Validator({}, {"name": "required"})
        assert "Validator" in repr(v)
        assert "pending" in repr(v)

        v.fails()
        assert "validated" in repr(v)
