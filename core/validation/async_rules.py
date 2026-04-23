from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..foundation import Application


class AsyncRule(ABC):
    """
    Async validation rule — for I/O operations (DB, API, cache).

    Usage:
        class UniqueEmail(AsyncRule):
            message = "The {field} is already taken"

            async def passes_async(self, field, value):
                repo = await self.app.make(UserRepository)
                return not await repo.exists_by_email(value)

    In rules:
        v = Validator(data, {
            "email": ["required", "email", UniqueEmail()],
        })
        await v.validate_async()  # note: async!
    """

    message: str = "The {field} is invalid"

    def __init__(self) -> None:
        self.app: Application | None = None

    @abstractmethod
    async def passes_async(self, field: str, value: Any) -> bool:
        """Return True if value passes validation."""

    def get_message(self, field: str, value: Any) -> str:
        return self.message.format(field=field, value=value)

    def set_app(self, app: Application) -> None:
        self.app = app

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ── Built-in Async Rules ─────────────────────────────────


class Unique(AsyncRule):
    """
    Check that value is unique in a data source.

    Usage:
        Unique(checker=lambda v: user_repo.exists_by_email(v))
        # or with service:
        Unique(service=UserService, method="email_exists")
    """

    message = "The {field} has already been taken"

    def __init__(
        self,
        *,
        checker: Callable | None = None,
        service: type | None = None,
        method: str = "exists",
        exclude_id: Any | None = None,
    ) -> None:
        super().__init__()
        self._checker = checker
        self._service_class = service
        self._method = method
        self._exclude_id = exclude_id

    async def passes_async(self, field: str, value: Any) -> bool:
        if self._checker is not None:
            result = self._checker(value)
            if inspect.isawaitable(result):
                result = await result
            return not result

        if self._service_class is not None and self.app is not None:
            svc = await self.app.make(self._service_class)
            check_method = getattr(svc, self._method)
            exists = check_method(value)
            if inspect.isawaitable(exists):
                exists = await exists
            return not exists

        return True


class Exists(AsyncRule):
    """
    Check that value exists in a data source.

    Opposite of Unique — value MUST exist.

    Usage:
        Exists(checker=lambda v: category_repo.find(v))
    """

    message = "The selected {field} does not exist"

    def __init__(
        self, *, checker: Callable | None = None, service: type | None = None, method: str = "get_by_id"
    ) -> None:
        super().__init__()
        self._checker = checker
        self._service_class = service
        self._method = method

    async def passes_async(self, field: str, value: Any) -> bool:
        if self._checker is not None:
            result = self._checker(value)
            if inspect.isawaitable(result):
                result = await result
            return result is not None and result is not False

        if self._service_class is not None and self.app is not None:
            svc = await self.app.make(self._service_class)
            check_method = getattr(svc, self._method)
            result = check_method(value)
            if inspect.isawaitable(result):
                result = await result
            return result is not None

        return True


class AsyncCallableRule(AsyncRule):
    """Wrap an async function as a rule."""

    def __init__(self, fn: Callable, message: str = "The {field} is invalid") -> None:
        super().__init__()
        self._fn = fn
        self.message = message

    async def passes_async(self, field: str, value: Any) -> bool:
        result = self._fn(value)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)


def async_rule(fn: Callable, message: str = "The {field} is invalid") -> AsyncCallableRule:
    """Create an async rule from a function."""
    return AsyncCallableRule(fn, message)
