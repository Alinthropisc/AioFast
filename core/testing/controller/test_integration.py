from __future__ import annotations

import pytest

from core.controller.base import Controller, ResourceController
from core.controller.compiler import compile_controller, compile_resource
from core.controller.decorators import delete, get, post
from core.controller.response import ApiResponse
from core.foundation.application import Application
from core.registry.route import RouteCollector
from core.service.base import CrudService

# ── service ───────────────────────────────────────────────


class ProductService(CrudService):
    def __init__(self):
        self._items = {
            1: {"id": 1, "name": "Widget", "price": 9.99},
            2: {"id": 2, "name": "Gadget", "price": 19.99},
        }
        self._next = 3

    async def get_all(self, **f):
        return list(self._items.values())

    async def get_by_id(self, id):
        return self._items.get(int(id))

    async def create(self, data):
        item = {"id": self._next, **data}
        self._items[self._next] = item
        self._next += 1
        return item

    async def update(self, id, data):
        item = self._items.get(int(id))
        if item:
            item.update(data)
        return item

    async def delete(self, id):
        return self._items.pop(int(id), None) is not None


# ── decorator controller ──────────────────────────────────


class ProductController(Controller):
    path = "/products"
    tags = ["products"]

    def __init__(self, service: ProductService):
        self.service = service

    @get()
    async def index(self) -> dict:
        items = await self.service.get_all()
        return ApiResponse.collection(items)

    @get("/{product_id:int}")
    async def show(self, product_id: int) -> dict:
        item = await self.service.get_by_id(product_id)
        if item is None:
            return ApiResponse.not_found(resource="Product")
        return ApiResponse.success(data=item)

    @post()
    async def store(self, name: str = "New", price: float = 0.0) -> dict:
        item = await self.service.create({"name": name, "price": price})
        return ApiResponse.created(data=item)

    @delete("/{product_id:int}")
    async def destroy(self, product_id: int) -> dict:
        deleted = await self.service.delete(product_id)
        if not deleted:
            return ApiResponse.not_found(resource="Product")
        return ApiResponse.no_content()


# ── resource controller ───────────────────────────────────


class CategoryController(ResourceController):
    path = "/categories"
    id_param = "category_id"

    def __init__(self, service: ProductService):
        self.service = service

    async def index(self) -> dict:
        return ApiResponse.collection(await self.service.get_all())

    async def show(self, category_id: int) -> dict:
        item = await self.service.get_by_id(category_id)
        return ApiResponse.success(data=item)

    async def store(self, name: str = "Cat") -> dict:
        item = await self.service.create({"name": name})
        return ApiResponse.created(data=item)

    async def update(self, category_id: int) -> dict:
        return ApiResponse.success(data={"id": category_id})

    async def destroy(self, category_id: int) -> dict:
        await self.service.delete(category_id)
        return ApiResponse.no_content()


# ── tests ─────────────────────────────────────────────────


class TestControllerWithDI:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        app = Application()
        app.singleton(ProductService)
        app.bind(ProductController)

        routes = compile_controller(ProductController, app)

        # Find and call index
        index = next(r for r in routes if "index" in r.name)  # ty:ignore[unsupported-operator]
        result = await index.handler()
        assert result["success"] is True
        assert result["meta"]["count"] == 2

        # Find and call show
        show = next(r for r in routes if "show" in r.name)  # ty:ignore[unsupported-operator]
        result = await show.handler(product_id=1)
        assert result["data"]["name"] == "Widget"

        # Show not found
        result = await show.handler(product_id=999)
        assert result["success"] is False
        assert result["status"] == 404

        # Create
        store = next(r for r in routes if "store" in r.name)  # ty:ignore[unsupported-operator]
        result = await store.handler(name="NewItem", price=5.0)
        assert result["status"] == 201
        assert result["data"]["name"] == "NewItem"

        # Delete
        destroy = next(r for r in routes if "destroy" in r.name)  # ty:ignore[unsupported-operator]
        result = await destroy.handler(product_id=1)
        assert result["status"] == 204


class TestResourceControllerWithDI:
    @pytest.mark.asyncio
    async def test_generates_crud(self):
        app = Application()
        app.singleton(ProductService)
        app.bind(CategoryController)

        routes = compile_resource(CategoryController, app)
        assert len(routes) == 5  # ← compile_resource: без PATCH

        names = {r.name for r in routes}
        assert "category.index" in names
        assert "category.show" in names
        assert "category.store" in names
        assert "category.update" in names
        assert "category.destroy" in names

    @pytest.mark.asyncio
    async def test_resource_calls(self):
        app = Application()
        app.singleton(ProductService)
        app.bind(CategoryController)

        routes = compile_resource(CategoryController, app)

        index = next(r for r in routes if "index" in r.name)  # ty:ignore[unsupported-operator]
        result = await index.handler()
        assert result["success"] is True

        show = next(r for r in routes if "show" in r.name)  # ty:ignore[unsupported-operator]
        result = await show.handler(category_id=1)
        assert result["success"] is True


class TestRouteCollectorIntegration:
    def test_controller_registration(self):
        collector = RouteCollector()

        with collector.group(prefix="/api/v1") as r:
            r.controller(ProductController)

        routes = collector.collect()
        assert len(routes) >= 4

        paths = {r.path for r in routes}
        assert "/api/v1/products" in paths
        assert "/api/v1/products/{product_id:int}" in paths

    def test_resource_registration(self):
        collector = RouteCollector()

        with collector.group(prefix="/api") as r:
            r.resource("/categories", CategoryController)

        routes = collector.collect()
        assert len(routes) == 6  # ← simple resource: включает PATCH

        paths = {r.path for r in routes}
        assert "/api/categories" in paths
        assert "/api/categories/{id}" in paths  # ← простой resource использует {id}

    def test_mixed_routes(self):
        collector = RouteCollector()

        async def health():
            return {"ok": True}

        with collector as r:
            r.get("/health", health, name="health")

            with r.group(prefix="/api/v1") as api:
                api.controller(ProductController)
                api.resource("/categories", CategoryController)

        routes = collector.collect()
        # 1 health + 4 product + 6 category = 11
        assert len(routes) >= 11

        names = {r.name for r in routes if r.name}
        assert "health" in names
        assert any("product" in n for n in names)
        assert any("categories" in n for n in names)  # ← "categories", НЕ "category"
