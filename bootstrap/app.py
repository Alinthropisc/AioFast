"""Application bootstrap.

`create_application()` builds the AioFast :class:`Application`, registers the
core service providers and the user-land providers from ``app/providers``.

The returned application is **not** booted — booting (which starts the
adapters and the underlying ASGI app) is the responsibility of whatever drives
it: the ``serve`` command for HTTP, or a bot runner for Aiogram.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.foundation import Application

BASE_PATH = Path(__file__).resolve().parent.parent


def load_dotenv(base_path: Path | None = None) -> None:
    """Minimal ``.env`` loader — populate ``os.environ`` before booting.

    Existing environment variables always win, so real env beats the file.
    """
    base = base_path or BASE_PATH
    env_file = base / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def create_application(base_path: str | Path | None = None) -> Application:
    """Build and configure the application (without booting it)."""
    base = Path(base_path) if base_path else BASE_PATH
    load_dotenv(base)

    app = Application(str(base))
    app.name = os.environ.get("APP_NAME", "AioFast")  # type: ignore[attr-defined]
    app.version = Application.VERSION  # type: ignore[attr-defined]

    _register_core_providers(app)
    _register_app_providers(app)
    return app


def _register_core_providers(app: Application) -> None:
    from core.adapters.litestar.litestar_service_provider import LitestarServiceProvider
    from core.configuration import ConfigServiceProvider
    from core.log.logger_service_provider import LogServiceProvider
    from core.registry import RegistryServiceProvider
    from core.server.servcer_service_provider import ServerServiceProvider

    # Order matters: RegistryServiceProvider must register the AdapterManager
    # before the adapters (Litestar/Aiogram) try to attach themselves to it.
    app.register_providers(
        LogServiceProvider,
        ConfigServiceProvider,
        RegistryServiceProvider,
        LitestarServiceProvider,
    )

    # Aiogram is optional — only wire it up when a bot token is configured.
    if os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN"):
        from core.adapters.aiogram.aiogram_service_provider import AiogramServiceProvider

        app.register_providers(AiogramServiceProvider)

    app.register_providers(ServerServiceProvider)


def _register_app_providers(app: Application) -> None:
    """Register user-land providers from ``app/providers``.

    Imported lazily and defensively so a fresh project without an ``app``
    package still boots.
    """
    try:
        from app.providers.app_service_provider import AppServiceProvider
    except ImportError:
        return
    app.register_providers(AppServiceProvider)
