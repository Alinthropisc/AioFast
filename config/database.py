from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import Field, SecretStr

from core.configuration.base import BaseConfiguration, NestedConfig


class ConnectionConfig(NestedConfig):
    """Single database connection config."""

    driver: Literal["sqlite", "postgresql", "mysql", "mssql", "oracle"] = "sqlite"
    host: str = "localhost"
    port: int | None = None
    database: str = "database.sqlite3"
    username: str = ""
    password: SecretStr = SecretStr("")
    url: str | None = Field(
        default=None,
        description="Full URL (overrides individual fields). Example: postgresql+asyncpg://user:pass@host:5432/dbname",
    )
    # Pool
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout: float = Field(default=30.0)
    pool_recycle: int = Field(default=3600, description="Seconds before connection recycled")
    pool_pre_ping: bool = Field(default=True, description="Test connections before use")

    # Engine options
    echo: bool = Field(default=False, description="Log SQL statements")
    echo_pool: bool = False

    def get_url(self) -> str:
        """Build SQLAlchemy async URL from config fields."""
        if self.url:
            return self.url

        driver_map = {
            "sqlite": "sqlite+aiosqlite",
            "postgresql": "postgresql+asyncpg",
            "mysql": "mysql+aiomysql",
            "mssql": "mssql+aioodbc",
            "oracle": "oracle+oracledb",
        }

        dialect = driver_map.get(self.driver, self.driver)

        if self.driver == "sqlite":
            return f"{dialect}:///{self.database}"

        pwd = self.password.get_secret_value() if self.password else ""
        port_str = f":{self.port}" if self.port else ""

        return f"{dialect}://{self.username}:{pwd}@{self.host}{port_str}/{self.database}"

    def get_default_port(self) -> int:
        ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "mssql": 1433,
            "oracle": 1521,
        }
        return ports.get(self.driver, 0)


class DatabaseConfiguration(BaseConfiguration):
    """Database configuration supporting multiple connections.

    Env: DB_DEFAULT, DB_URL, DB_HOST, DB_PORT, etc.

    Usage in config/database.py:
        class DatabaseConfiguration(DatabaseConfiguration):
            connections = {
                "default": ConnectionConfig(driver="postgresql", ...),
                "analytics": ConnectionConfig(driver="mysql", ...),
            }
    """

    __config_name__ = "database"
    __env_prefix__ = "DB_"

    default: str = Field(default="default", description="Default connection name")

    # Quick single-connection setup via env vars
    driver: Literal["sqlite", "postgresql", "mysql", "mssql", "oracle"] = "sqlite"
    host: str = "localhost"
    port: int | None = None
    database: str = "database.sqlite3"
    username: str = ""
    password: SecretStr = SecretStr("")
    url: str | None = None

    # Pool defaults
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False

    # Multiple connections (set in config/database.py)
    connections: dict[str, ConnectionConfig] = Field(default_factory=dict)

    def get_connection(self, name: str | None = None) -> ConnectionConfig:
        """Get a connection config by name."""
        name = name or self.default

        if name in self.connections:
            return self.connections[name]

        # Fallback to top-level fields as "default" connection
        if name == "default" or name == self.default:
            return ConnectionConfig(
                driver=self.driver,
                host=self.host,
                port=self.port,
                database=self.database,
                username=self.username,
                password=self.password,
                url=self.url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                echo=self.echo,
            )

        raise KeyError(f"Database connection '{name}' not found")
