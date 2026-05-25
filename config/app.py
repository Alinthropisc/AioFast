from typing import Literal, Optional

from pydantic import Field, HttpUrl, SecretStr, field_validator

from core.configuration import BaseConfiguration


class Application(BaseConfiguration):
    __config_name__ = "app"
    __env_prefix__ = "APP_"

    # ══════════════════════════════════════════════
    # APPLICATION
    # ══════════════════════════════════════════════

    name: str = Field(default="Application", description="Application name")
    env: Literal["local", "development", "staging", "production", "testing"] = Field(
        default="local", description="Application environment"
    )
    key: SecretStr = Field(description="Application encryption key (required)")
    debug: bool = Field(default=False, description="Debug mode")
    url: HttpUrl = Field(default="http://localhost:8000", description="Application URL")  # ty:ignore[invalid-assignment]

    # ══════════════════════════════════════════════
    # LOCALIZATION
    # ══════════════════════════════════════════════

    locale: str = Field(default="en")
    timezone: str = Field(default="UTC")
    fallback_locale: str = Field(default="en")
    faker_locale: str = Field(default="en_US")

    # ══════════════════════════════════════════════
    # SERVICES
    # ══════════════════════════════════════════════

    cache_store: str = Field(default="redis")
    cache_prefix: str = Field(default="app_cache_")
    filesystem_disk: str = Field(default="local")
    queue_connection: str = Field(default="redis")
    broadcast_connection: str = Field(default="redis")

    # ══════════════════════════════════════════════
    # MAINTENANCE
    # ══════════════════════════════════════════════

    maintenance_driver: str = Field(default="file")
    maintenance_store: str = Field(default="database")

    # ══════════════════════════════════════════════
    # SECURITY
    # ══════════════════════════════════════════════

    bcrypt_rounds: int = Field(default=12, ge=4, le=31)
    access_token_expire_minutes: int = Field(default=60 * 24 * 8)

    # ══════════════════════════════════════════════
    # EXTERNAL
    # ══════════════════════════════════════════════

    sentry_dsn: HttpUrl | None = Field(default=None)
    api_version: str = Field(default="v1")
    frontend_host: HttpUrl = Field(default="http://localhost:5173")  # ty:ignore[invalid-assignment]

    # ══════════════════════════════════════════════
    # METHODS
    # ══════════════════════════════════════════════

    # В pydantic v2 валидаторы объявляются по именам полей модели,
    # а не по именам переменных окружения.
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            value = v.strip().lower()
            return value in ("true", "1", "yes", "on")
        return bool(v)

    @field_validator("bcrypt_rounds", mode="before")
    @classmethod
    def parse_bcrypt_rounds(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_local(self) -> bool:
        return self.env == "local"

    @property
    def is_debug_mode(self) -> bool:
        return self.debug and not self.is_production
