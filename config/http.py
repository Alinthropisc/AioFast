
from typing import List, Literal

from pydantic import Field

from core.configuration.base import BaseConfiguration, NestedConfig


class CORSConfig(NestedConfig):
    allow_origins: list[str] = Field(default=["*"])
    allow_methods: list[str] = Field(default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    allow_headers: list[str] = Field(default=["*"])
    allow_credentials: bool = False
    expose_headers: list[str] = Field(default_factory=list)
    max_age: int = Field(default=600, description="Preflight cache seconds")


class RateLimitConfig(NestedConfig):
    enabled: bool = True
    requests: int = Field(default=60, description="Max requests per window")
    window: int = Field(default=60, description="Window in seconds")
    storage: Literal["memory", "redis"] = "memory"
    key_prefix: str = "ratelimit:"


class HTTPConfiguration(BaseConfiguration):
    __config_name__ = "http"
    __env_prefix__ = "HTTP_"

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    # Server
    server: Literal["granian", "uvicorn"] = "granian"
    # API
    api_prefix: str = "/api"
    api_version: str = "v1"
    # CORS
    cors: CORSConfig = Field(default_factory=CORSConfig)
    # Rate Limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    # Trusted proxies
    trusted_hosts: list[str] = Field(default=["*"])

    @property
    def full_api_prefix(self) -> str:
        return f"{self.api_prefix}/{self.api_version}"
