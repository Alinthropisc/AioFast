from __future__ import annotations

from core.controller.decorators import (
    delete,
    get,
    get_route_meta,
    has_route_meta,
    middleware,
    patch,
    post,
    put,
)


class TestRouteDecorators:
    def test_get(self):
        @get("/users")
        async def handler():
            pass

        assert has_route_meta(handler)
        meta = get_route_meta(handler)
        assert meta["methods"] == ["GET"]  # ty:ignore[not-subscriptable]
        assert meta["path"] == "/users"  # ty:ignore[not-subscriptable]

    def test_post(self):
        @post("/users")
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["methods"] == ["POST"]  # ty:ignore[not-subscriptable]

    def test_put(self):
        @put("/users/{id}")
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["methods"] == ["PUT"]  # ty:ignore[not-subscriptable]
        assert meta["path"] == "/users/{id}"  # ty:ignore[not-subscriptable]

    def test_patch(self):
        @patch()
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["methods"] == ["PATCH"]  # ty:ignore[not-subscriptable]
        assert meta["path"] == ""  # ty:ignore[not-subscriptable]

    def test_delete(self):
        @delete("/{id}")
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["methods"] == ["DELETE"]  # ty:ignore[not-subscriptable]

    def test_with_name(self):
        @get("/", name="home")
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["name"] == "home"  # ty:ignore[not-subscriptable]

    def test_with_middleware(self):
        @get("/", middleware=["auth", "throttle"])
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["middleware"] == ["auth", "throttle"]  # ty:ignore[not-subscriptable]

    def test_with_tags(self):
        @get("/", tags=["users", "public"])
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert meta["tags"] == ["users", "public"]  # ty:ignore[not-subscriptable]

    def test_no_meta(self):
        async def plain():
            pass

        assert has_route_meta(plain) is False
        assert get_route_meta(plain) is None

    def test_middleware_decorator_on_route(self):
        @middleware("auth", "admin")
        @get("/admin")
        async def handler():
            pass

        meta = get_route_meta(handler)
        assert "auth" in meta["middleware"]  # ty:ignore[not-subscriptable]
        assert "admin" in meta["middleware"]  # ty:ignore[not-subscriptable]
