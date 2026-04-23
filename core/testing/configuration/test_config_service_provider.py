from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.configuration import ConfigServiceProvider, ConfigurationManager
from core.foundation import Application

if TYPE_CHECKING:
    from pathlib import Path

SIMPLE_APP_CONFIG = """
config = {
    "name": "TestApp",
    "debug": True,
    "env": "testing",
}
"""

SIMPLE_DB_CONFIG = """
config = {
    "default": "sqlite",
    "connections": {
        "sqlite": {
            "url": "sqlite+aiosqlite:///:memory:",
        },
    },
}
"""


class TestConfigServiceProvider:
    @pytest.mark.asyncio
    async def test_register(self):
        app = Application()
        provider = ConfigServiceProvider(app)
        await provider.register()

        manager = await app.make(ConfigurationManager)
        assert isinstance(manager, ConfigurationManager)

    @pytest.mark.asyncio
    async def test_register_by_string(self):
        app = Application()
        provider = ConfigServiceProvider(app)
        await provider.register()

        manager = await app.make("config")
        assert isinstance(manager, ConfigurationManager)

    @pytest.mark.asyncio
    async def test_boot_loads_config(self, tmp_path: Path):
        # Create config directory with SIMPLE files (no external imports)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "app.py").write_text(SIMPLE_APP_CONFIG.strip(), encoding="utf-8")
        (config_dir / "database.py").write_text(SIMPLE_DB_CONFIG.strip(), encoding="utf-8")

        app = Application(base_path=tmp_path)  # ty:ignore[invalid-argument-type]
        provider = ConfigServiceProvider(app)
        await provider.register()
        await provider.boot()

        manager: ConfigurationManager = await app.make(ConfigurationManager)
        assert manager.is_loaded

        # Verify config was loaded
        assert manager.get("app.name") == "TestApp"
        assert manager.get("app.debug") is True
        assert manager.get("database.default") == "sqlite"

    @pytest.mark.asyncio
    async def test_boot_no_config_dir(self, tmp_path: Path):
        """Boot should not crash if config/ doesn't exist."""
        app = Application(base_path=tmp_path)  # ty:ignore[invalid-argument-type]
        provider = ConfigServiceProvider(app)
        await provider.register()
        await provider.boot()

        manager: ConfigurationManager = await app.make(ConfigurationManager)
        assert isinstance(manager, ConfigurationManager)

    @pytest.mark.asyncio
    async def test_boot_empty_config_dir(self, tmp_path: Path):
        """Boot should handle empty config/ directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        app = Application(base_path=tmp_path)  # ty:ignore[invalid-argument-type]
        provider = ConfigServiceProvider(app)
        await provider.register()
        await provider.boot()

        manager: ConfigurationManager = await app.make(ConfigurationManager)
        assert isinstance(manager, ConfigurationManager)

    @pytest.mark.asyncio
    async def test_boot_ignores_non_py_files(self, tmp_path: Path):
        """Boot should skip non-.py files in config/."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "app.py").write_text(SIMPLE_APP_CONFIG.strip(), encoding="utf-8")
        (config_dir / "readme.txt").write_text("ignore me", encoding="utf-8")
        (config_dir / "data.json").write_text('{"ignore": true}', encoding="utf-8")

        app = Application(base_path=tmp_path)  # ty:ignore[invalid-argument-type]
        provider = ConfigServiceProvider(app)
        await provider.register()
        await provider.boot()

        manager: ConfigurationManager = await app.make(ConfigurationManager)
        assert manager.has("app.name")

    @pytest.mark.asyncio
    async def test_boot_ignores_dunder_files(self, tmp_path: Path):
        """Boot should skip __init__.py and similar."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "__init__.py").write_text("", encoding="utf-8")
        (config_dir / "app.py").write_text(SIMPLE_APP_CONFIG.strip(), encoding="utf-8")

        app = Application(base_path=tmp_path)  # ty:ignore[invalid-argument-type]
        provider = ConfigServiceProvider(app)
        await provider.register()
        await provider.boot()

        manager: ConfigurationManager = await app.make(ConfigurationManager)
        assert manager.has("app.name")
        # __init__ should NOT become a config group
        assert not manager.has("__init__")
