
from typing import Literal, Optional

from pydantic import Field, SecretStr

from core.configuration.base import BaseConfiguration, NestedConfig


class JWTConfig(NestedConfig):
    secret: SecretStr = SecretStr("change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_days: int = 30
    issuer: str | None = None
    audience: str | None = None


class SessionConfig(NestedConfig):
    driver: Literal["memory", "redis"] = "memory"
    lifetime: int = Field(default=120, description="Minutes")
    cookie_name: str = "session_id"
    secure: bool = False
    http_only: bool = True
    same_site: Literal["lax", "strict", "none"] = "lax"


class AuthConfiguration(BaseConfiguration):
    __config_name__ = "auth"
    __env_prefix__ = "AUTH_"

    default_guard: Literal["jwt", "session"] = "jwt"
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    # RBAC
    rbac_enabled: bool = False
    rbac_model_path: str = "config/rbac_model.conf"
    rbac_policy_path: str = "config/rbac_policy.csv"
