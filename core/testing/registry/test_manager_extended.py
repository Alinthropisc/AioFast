from __future__ import annotations

import pytest

from core.foundation.application import Application
from core.registry.adapter import AdapterState, BaseAdapter
from core.registry.health import HealthStatus
from core.registry.manager import AdapterManager
from core.registry.route import RouteCollector, RouteType


class MockAdapter(BaseAdapter):
    name = "mock"
    supported_route_types = {RouteType.HTTP}

    async def configure(self, app, config):
        self._state = AdapterState.CONFIGURED

    async def start(self):
        self.mark_started()

    async def stop(self):
        self.mark_stopped()

    def compile_routes(self, routes):
        self._route_count = len(routes)


async def dummy():
    pass


class TestAdapterManagerHealth:
    _route_count = 0  # или нужное значение

    @pytest.mark.asyncio
    async def test_health_all_healthy(self):
        app = Application()
        mgr = AdapterManager()
        mgr.register(MockAdapter())

        await mgr.configure(app)
        await mgr.start()

        health = await mgr.health()
        assert health.status == HealthStatus.HEALTHY
        assert len(health.checks) == 1

    @pytest.mark.asyncio
    async def test_health_includes_version(self):
        app = Application()
        mgr = AdapterManager()
        mgr.register(MockAdapter())
        await mgr.configure(app)
        await mgr.start()

        health = await mgr.health()
        assert health.version != ""


class TestAdapterManagerURL:
    def test_url_generation(self):
        mgr = AdapterManager()
        c = RouteCollector()
        c.get("/users/{id}", dummy, name="users.show")
        mgr.add_routes(c)

        url = mgr.url("users.show", id=42)
        assert url == "/users/42"

    def test_urls_property(self):
        mgr = AdapterManager()
        c = RouteCollector()
        c.get("/", dummy, name="home")
        mgr.add_routes(c)

        assert mgr.urls.has("home")


class TestAdapterManagerRouteTable:
    def test_route_table(self):
        mgr = AdapterManager()
        c = RouteCollector()
        c.get("/users", dummy, name="users.index")
        c.post("/users", dummy, name="users.store")
        c.command("/start", dummy, name="bot.start")
        mgr.add_routes(c)

        table = mgr.route_table()
        assert len(table) == 3
        assert table[0]["path"] == "/users"
        assert table[0]["methods"] == "GET"
        assert table[0]["name"] == "users.index"

    def test_print_routes(self, capsys):
        mgr = AdapterManager()
        c = RouteCollector()
        c.get("/", dummy, name="home")
        mgr.add_routes(c)

        mgr.print_routes()
        captured = capsys.readouterr()
        assert "home" in captured.out
        assert "/" in captured.out

    def test_print_routes_empty(self, capsys):
        mgr = AdapterManager()
        mgr.print_routes()
        captured = capsys.readouterr()
        assert "No routes" in captured.out


class TestAdapterManagerGlobalMiddleware:
    def test_add_global_middleware(self):
        mgr = AdapterManager()

        class MW1:
            pass

        class MW2:
            pass

        mgr.add_global_middleware(MW1, priority=10)
        mgr.add_global_middleware(MW2, priority=5)

        mw_list = mgr.global_middleware
        assert len(mw_list) == 2
        # Sorted by priority (lower first)
        assert mw_list[0].middleware is MW2
        assert mw_list[1].middleware is MW1
