from __future__ import annotations

from core.registry import (
    RateLimit,
    Route,
    RouteCollector,
    RouteType,
    route,
)

# ── dummy handlers ────────────────────────────────────────


async def home():
    return "home"


async def list_users():
    return "users"


async def create_user():
    return "created"


async def show_user():
    return "user"


async def update_user():
    return "updated"


async def delete_user():
    return "deleted"


async def start_cmd():
    return "start"


async def help_cmd():
    return "help"


async def on_msg():
    return "msg"


async def on_cb():
    return "cb"


class TestRouteDataclass:
    def test_defaults(self):
        r = Route(path="/test", handler=home)
        assert r.methods == ["GET"]
        assert r.route_type == RouteType.HTTP
        assert r.name is None
        assert r.middleware == []

    def test_full_name(self):
        r = Route(path="/test", handler=home, name="test.route")
        assert r.full_name == "test.route"

    def test_full_name_auto(self):
        r = Route(path="/test", handler=home, methods=["POST"])
        assert r.full_name == "post:/test"

    def test_repr(self):
        r = Route(path="/test", handler=home)
        assert "/test" in repr(r)
        assert "home" in repr(r)

    def test_rate_limit(self):
        rl = RateLimit(max_requests=100, window_seconds=30)
        r = Route(path="/", handler=home, rate_limit=rl)
        assert r.rate_limit.max_requests == 100  # ty:ignore[unresolved-attribute]


class TestRouteCollectorBasic:
    def test_get(self):
        c = RouteCollector()
        c.get("/users", list_users)
        routes = c.collect()
        assert len(routes) == 1
        assert routes[0].methods == ["GET"]
        assert routes[0].path == "/users"

    def test_post(self):
        c = RouteCollector()
        c.post("/users", create_user)
        assert c.collect()[0].methods == ["POST"]

    def test_put(self):
        c = RouteCollector()
        c.put("/users/1", update_user)
        assert c.collect()[0].methods == ["PUT"]

    def test_patch(self):
        c = RouteCollector()
        c.patch("/users/1", update_user)
        assert c.collect()[0].methods == ["PATCH"]

    def test_delete(self):
        c = RouteCollector()
        c.delete("/users/1", delete_user)
        assert c.collect()[0].methods == ["DELETE"]

    def test_any(self):
        c = RouteCollector()
        c.any("/wildcard", home)
        r = c.collect()[0]
        assert "GET" in r.methods
        assert "POST" in r.methods
        assert "DELETE" in r.methods

    def test_match(self):
        c = RouteCollector()
        c.match(["GET", "POST"], "/both", home)
        r = c.collect()[0]
        assert r.methods == ["GET", "POST"]

    def test_named_route(self):
        c = RouteCollector()
        c.get("/users", list_users, name="users.index")
        assert c.collect()[0].name == "users.index"

    def test_middleware_on_route(self):
        c = RouteCollector()
        c.get("/admin", home, middleware=["auth"])
        assert c.collect()[0].middleware == ["auth"]

    def test_len(self):
        c = RouteCollector()
        c.get("/a", home)
        c.post("/b", home)
        assert len(c) == 2

    def test_iter(self):
        c = RouteCollector()
        c.get("/a", home)
        c.get("/b", home)
        routes = list(c)
        assert len(routes) == 2

    def test_find(self):
        c = RouteCollector()
        c.get("/a", home, name="route.a")
        c.get("/b", home, name="route.b")
        found = c.find("route.b")
        assert found is not None
        assert found.path == "/b"

    def test_find_missing(self):
        c = RouteCollector()
        assert c.find("nonexistent") is None

    def test_clear(self):
        c = RouteCollector()
        c.get("/a", home)
        c.clear()
        assert len(c) == 0

    def test_repr(self):
        c = RouteCollector()
        c.get("/", home)
        assert "RouteCollector" in repr(c)


class TestRouteCollectorContextManager:
    def test_with_statement(self):
        c = RouteCollector()
        with c as r:
            r.get("/", home)
            r.post("/submit", create_user)
        assert len(c) == 2


class TestRouteCollectorGroup:
    def test_group_prefix(self):
        c = RouteCollector()
        with c.group(prefix="/api") as r:
            r.get("/users", list_users)
        routes = c.collect()
        assert routes[0].path == "/api/users"

    def test_group_middleware(self):
        c = RouteCollector()
        with c.group(middleware=["auth"]) as r:
            r.get("/admin", home)
        assert c.collect()[0].middleware == ["auth"]

    def test_group_name_prefix(self):
        c = RouteCollector()
        with c.group(name="api.") as r:
            r.get("/users", list_users, name="users.index")
        assert c.collect()[0].name == "api.users.index"

    def test_nested_groups(self):
        c = RouteCollector()
        with c.group(prefix="/api") as r:
            r.get("/root", home)  # /api/root

            with r.group(prefix="/v1") as r:
                r.get("/users", list_users)  # /api/v1/users

                with r.group(prefix="/admin", middleware=["admin"]) as r:
                    r.get("/stats", home)  # /api/v1/admin/stats

            # Back to /api scope
            r.get("/health", home)  # /api/health

        routes = c.collect()
        assert len(routes) == 4
        assert routes[0].path == "/api/root"
        assert routes[1].path == "/api/v1/users"
        assert routes[2].path == "/api/v1/admin/stats"
        assert routes[2].middleware == ["admin"]
        assert routes[3].path == "/api/health"
        assert routes[3].middleware == []  # no admin middleware

    def test_nested_middleware_stacks(self):
        c = RouteCollector()
        with c.group(middleware=["global"]) as r:
            r.get("/public", home)

            with r.group(middleware=["auth"]) as r:
                r.get("/protected", home)

                with r.group(middleware=["admin"]) as r:
                    r.get("/admin", home)

        routes = c.collect()
        assert routes[0].middleware == ["global"]
        assert routes[1].middleware == ["global", "auth"]
        assert routes[2].middleware == ["global", "auth", "admin"]

    def test_nested_name_prefixes(self):
        c = RouteCollector()
        with c.group(name="api.") as r, r.group(name="v1.") as r:
            r.get("/users", list_users, name="users")
        assert c.collect()[0].name == "api.v1.users"

    def test_prefix_shorthand(self):
        c = RouteCollector()
        with c.prefix("/api/v1") as r:
            r.get("/users", list_users)
        assert c.collect()[0].path == "/api/v1/users"

    def test_middleware_group_shorthand(self):
        c = RouteCollector()
        with c.middleware_group("auth", "throttle") as r:
            r.get("/admin", home)
        assert c.collect()[0].middleware == ["auth", "throttle"]


class TestRouteCollectorBot:
    def test_command(self):
        c = RouteCollector()
        c.command("/start", start_cmd)
        r = c.collect()[0]
        assert r.route_type == RouteType.BOT_COMMAND
        assert r.path == "/start"

    def test_on_message(self):
        c = RouteCollector()
        c.on_message(on_msg, filters="text_filter")
        r = c.collect()[0]
        assert r.route_type == RouteType.BOT_MESSAGE
        assert r.meta["filters"] == "text_filter"

    def test_on_callback(self):
        c = RouteCollector()
        c.on_callback(on_cb, filters="cb_filter")
        r = c.collect()[0]
        assert r.route_type == RouteType.BOT_CALLBACK
        assert r.meta["filters"] == "cb_filter"


class TestRouteCollectorWebsocket:
    def test_websocket(self):
        c = RouteCollector()
        c.websocket("/ws", home)
        r = c.collect()[0]
        assert r.route_type == RouteType.WEBSOCKET
        assert r.path == "/ws"


class TestRouteCollectorResource:
    def test_resource(self):
        class UserController:
            async def index(self):
                pass

            async def store(self):
                pass

            async def show(self):
                pass

            async def update(self):
                pass

            async def destroy(self):
                pass

            def get_name_prefix(self):
                return "user"

        c = RouteCollector()
        routes = c.resource("/users", UserController())
        assert len(routes) >= 5

        paths = [r.path for r in routes]
        assert "/users" in paths
        assert "/users/{id}" in paths

        methods = {r.methods[0] for r in routes}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods


class TestRouteCollectorCollectByType:
    def test_collect_by_type(self):
        c = RouteCollector()
        c.get("/users", list_users)
        c.post("/users", create_user)
        c.command("/start", start_cmd)

        http_routes = c.collect_by_type(RouteType.HTTP)
        assert len(http_routes) == 2

        bot_routes = c.collect_by_type(RouteType.BOT_COMMAND)
        assert len(bot_routes) == 1


class TestRouteFactory:
    def test_route_factory(self):
        r = route()
        assert isinstance(r, RouteCollector)
        assert len(r) == 0

    def test_route_factory_usage(self):
        r = route()
        with r as routes:
            routes.get("/", home)
        assert len(r) == 1
