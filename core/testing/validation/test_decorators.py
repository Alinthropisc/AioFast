from __future__ import annotations

import pytest
from pydantic import Field

from core.validation.decorators import validate_input, validated
from core.validation.dto import DTO


class SampleDTO(DTO):
    name: str = Field(min_length=2)
    email: str


class TestValidatedWithRules:
    @pytest.mark.asyncio
    async def test_valid(self):
        @validated(rules={"name": "required|string", "email": "required|email"})
        async def handler(data: dict):
            return {"ok": True, "data": data}

        result = await handler(data={"name": "Alice", "email": "a@b.com"})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invalid(self):
        @validated(rules={"name": "required", "email": "required|email"})
        async def handler(data: dict):
            return {"ok": True}

        result = await handler(data={"name": "", "email": "bad"})
        assert result["success"] is False
        assert result["status"] == 422


class TestValidatedWithDTO:
    @pytest.mark.asyncio
    async def test_valid(self):
        @validated(dto_class=SampleDTO)
        async def handler(data: SampleDTO):
            return {"name": data.name}

        result = await handler(data={"name": "Alice", "email": "a@b.com"})
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_invalid(self):
        @validated(dto_class=SampleDTO)
        async def handler(data: SampleDTO):
            return {"ok": True}

        result = await handler(data={"name": "A"})  # too short
        assert result["success"] is False
        assert result["status"] == 422


class TestValidateInput:
    @pytest.mark.asyncio
    async def test_valid(self):
        @validate_input({"name": "required|string"})
        async def handler(name: str):
            return {"name": name}

        result = await handler(name="Alice")
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_invalid(self):
        @validate_input({"name": "required"})
        async def handler(name: str = ""):
            return {"name": name}

        result = await handler(name="")
        assert result["success"] is False
