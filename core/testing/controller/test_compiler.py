from __future__ import annotations

import inspect

import pytest

from core.controller.base import Controller, ResourceController
from core.controller.compiler import (
    _make_handler,
    compile_controller,
    compile_resource,
)
from core.controller.decorators import delete, get, post, put
from core.foundation.application import Application
from core.service.base import Service

# ── test services ─────────────────────────────────────────


class GreetingService(Service):
    async def greet(self, name: str) -> str:
        return f"Hello, {name}!"


# ── test controllers ──────────────────────────────────────


class HomeController(Controller):
    path = ""

    @get("/")
    async def index(self) -> dict:
        return {"message": "home"}


class UserController(Controller):
    path = "/users"
    tags = ["users"]

    def __init__(self, service: GreetingService):
        self.service = service

    @get()
    async def index(self) -> list:
        return [{"id": 1}]

    @get("/{user_id:int}")
    async def show(self, user_id: int) -> dict:
        return {"id": user_id}

    @post()
    async def store(self, name: str = "test") -> dict:
        greeting = await self.service.greet(name)
        return {"greeting": greeting}

    @put("/{user_id:int}")
    async def update(self, user_id: int) -> dict:
        return {"id": user_id, "updated": True}

    @delete("/{user_id:int}")
    async def destroy(self, user_id: int) -> dict:
        return {"deleted": user_id}


class ArticleController(ResourceController):
    path = "/articles"

    async def index(self) -> list:
        return [{"id": 1, "title": "First"}]

    async def show(self, id: int) -> dict:
        return {"id": id}

    async def store(self, title: str = "Untitled") -> dict:
        return {"id": 2, "title": title}

    async def update(self, id: int) -> dict:
        return {"id": id, "updated": True}

    async def destroy(self, id: int) -> dict:
        return {"deleted": id}


# ── tests ─────────────────────────────────────────────────


class TestCompileController:
    def test_compiles_routes(self):
        routes = compile_controller(HomeController)
        assert len(routes) == 1
        assert routes[0].path == "/"
        assert routes[0].methods == ["GET"]

    def test_compiles_all_methods(self):
        routes = compile_controller(UserController)
        assert len(routes) == 5  # index, show, store, update, destroy

    def test_paths(self):
        routes = compile_controller(UserController)
        paths = {r.path for r in routes}
        assert "/users" in paths
        assert "/users/{user_id:int}" in paths

    def test_methods(self):
        routes = compile_controller(UserController)
        methods_by_name = {r.name.split(".")[-1]: r.methods[0] for r in routes}  # ty:ignore[unresolved-attribute]
        assert methods_by_name["index"] == "GET"
        assert methods_by_name["store"] == "POST"
        assert methods_by_name["update"] == "PUT"
        assert methods_by_name["destroy"] == "DELETE"

    def test_names(self):
        routes = compile_controller(UserController)
        names = [r.name for r in routes]
        assert "user.index" in names
        assert "user.show" in names
        assert "user.store" in names

    def test_tags(self):
        routes = compile_controller(UserController)
        for r in routes:
            assert "users" in r.tags

    def test_handler_signature_no_self(self):
        routes = compile_controller(UserController)
        show_route = next(r for r in routes if "show" in r.name)  # ty:ignore[unsupported-operator]
        sig = inspect.signature(show_route.handler)
        assert "self" not in sig.parameters
        assert "user_id" in sig.parameters


class TestCompileResource:
    def test_generates_crud_routes(self):
        routes = compile_resource(ArticleController)
        assert len(routes) == 5

    def test_resource_paths(self):
        routes = compile_resource(ArticleController)
        paths = {r.methods[0]: r.path for r in routes}
        assert paths["GET"] in ("/articles", "/articles/{id:int}")
        assert paths["POST"] == "/articles"
        assert paths["PUT"] == "/articles/{id:int}"
        assert paths["DELETE"] == "/articles/{id:int}"

    def test_resource_names(self):
        routes = compile_resource(ArticleController)
        names = {r.name for r in routes}
        assert "article.index" in names
        assert "article.show" in names
        assert "article.store" in names
        assert "article.update" in names
        assert "article.destroy" in names

    def test_custom_path(self):
        routes = compile_resource(ArticleController, path="/blog/posts")
        for r in routes:
            assert r.path.startswith("/blog/posts")


class TestMakeHandler:
    @pytest.mark.asyncio
    async def test_handler_without_container(self):
        handler = _make_handler(HomeController, "index", None)
        result = await handler()
        assert result == {"message": "home"}

    @pytest.mark.asyncio
    async def test_handler_with_container(self):
        app = Application()
        app.singleton(GreetingService)
        app.bind(UserController)

        handler = _make_handler(UserController, "index", app)
        result = await handler()
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_handler_with_params(self):
        from unittest.mock import AsyncMock

        from core.foundation import Container

        container = Container()
        mock_service = AsyncMock()  # без spec
        container.bind(GreetingService, mock_service)
        handler = _make_handler(UserController, "show", container)  # ty:ignore[invalid-argument-type]
        result = await handler(user_id=42)
        assert result == {"id": 42}

    @pytest.mark.asyncio
    async def test_handler_with_di_service(self):
        app = Application()
        app.singleton(GreetingService)
        app.bind(UserController)

        handler = _make_handler(UserController, "store", app)
        result = await handler(name="World")
        assert result == {"greeting": "Hello, World!"}

    def test_handler_metadata(self):
        handler = _make_handler(UserController, "index", None)
        assert handler.__controller__ is UserController  # ty:ignore[unresolved-attribute]
        assert handler.__method_name__ == "index"  # ty:ignore[unresolved-attribute]
        assert "UserController" in handler.__qualname__  # ty:ignore[unresolved-attribute]
