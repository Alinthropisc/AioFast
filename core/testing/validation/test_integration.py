from __future__ import annotations

import pytest
from pydantic import Field

from core.controller.base import Controller
from core.controller.compiler import _make_handler
from core.controller.decorators import get, post
from core.foundation.application import Application
from core.service.base import CrudService
from core.validation.dto import DTO, UpdateDTO
from core.validation.errors import ValidationError
from core.validation.validator import validate

# ── DTOs ──────────────────────────────────────────────────


class CreateProductDTO(DTO):
    name: str = Field(min_length=2, max_length=100)
    price: float = Field(gt=0)
    category: str = Field(default="general")


class UpdateProductDTO(UpdateDTO):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)


# ── Service ───────────────────────────────────────────────


class ProductService(CrudService):
    def __init__(self):
        self._items = {}
        self._next = 1

    async def get_all(self, **f):
        return list(self._items.values())

    async def get_by_id(self, id):
        return self._items.get(int(id))

    async def create(self, data):
        if isinstance(data, DTO):
            data = data.to_dict()
        item = {"id": self._next, **data}
        self._items[self._next] = item
        self._next += 1
        return item

    async def update(self, id, data):
        item = self._items.get(int(id))
        if item:
            if isinstance(data, DTO):
                data = data.changes() if hasattr(data, "changes") else data.to_dict()
            item.update(data)
        return item

    async def delete(self, id):
        return self._items.pop(int(id), None) is not None


# ── Controller with validation ────────────────────────────


class ProductController(Controller):
    path = "/products"

    def __init__(self, service: ProductService):
        self.service = service

    async def validate(self, action, data=None):
        if action == "store" and data is not None and isinstance(data, dict):
            return CreateProductDTO.create(data)
        if action == "update" and data is not None and isinstance(data, dict):
            return UpdateProductDTO.create(data)
        return data

    @get()
    async def index(self):
        items = await self.service.get_all()
        return self.ok(data=items)

    @post()
    async def store(self, data: dict | None = None):  # ty:ignore[invalid-parameter-default]
        # data is validated by validate() hook → CreateProductDTO
        item = await self.service.create(data)
        return self.created(data=item)


# ── Tests ─────────────────────────────────────────────────


class TestControllerValidation:
    @pytest.mark.asyncio
    async def test_store_valid(self):
        app = Application()
        app.singleton(ProductService)
        app.bind(ProductController)

        handler = _make_handler(ProductController, "store", app)
        result = await handler(data={"name": "Widget", "price": 9.99})

        assert result["status"] == 201
        assert result["data"]["name"] == "Widget"
        assert result["data"]["price"] == 9.99

    @pytest.mark.asyncio
    async def test_store_invalid(self):
        app = Application()
        app.singleton(ProductService)
        app.bind(ProductController)

        handler = _make_handler(ProductController, "store", app)
        result = await handler(data={"name": "A", "price": -1})

        assert result["status"] == 422
        assert result["success"] is False


class TestDTOWithService:
    @pytest.mark.asyncio
    async def test_create_flow(self):
        service = ProductService()
        dto = CreateProductDTO.create(
            {
                "name": "Gadget",
                "price": 19.99,
            }
        )
        item = await service.create(dto)
        assert item["name"] == "Gadget"
        assert item["price"] == 19.99

    @pytest.mark.asyncio
    async def test_update_flow(self):
        service = ProductService()
        await service.create({"name": "Old", "price": 10.0})

        dto = UpdateProductDTO.create({"name": "New"})
        assert dto.has_changes
        assert dto.changes() == {"name": "New"}

        item = await service.update(1, dto)
        assert item["name"] == "New"


class TestValidatorWithService:
    @pytest.mark.asyncio
    async def test_validate_then_create(self):
        service = ProductService()
        raw_data = {"name": "Widget", "price": 9.99}

        clean = validate(
            raw_data,
            {
                "name": "required|string|min_length:2",
                "price": "required|numeric|positive",
            },
        )

        item = await service.create(clean)
        assert item["name"] == "Widget"

    @pytest.mark.asyncio
    async def test_validate_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            validate(
                {"name": "", "price": -5},
                {
                    "name": "required|string",
                    "price": "required|positive",
                },
            )

        err = exc_info.value
        assert err.has("name")
        assert err.has("price")
