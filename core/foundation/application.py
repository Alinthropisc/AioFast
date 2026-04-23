from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
)

from .container import Container
from .platform import LoopType, Platform, PlatformInfo

if TYPE_CHECKING:
    from .service_provider import ServiceProvider

logger = logging.getLogger(__name__)

ResponseHandler = Callable[[str, list[tuple]], None]


class Application(Container):
    VERSION = "1.0.0"

    def __init__(self, base_path: str | None = None, *, strict: bool = False, override: bool = True) -> None:
        super().__init__(strict=strict, override=override)
        self._base_path: Path | None = Path(base_path) if base_path else None
        self._storage_path: Path | None = None
        self._config_path: Path | None = None
        self._database_path: Path | None = None
        self._resources_path: Path | None = None
        self._public_path: Path | None = None
        self._providers: list[ServiceProvider] = []
        self._deferred_providers: dict[Any, ServiceProvider] = {}
        self._booted: bool = False
        self._platform: Platform = Platform()
        self._response_handler: ResponseHandler | None = None
        self._self_bind()

    def _self_bind(self) -> None:
        self._self_keys: set = set()
        self.instance("app", self)
        self._self_keys.add("app")
        self.instance(Application, self)
        self._self_keys.add(Application)
        self.instance(Container, self)
        self._self_keys.add(Container)
        self.instance(Platform, self._platform)
        self.instance("platform", self._platform)

    @property
    def platform(self) -> Platform:
        return self._platform

    @property
    def platform_info(self) -> PlatformInfo:
        return self._platform.info

    @property
    def is_windows(self) -> bool:
        return self._platform.is_windows

    @property
    def is_linux(self) -> bool:
        return self._platform.is_linux

    @property
    def is_macos(self) -> bool:
        return self._platform.is_macos

    @property
    def is_unix(self) -> bool:
        return self._platform.is_unix

    def configure_event_loop(self, preferred: LoopType | None = None, *, force: bool = False) -> LoopType:
        return self._platform.configure_event_loop(preferred, force=force)

    @property
    def base_path(self) -> Path | None:
        return self._base_path

    @base_path.setter
    def base_path(self, path: str) -> None:
        self._base_path = Path(path)

    def path(self, *segments: str) -> Path:
        if self._base_path is None:
            raise RuntimeError("base_path is not set")
        return self._base_path.joinpath(*segments)

    @property
    def storage_path(self) -> Path | None:
        return self._storage_path

    def use_storage_path(self, path: str) -> Application:
        self._storage_path = Path(path)
        return self

    def storage(self, *segments: str) -> Path:
        base = self._storage_path or self.path("storage")
        return base.joinpath(*segments)

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    def use_config_path(self, path: str) -> Application:
        self._config_path = Path(path)
        return self

    def config(self, *segments: str) -> Path:
        base = self._config_path or self.path("config")
        return base.joinpath(*segments)

    @property
    def database_path(self) -> Path | None:
        return self._database_path

    def use_database_path(self, path: str) -> Application:
        self._database_path = Path(path)
        return self

    def database(self, *segments: str) -> Path:
        base = self._database_path or self.path("database")
        return base.joinpath(*segments)

    def resource(self, *segments: str) -> Path:
        base = self._resources_path or self.path("resources")
        return base.joinpath(*segments)

    def public(self, *segments: str) -> Path:
        base = self._public_path or self.path("public")
        return base.joinpath(*segments)

    @property
    def is_debug(self) -> bool:
        val = os.getenv("APP_DEBUG", "true").lower()
        return val in ("true", "1", "yes")

    @property
    def is_dev(self) -> bool:
        return not self.is_testing and self.app_env in ("development", "local")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return "pytest" in sys.modules

    @property
    def is_console(self) -> bool:
        if len(sys.argv) > 1:
            return sys.argv[1] != "serve"
        return True

    @property
    def app_env(self) -> str:
        if self.is_testing:
            return "testing"
        return os.getenv("APP_ENV", "local")

    def set_response_handler(self, handler: ResponseHandler) -> None:
        self._response_handler = handler

    def get_response_handler(self) -> ResponseHandler | None:
        return self._response_handler

    def register_provider(self, provider_class: type[ServiceProvider]) -> Application:
        provider = provider_class(self)

        if provider.deferred:
            for key in provider.provides():
                self._deferred_providers[key] = provider
            logger.debug("Deferred provider: %s", provider)
        else:
            self._providers.append(provider)
            logger.debug("Registered provider: %s", provider)

        return self

    def register_providers(self, *provider_classes: type[ServiceProvider]) -> Application:
        for cls in provider_classes:
            self.register_provider(cls)
        return self

    def add_providers(self, *provider_classes: type[ServiceProvider]) -> Application:
        for provider_class in provider_classes:
            provider = provider_class(self)
            self._providers.append(provider)
        return self

    def get_providers(self) -> list[ServiceProvider]:
        return list(self._providers)

    async def boot(self) -> None:
        if self._booted:
            logger.warning("Application already booted")
            return
        logger.info("Booting application v%s on %s...", self.VERSION, self._platform)

        for provider in self._providers:
            logger.debug("Registering: %s", provider)
            await provider.register()
        await self.build_dishka()

        for provider in self._providers:
            logger.debug("Booting: %s", provider)
            await provider.boot()
        self._booted = True
        logger.info("Application booted — %d providers, %d bindings", len(self._providers), len(self._bindings))

    @property
    def is_booted(self) -> bool:
        return self._booted

    async def shutdown(self) -> None:
        logger.info("Shutting down application...")
        await self.close()
        self._booted = False
        logger.info("Application shut down")

    async def make(self, abstract: Any, *args: Any, **kwargs: Any) -> Any:
        # Lazy-load deferred providers
        if abstract in self._deferred_providers and not self.has(abstract):
            provider = self._deferred_providers.pop(abstract)
            logger.debug("Lazy-registering deferred provider: %s", provider)
            await provider.register()
            if self._booted:
                await provider.boot()
            self._providers.append(provider)
        return await super().make(abstract, *args, **kwargs)

    async def close(self) -> None:
        for key, binding in self._bindings.items():
            # Skip self-references!
            if hasattr(self, "_self_keys") and key in self._self_keys:
                continue
            if binding.instance is not None:
                await self._try_close(binding.instance)

        if self._dishka_container is not None:
            await self._dishka_container.close()
            self._dishka_container = None

    def __call__(self, *args, **kwargs) -> Any:
        if self._response_handler:
            return self._response_handler(*args, **kwargs)
        raise RuntimeError("No response handler set")

    def __repr__(self) -> str:
        status = "booted" if self._booted else "not booted"
        env = self.app_env
        return (
            f"<Application v{self.VERSION} [{status}] env={env} "
            f"providers={len(self._providers)} "
            f"bindings={len(self._bindings)} "
            f"platform={self._platform.os_type.name}>"
        )
