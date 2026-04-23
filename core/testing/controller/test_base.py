from __future__ import annotations

from core.controller.base import Controller, ResourceController


class UserController(Controller):
    path = "/users"
    name_prefix = "users."
    tags = ["users"]
    middleware = ["auth"]


class PostController(ResourceController):
    path = "/posts"
    id_param = "post_id"
    id_type = "int"

    async def index(self):
        return []

    async def show(self, post_id: int):
        return {}

    async def store(self, data: dict):
        return {}

    async def update(self, post_id: int, data: dict):
        return {}

    async def destroy(self, post_id: int):
        return True


class PartialController(ResourceController):
    path = "/items"
    only = ["index", "show"]

    async def index(self):
        return []

    async def show(self, id: int):
        return {}


class ExcludeController(ResourceController):
    path = "/things"
    exclude = ["destroy"]

    async def index(self):
        return []

    async def show(self, id: int):
        return {}

    async def store(self, data: dict):
        return {}

    async def update(self, id: int, data: dict):
        return {}

    async def destroy(self, id: int):
        return True


class TestControllerName:
    def test_auto_name(self):
        assert UserController.controller_name() == "user"

    def test_custom_prefix(self):
        assert UserController.get_name_prefix() == "users."

    def test_auto_prefix(self):
        class ProductController(Controller):
            path = "/products"

        assert ProductController.get_name_prefix() == "product."

    def test_repr(self):
        ctrl = UserController()
        assert "UserController" in repr(ctrl)
        assert "/users" in repr(ctrl)


class TestResourceControllerMethods:
    def test_all_methods(self):
        methods = PostController.get_resource_methods()
        assert "index" in methods
        assert "show" in methods
        assert "store" in methods
        assert "update" in methods
        assert "destroy" in methods

    def test_only(self):
        methods = PartialController.get_resource_methods()
        assert "index" in methods
        assert "show" in methods
        assert "store" not in methods
        assert "destroy" not in methods

    def test_exclude(self):
        methods = ExcludeController.get_resource_methods()
        assert "index" in methods
        assert "show" in methods
        assert "store" in methods
        assert "destroy" not in methods
