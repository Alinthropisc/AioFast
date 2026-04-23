from __future__ import annotations

import re
from typing import Any, ClassVar


class Controller:
    """
    Base controller — decorator-based routing.

    Methods decorated with @get, @post, etc. become route handlers.
    Dependencies are injected via __init__ from the container.

    Usage:
        class UserController(Controller):
            path = "/users"
            name_prefix = "users."
            tags = ["users"]
            middleware = ["auth"]

            def __init__(self, service: UserService):
                self.service = service

            @get()
            async def index(self) -> list:
                return await self.service.get_all()

            @get("/{user_id:int}")
            async def show(self, user_id: int) -> dict:
                return await self.service.get_by_id(user_id)

            @post()
            async def store(self, data: CreateUserDTO) -> dict:
                return await self.service.create(data)

            @put("/{user_id:int}")
            async def update(self, user_id: int, data: UpdateUserDTO) -> dict:
                return await self.service.update(user_id, data)

            @delete("/{user_id:int}")
            async def destroy(self, user_id: int) -> None:
                await self.service.delete(user_id)
    """

    path: ClassVar[str] = ""
    name_prefix: ClassVar[str] = ""
    tags: ClassVar[list[str]] = []
    middleware: ClassVar[list[Any]] = []

    @classmethod
    def controller_name(cls) -> str:
        """Auto-generate name from class: UserController → user."""
        name = cls.__name__
        for suffix in ("Controller", "Ctrl"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @classmethod
    def get_name_prefix(cls) -> str:
        """Get name prefix for routes."""
        if cls.name_prefix:
            return cls.name_prefix
        return f"{cls.controller_name()}."

    # ── lifecycle hooks ───────────────────────────────────

    async def before_action(self, action: str, **kwargs: Any) -> None:
        """
        Called before every controller action.

        Override to add setup logic (load user, log, etc.)

        Args:
            action: method name being called (e.g. "index", "show")
            **kwargs: route parameters
        """
        pass

    async def after_action(self, action: str, result: Any, **kwargs: Any) -> Any:
        """
        Called after every controller action.

        Override to modify response, log, clean up, etc.
        Return the (possibly modified) result.

        Args:
            action: method name that was called
            result: return value of the action
            **kwargs: route parameters
        """
        return result

    async def authorize(self, action: str, **kwargs: Any) -> bool:
        """
        Authorization check — runs before the action.

        Override to implement access control.
        Return False → 403 Forbidden response.
        Raise exception → custom error handling.

        Args:
            action: method name (e.g. "destroy", "update")
            **kwargs: route parameters (e.g. user_id=1)
        """
        return True

    async def validate(self, action: str, data: Any = None) -> Any:
        """
        Validation hook — runs before create/update actions.

        Override to validate input data.
        Return validated/cleaned data.
        Raise ValueError/ValidationError for invalid input.

        Args:
            action: method name
            data: input data (body, form, etc.)
        """
        return data

    # ── response helpers ──────────────────────────────────

    def ok(self, data: Any = None, message: str = "Success") -> dict[str, Any]:
        """200 OK response."""
        result: dict[str, Any] = {"success": True, "message": message, "status": 200}
        if data is not None:
            result["data"] = data
        return result

    def created(self, data: Any = None) -> dict[str, Any]:
        """201 Created response."""
        result: dict[str, Any] = {"success": True, "message": "Created", "status": 201}
        if data is not None:
            result["data"] = data
        return result

    def no_content(self) -> dict[str, Any]:
        """204 No Content response."""
        return {"success": True, "status": 204}

    def not_found(self, resource: str = "") -> dict[str, Any]:
        """404 Not Found response."""
        msg = f"{resource} not found" if resource else "Not Found"
        return {"success": False, "message": msg, "status": 404}

    def forbidden(self, message: str = "Forbidden") -> dict[str, Any]:
        """403 Forbidden response."""
        return {"success": False, "message": message, "status": 403}

    def error(self, message: str = "Error", status: int = 400, errors: Any = None) -> dict[str, Any]:
        """Error response."""
        result: dict[str, Any] = {
            "success": False,
            "message": message,
            "status": status,
        }
        if errors is not None:
            result["errors"] = errors
        return result

    # ── naming ────────────────────────────────────────────

    @classmethod
    def controller_name(cls) -> str:
        name = cls.__name__
        for suffix in ("Controller", "Ctrl"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @classmethod
    def get_name_prefix(cls) -> str:
        if cls.name_prefix:
            return cls.name_prefix
        return f"{cls.controller_name()}."

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} path={self.path!r}>"


class ResourceController(Controller):
    """
    Resource controller — convention-based CRUD routing.

    Just define methods with standard names — routes are generated automatically.

    Methods → Routes:
        index()              → GET    /path
        show(id)             → GET    /path/{id}
        store(data)          → POST   /path
        update(id, data)     → PUT    /path/{id}
        destroy(id)          → DELETE /path/{id}

    Optional extra methods:
        create()             → GET    /path/create  (form page)
        edit(id)             → GET    /path/{id}/edit (form page)

    Usage:
        class PostController(ResourceController):
            path = "/posts"
            id_param = "post_id"     # default: "id"
            id_type = "int"          # default: "int"

            def __init__(self, service: PostService):
                self.service = service

            async def index(self) -> list:
                return await self.service.get_all()

            async def show(self, post_id: int) -> dict:
                return await self.service.get_by_id(post_id)

            async def store(self, data: dict) -> dict:
                return await self.service.create(data)

            async def update(self, post_id: int, data: dict) -> dict:
                return await self.service.update(post_id, data)

            async def destroy(self, post_id: int) -> None:
                await self.service.delete(post_id)
    """

    id_param: ClassVar[str] = "id"
    id_type: ClassVar[str] = "int"
    only: ClassVar[list[str] | None] = None
    exclude: ClassVar[list[str] | None] = None

    # Standard CRUD method → (HTTP method, path suffix, name suffix)
    RESOURCE_MAP: ClassVar[dict[str, tuple]] = {
        "index": ("GET", "", "index"),
        "create": ("GET", "/create", "create"),
        "store": ("POST", "", "store"),
        "show": ("GET", "/{id_param}", "show"),
        "edit": ("GET", "/{id_param}/edit", "edit"),
        "update": ("PUT", "/{id_param}", "update"),
        "destroy": ("DELETE", "/{id_param}", "destroy"),
    }

    @classmethod
    def get_resource_methods(cls) -> list[str]:
        """Get list of CRUD methods this controller implements."""
        available = []
        for method_name in cls.RESOURCE_MAP:
            if cls.only and method_name not in cls.only:
                continue
            if cls.exclude and method_name in cls.exclude:
                continue
            # Check if method is actually defined (not just inherited stub)
            method = getattr(cls, method_name, None)
            if method is not None and callable(method):
                # Skip if it's just the base class raising NotImplementedError
                if not _is_abstract_method(method):
                    available.append(method_name)
        return available


def _is_abstract_method(method: Any) -> bool:
    """Check if method just raises NotImplementedError."""
    import inspect

    try:
        source = inspect.getsource(method)
        return "raise NotImplementedError" in source and source.count("\n") <= 3
    except (OSError, TypeError):
        return False
