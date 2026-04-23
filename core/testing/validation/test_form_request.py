from __future__ import annotations

import pytest

from core.validation.errors import ValidationError
from core.validation.form_request import FormRequest


class CreateUserRequest(FormRequest):
    def rules(self):
        return {
            "name": "required|string|min_length:2",
            "email": "required|email",
            "age": "integer|min:18",
        }

    def messages(self):
        return {
            "name.required": "Name is required",
            "email.email": "Enter a valid email",
        }

    def sanitizers(self):
        return {
            "name": ["trim", "title_case"],
            "email": ["trim", "lowercase"],
        }

    def after_validation(self, data):
        data["normalized"] = True
        return data


class AuthorizedRequest(FormRequest):
    def authorize(self):
        return self.user is not None and self.user.get("role") == "admin"

    def rules(self):
        return {"action": "required|string"}


class TestFormRequestValidation:
    @pytest.mark.asyncio
    async def test_valid(self):
        req = CreateUserRequest(
            {
                "name": "  john doe  ",
                "email": "  John@Example.COM  ",
                "age": 25,
            }
        )
        clean = await req.validate()
        assert clean["name"] == "John Doe"  # sanitized
        assert clean["email"] == "john@example.com"  # sanitized
        assert clean["normalized"] is True  # after_validation

    @pytest.mark.asyncio
    async def test_invalid(self):
        req = CreateUserRequest(
            {
                "name": "",
                "email": "bad",
            }
        )
        with pytest.raises(ValidationError) as exc:
            await req.validate()
        assert exc.value.has("name")

    @pytest.mark.asyncio
    async def test_custom_messages(self):
        req = CreateUserRequest({"name": "", "email": "bad"})
        with pytest.raises(ValidationError) as exc:
            await req.validate()
        assert "Name is required" in exc.value.get("name")


class TestFormRequestAuthorization:
    @pytest.mark.asyncio
    async def test_authorized(self):
        req = AuthorizedRequest(
            {"action": "delete"},
            user={"role": "admin"},
        )
        clean = await req.validate()
        assert clean["action"] == "delete"

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        req = AuthorizedRequest({"action": "delete"}, user=None)
        with pytest.raises(PermissionError):
            await req.validate()


class TestFormRequestValidateOrError:
    @pytest.mark.asyncio
    async def test_valid(self):
        req = CreateUserRequest(
            {
                "name": "Alice",
                "email": "alice@test.com",
                "age": 25,
            }
        )
        data, error = await req.validate_or_error()
        assert data is not None
        assert error is None

    @pytest.mark.asyncio
    async def test_invalid(self):
        req = CreateUserRequest({"name": "", "email": ""})
        data, error = await req.validate_or_error()
        assert data is None
        assert error is not None
        assert error["status"] == 422

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        req = AuthorizedRequest({"action": "x"}, user=None)
        data, error = await req.validate_or_error()
        assert data is None
        assert error["status"] == 403  # ty:ignore[not-subscriptable]
