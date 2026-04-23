from pathlib import Path

import pytest
from pydantic import Field

from core.configuration.base import BaseConfiguration
from core.configuration.environment import Environment
from core.configuration.manager import ConfigurationManager

# ── Test Config Classes ─────────────────────────────────


class AppConfig(BaseConfiguration):
    __config_name__ = "app"
    __env_prefix__ = "APP_"
    name: str = Field(default="TestApp")
    env: str = Field(default="testing")
    debug: bool = Field(default=True)
    port: int = Field(default=8000)


class DatabaseConfig(BaseConfiguration):
    __config_name__ = "database"
    __env_prefix__ = "DB_"
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="testdb")
    user: str = Field(default="postgres")
    password: str = Field(default="secret")


# ── MAIN FIXTURES ───────────────────────────────────────


@pytest.fixture
def manager() -> ConfigurationManager:
    """Основная фикстура для test_manager.py."""
    mgr = ConfigurationManager()
    mgr.register(AppConfig())
    mgr.register(DatabaseConfig())
    mgr.set("app.name", "TestApp")
    mgr.set("app.env", "testing")
    mgr.set("database.host", "localhost")
    mgr.set("database.port", 5432)
    return mgr


@pytest.fixture
def config_manager() -> ConfigurationManager:
    """Алиас для manager."""
    return manager()


# ── Environment Fixtures ────────────────────────────────


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    """Создаёт тестовый .env файл со ВСЕМИ переменными."""
    env_path = tmp_path / ".env.testing"
    env_path.write_text(
        """
# App
APP_NAME=TestApp
APP_ENV=local
APP_DEBUG=true
APP_PORT=8000
APP_KEY=test-key-123
APP_PREFIX=MyApp
APP_SECRET=app-secret-value

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=testdb
DB_USER=postgres
DB_PASSWORD=my_db_pass

# Test variables
LIST_VAR=a,b,c
INT_VAR=42
FLOAT_VAR=3.14
BOOL_TRUE=true
BOOL_FALSE=false
STRING_VAR=hello
DICT_VAR={"key": "value"}
JSON_VAR={"key": "value"}
ENUM_VAR=local
SECRET_VAR=secret

# For SecretsResolver tests (IMPORTANT!)
API_KEY=key-123-abc
DB_SECRET=db-secret-value
SECRET_KEY=super-secret-key-12345

# Interpolation
BASE_URL=https://api.example.com
API_URL=${BASE_URL}/v1
INTERPOLATED=${APP_PREFIX}_suffix
""".strip(),
        encoding="utf-8",
    )
    return env_path


@pytest.fixture
def env(env_file: Path, tmp_path: Path) -> Environment:
    """Создаёт Environment с загруженным .env."""
    return Environment(env_file=env_file, load_system_env=False, base_path=tmp_path, interpolate=True)


# ── Config Directory Fixture ────────────────────────────


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Создаёт директорию с .py конфигами."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    (cfg_dir / "app.py").write_text(
        """
from core.configuration.base import BaseConfiguration
from pydantic import Field

class AppConfig(BaseConfiguration):
    __config_name__ = "app"
    name: str = Field(default="FromFile")
    debug: bool = Field(default=False)
""".strip(),
        encoding="utf-8",
    )

    (cfg_dir / "database.py").write_text(
        """
from core.configuration.base import BaseConfiguration
from pydantic import Field

class DatabaseConfig(BaseConfiguration):
    __config_name__ = "database"
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
""".strip(),
        encoding="utf-8",
    )

    return cfg_dir


# ── Individual Config Fixtures ──────────────────────────


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def db_config() -> DatabaseConfig:
    return DatabaseConfig()
