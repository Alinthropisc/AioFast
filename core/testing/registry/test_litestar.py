from __future__ import annotations

import pytest

litestar = pytest.importorskip("litestar")

from core.adapters.litestar import LitestarAdapter
from core.adapters.litestar.dependency import (
    _type_to_dep_name,
    build_container_dependencies,
)
from core.foundation.application import Application

# from litestar import Application
from core.registry.route import Route, RouteType


async def dummy_handler() -> dict:
    return {"ok": True}


class TestLitestarAdapter:
    @pytest.mark.asyncio
    async def test_configure(self):
        app = Application()
        adapter = LitestarAdapter()
        await adapter.configure(app, {})
        assert adapter.is_configured

    @pytest.mark.asyncio
    async def test_compile_and_start(self):
        app = Application()
        adapter = LitestarAdapter()
        await adapter.configure(app, {"debug": True})
        routes = [Route(path="/test", handler=dummy_handler, methods=["GET"])]
        adapter.compile_routes(routes)
        await adapter.start()
        assert adapter.is_started
        assert adapter.get_native_app() is not None

    @pytest.mark.asyncio
    async def test_native_handler_passthrough(self):
        from litestar import get

        @get("/native")
        async def native() -> dict:
            return {"native": True}

        app = Application()
        adapter = LitestarAdapter()
        await adapter.configure(app, {})
        adapter.add_route_handler(native)
        await adapter.start()
        assert adapter.is_started

    @pytest.mark.asyncio
    async def test_stop(self):
        app = Application()
        adapter = LitestarAdapter()
        await adapter.configure(app, {})
        await adapter.start()
        await adapter.stop()
        assert adapter.state.name == "STOPPED"

    def test_name(self):
        assert LitestarAdapter.name == "litestar"

    def test_supported_types(self):
        assert RouteType.HTTP in LitestarAdapter.supported_route_types
        assert RouteType.WEBSOCKET in LitestarAdapter.supported_route_types
        assert RouteType.BOT_COMMAND not in LitestarAdapter.supported_route_types


class TestLitestarDependency:
    def test_type_to_dep_name(self):
        class UserService:
            pass

        assert _type_to_dep_name(UserService) == "user_service"

    def test_type_to_dep_name_complex(self):
        class HTTPClientManager:
            pass

        result = _type_to_dep_name(HTTPClientManager)
        assert result == "http_client_manager"

    @pytest.mark.asyncio
    async def test_build_dependencies(self):
        class MyService:
            pass

        app = Application()
        app.singleton(MyService)
        deps = build_container_dependencies(app)
        assert "app" in deps
