from __future__ import annotations

import os

import pytest

aiogram = pytest.importorskip("aiogram")

from core.adapters.aiogram.adapter import AiogramAdapter
from core.adapters.aiogram.dependency import resolve_handler_dependencies
from core.adapters.aiogram.middleware import ContainerMiddleware
from core.foundation.application import Application
from core.registry.route import RouteType


class UserService:
    pass


class TestAiogramAdapterConfigure:
    @pytest.mark.asyncio
    async def test_configure_with_token(self):
        app = Application()
        adapter = AiogramAdapter()
        await adapter.configure(app, {"token": "123:ABC"})
        assert adapter.is_configured
        assert adapter.bot is not None
        assert adapter.dispatcher is not None

    @pytest.mark.asyncio
    async def test_configure_without_token(self):
        app = Application()
        adapter = AiogramAdapter()
        # Remove BOT_TOKEN if set
        old = os.environ.pop("BOT_TOKEN", None)
        try:
            await adapter.configure(app, {})
            # Should set state to ERROR (no token)
            assert adapter.state.name == "ERROR"
        finally:
            if old:
                os.environ["BOT_TOKEN"] = old

    def test_name(self):
        assert AiogramAdapter.name == "aiogram"

    def test_supported_types(self):
        assert RouteType.BOT_COMMAND in AiogramAdapter.supported_route_types
        assert RouteType.BOT_MESSAGE in AiogramAdapter.supported_route_types
        assert RouteType.BOT_CALLBACK in AiogramAdapter.supported_route_types
        assert RouteType.HTTP not in AiogramAdapter.supported_route_types


class TestAiogramMiddleware:
    @pytest.mark.asyncio
    async def test_container_middleware_injects_app(self):
        app = Application()
        mw = ContainerMiddleware(app)
        received_data = {}

        async def handler(event, data):
            received_data.update(data)

        # Simple test with mock
        await mw(handler, None, {"existing": "data"})  # ty:ignore[invalid-argument-type]
        assert received_data["app"] is app
        assert received_data["container"] is app
        assert received_data["existing"] == "data"


class TestAiogramDependencyResolution:
    @pytest.mark.asyncio
    async def test_resolve_dependencies(self):
        app = Application()
        svc = UserService()
        app.instance(UserService, svc)

        async def handler(user_service: UserService) -> None:
            pass

        result = await resolve_handler_dependencies(app, handler, {})
        assert result["user_service"] is svc

    @pytest.mark.asyncio
    async def test_existing_data_preserved(self):
        app = Application()

        async def handler(x: int) -> None:
            pass

        result = await resolve_handler_dependencies(app, handler, {"x": 42})
        assert result["x"] == 42
