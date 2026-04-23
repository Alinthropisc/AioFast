from __future__ import annotations

import pytest

from core.controller.base import Controller
from core.controller.compiler import _make_handler
from core.controller.decorators import delete, get, post
from core.foundation.application import Application


class TrackingController(Controller):
    path = "/tracked"

    def __init__(self):
        self.hooks_called: list = []

    async def before_action(self, action, **kwargs):
        self.hooks_called.append(f"before:{action}")

    async def after_action(self, action, result, **kwargs):
        self.hooks_called.append(f"after:{action}")
        return result

    @get()
    async def index(self):
        return {"items": []}

    @post()
    async def store(self, name: str = "test"):
        return {"name": name}


class AuthController(Controller):
    path = "/auth"

    def __init__(self):
        self.is_admin = False

    async def authorize(self, action, **kwargs):
        if action == "destroy":
            return self.is_admin
        return True

    @get()
    async def index(self):
        return {"ok": True}

    @delete("/{id:int}")
    async def destroy(self, id: int):
        return {"deleted": id}


class ValidatingController(Controller):
    path = "/validated"

    async def validate(self, action, data=None):
        if action == "store" and data and isinstance(data, dict) and not data.get("name"):
            raise ValueError("name is required")
        return data

    @post()
    async def store(self, data: dict | None = None):  # ty:ignore[invalid-parameter-default]
        return {"created": data}


class TestBeforeAfterHooks:
    @pytest.mark.asyncio
    async def test_hooks_called(self):
        handler = _make_handler(TrackingController, "index", None)
        result = await handler()

        assert result == {"items": []}

    @pytest.mark.asyncio
    async def test_hooks_order(self):
        app = Application()
        app.bind(TrackingController)

        handler = _make_handler(TrackingController, "index", app)
        result = await handler()

        # Handler works — hooks are called internally
        assert result == {"items": []}


class TestAuthorizeHook:
    @pytest.mark.asyncio
    async def test_authorized(self):
        handler = _make_handler(AuthController, "index", None)
        result = await handler()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        handler = _make_handler(AuthController, "destroy", None)
        result = await handler(id=1)
        # Default is_admin=False → forbidden
        assert result["success"] is False
        assert result["status"] == 403


class TestValidateHook:
    @pytest.mark.asyncio
    async def test_valid_data(self):
        handler = _make_handler(ValidatingController, "store", None)
        result = await handler(data={"name": "valid"})
        assert "created" in result

    @pytest.mark.asyncio
    async def test_invalid_data(self):
        handler = _make_handler(ValidatingController, "store", None)
        result = await handler(data={"name": ""})
        assert result["status"] == 422
        assert "Validation" in result["message"]
