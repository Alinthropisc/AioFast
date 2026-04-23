from __future__ import annotations

import pytest

from core.validation.async_rules import Exists, Unique, async_rule
from core.validation.validator import Validator


class TestUnique:
    @pytest.mark.asyncio
    async def test_unique_passes(self):
        emails = {"taken@test.com"}
        r = Unique(checker=lambda v: v in emails)
        assert await r.passes_async("email", "new@test.com") is True

    @pytest.mark.asyncio
    async def test_unique_fails(self):
        emails = {"taken@test.com"}
        r = Unique(checker=lambda v: v in emails)
        assert await r.passes_async("email", "taken@test.com") is False

    @pytest.mark.asyncio
    async def test_unique_async_checker(self):
        async def check(v):
            return v == "exists@test.com"

        r = Unique(checker=check)
        assert await r.passes_async("email", "new@test.com") is True
        assert await r.passes_async("email", "exists@test.com") is False


class TestExists:
    @pytest.mark.asyncio
    async def test_exists_passes(self):
        categories = {1: "Tech", 2: "Science"}
        r = Exists(checker=lambda v: categories.get(v))
        assert await r.passes_async("category_id", 1) is True

    @pytest.mark.asyncio
    async def test_exists_fails(self):
        categories = {1: "Tech"}
        r = Exists(checker=lambda v: categories.get(v))
        assert await r.passes_async("category_id", 999) is False


class TestAsyncCallableRule:
    @pytest.mark.asyncio
    async def test_passes(self):
        r = async_rule(lambda v: v > 0, "Must be positive")
        assert await r.passes_async("f", 5) is True
        assert await r.passes_async("f", -1) is False


class TestValidatorAsync:
    @pytest.mark.asyncio
    async def test_async_validation(self):
        existing_emails = {"taken@test.com"}

        data = {"email": "new@test.com", "name": "Alice"}
        v = Validator(
            data,
            {
                "name": "required|string",
                "email": [
                    "required",
                    "email",
                    Unique(checker=lambda v: v in existing_emails),
                ],
            },
        )
        clean = await v.validate_async()
        assert clean["email"] == "new@test.com"

    @pytest.mark.asyncio
    async def test_async_validation_fails(self):
        existing_emails = {"taken@test.com"}

        from core.validation.errors import ValidationError

        data = {"email": "taken@test.com", "name": "Bob"}
        v = Validator(
            data,
            {
                "email": [
                    "required",
                    Unique(checker=lambda v: v in existing_emails),
                ],
            },
        )
        with pytest.raises(ValidationError):
            await v.validate_async()
