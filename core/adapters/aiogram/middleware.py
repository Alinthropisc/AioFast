from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject

    from ...foundation import Application

logger = logging.getLogger(__name__)


class ContainerMiddleware:
    """
    Aiogram middleware — injects IoC container into handler data.

    Every handler receives `app` and `container` in **data.
    Also resolves type-hinted dependencies automatically.

    Usage:
        dp.update.middleware(ContainerMiddleware(app))

        async def my_handler(message: Message, app: Application):
            service = await app.make(UserService)
    """

    def __init__(self, app: Application) -> None:
        self._app = app

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["app"] = self._app
        data["container"] = self._app
        return await handler(event, data)


class DependencyInjectionMiddleware:
    """
    Aiogram middleware — auto-resolves handler dependencies from container.

    Inspects handler signature and resolves type-hinted parameters.

    Usage:
        dp.update.middleware(DependencyInjectionMiddleware(app))

        async def my_handler(message: Message, user_service: UserService):
            # user_service auto-resolved from container
            users = await user_service.get_all()
    """

    def __init__(self, app: Application) -> None:
        self._app = app

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from .dependency import resolve_handler_dependencies

        data["app"] = self._app
        data["container"] = self._app

        enriched = await resolve_handler_dependencies(self._app, handler, data)
        return await handler(event, enriched)


class ScopedContainerMiddleware:
    """
    Aiogram middleware — creates a scoped container per update.

    Scoped bindings (e.g. DB session) are isolated per Telegram update.

    Usage:
        dp.update.middleware(ScopedContainerMiddleware(app))
    """

    def __init__(self, app: Application) -> None:
        self._app = app

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._app.create_scope("telegram") as scope:
            data["app"] = self._app
            data["container"] = self._app
            data["scope"] = scope
            return await handler(event, data)


class LoggingMiddleware:
    """Log all Telegram updates."""

    def __init__(self, log: Any = None) -> None:
        self._log = log

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update_type = type(event).__name__
        log = self._log or logger

        log.debug("→ Telegram update: %s", update_type)
        try:
            result = await handler(event, data)
            log.debug("← Telegram update: %s OK", update_type)
            return result
        except Exception as e:
            log.error("✗ Telegram update %s failed: %s", update_type, e)
            raise
