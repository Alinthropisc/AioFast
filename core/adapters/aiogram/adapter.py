from __future__ import annotations

import contextlib
import logging
import os
from typing import TYPE_CHECKING, Any

from ...registry.adapter import AdapterState, BaseAdapter
from ...registry.route import Route, RouteType

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogram import Bot, Dispatcher, Router

    from ...foundation.application import Application

logger = logging.getLogger(__name__)


class AiogramAdapter(BaseAdapter):
    """
    Bridges AIoFast with Aiogram v3.

    - Compiles Route definitions → Aiogram router registrations
    - Bridges DI: Container → middleware data injection
    - Creates Bot + Dispatcher
    - Manages lifecycle (polling / webhook)
    """

    name = "aiogram"
    supported_route_types = {
        RouteType.BOT_COMMAND,
        RouteType.BOT_MESSAGE,
        RouteType.BOT_CALLBACK,
    }

    def __init__(self) -> None:
        super().__init__()
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._router: Router | None = None
        self._native_routers: list[Router] = []
        self._middleware: list[Any] = []
        self._on_startup: list[Callable] = []
        self._on_shutdown: list[Callable] = []

    async def configure(self, app: Application, config: dict[str, Any]) -> None:
        try:
            from aiogram import Bot, Dispatcher, Router
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
        except ImportError:
            raise ImportError(
                "aiogram is required for AiogramAdapter. Install: pip install aiogram or use uv, uv add aiogram"
            )

        token = config.get("token") or os.getenv("BOT_TOKEN", "")
        if not token:
            logger.warning("Bot token not provided — Aiogram adapter inactive")
            self._state = AdapterState.ERROR
            return
        parse_mode = config.get("parse_mode", ParseMode.HTML)
        self._bot = Bot(token=token, default=DefaultBotProperties(parse_mode=parse_mode))
        self._dispatcher = Dispatcher()
        self._router = Router(name="aiofast")
        # Store in container
        app.instance(Bot, self._bot)
        app.instance(Dispatcher, self._dispatcher)
        app.instance("bot", self._bot)
        app.instance("dispatcher", self._dispatcher)
        self._app = app
        self._state = AdapterState.CONFIGURED

    def compile_routes(self, routes: list[Route]) -> None:
        if self._router is None:
            return

        from aiogram.filters import Command

        for route_def in routes:
            handler = route_def.handler
            if handler is None:
                continue

            if route_def.route_type == RouteType.BOT_COMMAND:
                cmd = route_def.path.lstrip("/")
                self._router.message.register(handler, Command(cmd))
                logger.debug("Bot command: /%s → %s", cmd, handler)

            elif route_def.route_type == RouteType.BOT_MESSAGE:
                filters = route_def.meta.get("filters")
                if filters:
                    self._router.message.register(handler, filters)
                else:
                    self._router.message.register(handler)
                logger.debug("Bot message handler: %s", handler)

            elif route_def.route_type == RouteType.BOT_CALLBACK:
                filters = route_def.meta.get("filters")
                if filters:
                    self._router.callback_query.register(handler, filters)
                else:
                    self._router.callback_query.register(handler)
                logger.debug("Bot callback handler: %s", handler)

    async def start(self) -> None:
        if self._dispatcher is None or self._bot is None:
            return

        from .middleware import ContainerMiddleware

        # Add container middleware
        self._dispatcher.update.middleware(ContainerMiddleware(self._app))  # ty:ignore[invalid-argument-type]

        # Add custom middleware
        for mw in self._middleware:
            self._dispatcher.update.middleware(mw)

        # Include routers
        if self._router:
            self._dispatcher.include_router(self._router)

        for router in self._native_routers:
            self._dispatcher.include_router(router)

        # Startup hooks
        for hook in self._on_startup:
            self._dispatcher.startup.register(hook)

        # Shutdown hooks
        for hook in self._on_shutdown:
            self._dispatcher.shutdown.register(hook)

        self._state = AdapterState.STARTED
        logger.info("Aiogram adapter started")

    async def stop(self) -> None:
        if self._bot:
            with contextlib.suppress(Exception):
                await self._bot.session.close()
        self._state = AdapterState.STOPPED

    def get_native_app(self) -> Dispatcher | None:
        return self._dispatcher

    async def start_polling(self, **kwargs: Any) -> None:
        """Start long polling (blocking)."""
        if self._dispatcher is None or self._bot is None:
            raise RuntimeError("Aiogram not configured")
        await self._dispatcher.start_polling(self._bot, **kwargs)

    async def set_webhook(self, url: str, **kwargs: Any) -> None:
        """Set webhook for the bot."""
        if self._bot is None:
            raise RuntimeError("Aiogram not configured")
        await self._bot.set_webhook(url, **kwargs)

    def add_router(self, router: Router) -> AiogramAdapter:
        """Add a native Aiogram router."""
        self._native_routers.append(router)
        return self

    def add_middleware(self, middleware: Any) -> AiogramAdapter:
        self._middleware.append(middleware)
        return self

    def on_startup(self, handler: Callable) -> AiogramAdapter:
        self._on_startup.append(handler)
        return self

    def on_shutdown(self, handler: Callable) -> AiogramAdapter:
        self._on_shutdown.append(handler)
        return self

    @property
    def bot(self) -> Bot | None:
        return self._bot

    @property
    def dispatcher(self) -> Dispatcher | None:
        return self._dispatcher
