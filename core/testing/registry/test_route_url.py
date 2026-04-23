from __future__ import annotations

import pytest

from core.registry import Route, RouteURLGenerator


class TestRouteURLGenerator:
    def setup_method(self):
        self.routes = [
            Route(path="/", handler=None, name="home"),
            Route(path="/users", handler=None, name="users.index"),
            Route(path="/users/{id}", handler=None, name="users.show"),
            Route(path="/users/{id}/posts/{post_id}", handler=None, name="users.posts"),
            Route(path="/users/{id:int}", handler=None, name="users.typed"),
        ]
        self.gen = RouteURLGenerator(self.routes)

    def test_simple(self):
        assert self.gen.generate("home") == "/"
        assert self.gen.generate("users.index") == "/users"

    def test_with_param(self):
        url = self.gen.generate("users.show", id=42)
        assert url == "/users/42"

    def test_multiple_params(self):
        url = self.gen.generate("users.posts", id=1, post_id=5)
        assert url == "/users/1/posts/5"

    def test_typed_param(self):
        url = self.gen.generate("users.typed", id=99)
        assert url == "/users/99"

    def test_missing_route(self):
        with pytest.raises(KeyError, match="not found"):
            self.gen.generate("nonexistent")

    def test_has(self):
        assert self.gen.has("home") is True
        assert self.gen.has("missing") is False

    def test_names(self):
        names = self.gen.names()
        assert "home" in names
        assert "users.index" in names

    def test_repr(self):
        r = repr(self.gen)
        assert "RouteURLGenerator" in r
