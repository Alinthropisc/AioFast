from typing import Literal, Optional

from pydantic import Field

from core.configuration import BaseConfiguration, NestedConfig


class RedisStoreConfig(NestedConfig):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 50
    decode_responses: bool = True
    url: str | None = Field(
        default=None, description="Full Redis URL (overrides host/port/db). Example: redis://localhost:6379/0"
    )


class FileStoreConfig(NestedConfig):
    path: str = "storage/cache"
    extension: str = ".cache"


class CacheConfiguration(BaseConfiguration):
    """Cache configuration.

    Env: CACHE_DEFAULT, CACHE_PREFIX, CACHE_TTL, CACHE_REDIS__HOST, etc.
    """

    __config_name__ = "cache"
    __env_prefix__ = "CACHE_"

    default: str = Field(default="memory", description="Default cache store")
    prefix: str = Field(default="app_cache:", description="Key prefix")
    ttl: int = Field(default=3600, description="Default TTL in seconds")
    serializer: Literal["json", "pickle"] = Field(default="json")

    # Store configs
    redis: RedisStoreConfig = Field(default_factory=RedisStoreConfig)
    file: FileStoreConfig = Field(default_factory=FileStoreConfig)
