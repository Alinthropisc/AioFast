from __future__ import annotations

import pytest

from core.foundation import Application
from core.registry import AdapterManager, AdapterState, BaseAdapter, Route, RouteCollector, RouteType

# ── Mock adapter ──────────────────────────────────────────


class MockAdapter(BaseAdapter):
    name = "mock"
    supported_route_types = {RouteType.HTTP}

    def __init__(self) -> None:
        super().__init__()
        self.compiled_routes: list[Route] = []
        self.started = False
        self.stopped = False

    async def configure(self, app, config):
        self._app = app
        self._config = config
        self._state = AdapterState.CONFIGURED

    async def start(self):
        self.started = True
        self._state = AdapterState.STARTED

    async def stop(self):
        self.stopped = True
        self._state = AdapterState.STOPPED

    def compile_routes(self, routes):
        self.compiled_routes = list(routes)

    def get_native_app(self):
        return "mock_app"


class MockBotAdapter(BaseAdapter):
    name = "mock_bot"
    supported_route_types = {RouteType.BOT_COMMAND, RouteType.BOT_MESSAGE}

    def __init__(self):
        super().__init__()
        self.compiled_routes = []

    async def configure(self, app, config):
        self._state = AdapterState.CONFIGURED

    async def start(self):
        self._state = AdapterState.STARTED

    async def stop(self):
        self._state = AdapterState.STOPPED

    def compile_routes(self, routes):
        self.compiled_routes = list(routes)

    def get_native_app(self):
        return "mock_bot_dispatcher"


async def dummy():
    pass


# ── Tests ─────────────────────────────────────────────────


class TestAdapterManagerRegistration:
    def test_register(self):
        mgr = AdapterManager()
        adapter = MockAdapter()
        mgr.register(adapter)
        assert mgr.has("mock")

    def test_register_no_name_raises(self):
        mgr = AdapterManager()

        class NoName(BaseAdapter):
            name = ""
            supported_route_types = set()

            async def configure(self, app, config):
                pass

            async def start(self):
                pass

            async def stop(self):
                pass

            def compile_routes(self, routes):
                pass

        with pytest.raises(ValueError, match="no name"):
            mgr.register(NoName())

    def test_get(self):
        mgr = AdapterManager()
        adapter = MockAdapter()
        mgr.register(adapter)
        assert mgr.get("mock") is adapter

    def test_get_missing_raises(self):
        mgr = AdapterManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.get("nonexistent")

    def test_has(self):
        mgr = AdapterManager()
        assert mgr.has("mock") is False
        mgr.register(MockAdapter())
        assert mgr.has("mock") is True

    def test_adapter_names(self):
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        mgr.register(MockBotAdapter())
        assert set(mgr.adapter_names) == {"mock", "mock_bot"}


class TestAdapterManagerRoutes:
    def test_add_routes(self):
        mgr = AdapterManager()
        c = RouteCollector()
        c.get("/test", dummy)
        mgr.add_routes(c)
        assert len(mgr.all_routes()) == 1

    def test_routes_for_adapter(self):
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        mgr.register(MockBotAdapter())

        c = RouteCollector()
        c.get("/users", dummy)
        c.command("/start", dummy)
        mgr.add_routes(c)

        http_routes = mgr.routes_for("mock")
        assert len(http_routes) == 1
        assert http_routes[0].route_type == RouteType.HTTP

        bot_routes = mgr.routes_for("mock_bot")
        assert len(bot_routes) == 1
        assert bot_routes[0].route_type == RouteType.BOT_COMMAND


class TestAdapterManagerLifecycle:
    @pytest.mark.asyncio
    async def test_configure(self):
        app = Application()
        mgr = AdapterManager()
        adapter = MockAdapter()
        mgr.register(adapter)

        await mgr.configure(app)
        assert mgr.is_configured
        assert adapter.state == AdapterState.CONFIGURED

    @pytest.mark.asyncio
    async def test_start(self):
        app = Application()
        mgr = AdapterManager()
        adapter = MockAdapter()
        mgr.register(adapter)

        c = RouteCollector()
        c.get("/test", dummy)
        mgr.add_routes(c)

        await mgr.configure(app)
        await mgr.start()
        assert mgr.is_started
        assert adapter.started
        assert len(adapter.compiled_routes) == 1

    @pytest.mark.asyncio
    async def test_start_without_configure_raises(self):
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        with pytest.raises(RuntimeError, match="not configured"):
            await mgr.start()

    @pytest.mark.asyncio
    async def test_stop(self):
        app = Application()
        mgr = AdapterManager()
        adapter = MockAdapter()
        mgr.register(adapter)

        await mgr.configure(app)
        await mgr.start()
        await mgr.stop()
        assert adapter.stopped
        assert not mgr.is_started

    @pytest.mark.asyncio
    async def test_route_distribution(self):
        app = Application()
        mgr = AdapterManager()

        http_adapter = MockAdapter()
        bot_adapter = MockBotAdapter()
        mgr.register(http_adapter)
        mgr.register(bot_adapter)

        c = RouteCollector()
        c.get("/api/users", dummy)
        c.post("/api/users", dummy)
        c.command("/start", dummy)
        c.command("/help", dummy)
        c.on_message(dummy)
        mgr.add_routes(c)

        await mgr.configure(app)
        await mgr.start()

        assert len(http_adapter.compiled_routes) == 2
        assert len(bot_adapter.compiled_routes) == 3


class TestAdapterManagerHelpers:
    @pytest.mark.asyncio
    async def test_get_asgi_app(self):
        app = Application()
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        await mgr.configure(app)
        await mgr.start()
        assert mgr.get_asgi_app() == "mock_app"

    @pytest.mark.asyncio
    async def test_get_bot_dispatcher(self):
        app = Application()
        mgr = AdapterManager()
        mgr.register(MockBotAdapter())
        await mgr.configure(app)
        await mgr.start()
        assert mgr.get_bot_dispatcher() == "mock_bot_dispatcher"

    def test_repr(self):
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        r = repr(mgr)
        assert "AdapterManager" in r
        assert "mock" in r


class TestAdapterManagerLoadModule:
    def test_load_module_with_register(self):
        import types

        module = types.ModuleType("test_routes")

        def register(routes: RouteCollector):
            routes.get("/from-module", dummy)

        module.register = register  # ty:ignore[unresolved-attribute]
        mgr = AdapterManager()
        mgr.load_route_module(module)
        assert len(mgr.all_routes()) == 1

    def test_load_module_with_routes_attr(self):
        import types

        module = types.ModuleType("test_routes")
        c = RouteCollector()
        c.get("/from-attr", dummy)
        module.routes = c  # ty:ignore[unresolved-attribute]

        mgr = AdapterManager()
        mgr.load_route_module(module)
        assert len(mgr.all_routes()) == 1

    def test_load_module_invalid(self):
        import types

        module = types.ModuleType("empty")

        mgr = AdapterManager()
        with pytest.raises(ValueError, match="no 'register'"):
            mgr.load_route_module(module)
