from __future__ import annotations

import pytest
from pydantic import Field

from core.configuration import (
    BaseConfiguration,
    ConfigError,
    ConfigKeyError,
    ConfigurationManager,
    FrozenConfigError,
)


class AppConfig(BaseConfiguration):
    __config_name__ = "app"
    __env_prefix__ = "APP_"
    name: str = Field(default="TestApp")
    env: str = Field(default="testing")
    debug: bool = Field(default=True)


class DbConfig(BaseConfiguration):
    __config_name__ = "database"
    __env_prefix__ = "DB_"
    host: str = Field(default="localhost")
    port: int = Field(default=5432)


class TestManagerRegistration:
    def test_register(self):
        m = ConfigurationManager()
        m.register(AppConfig())
        assert "app" in m.groups()

    def test_register_class(self):
        m = ConfigurationManager()
        cfg = m.register_class(AppConfig)
        assert isinstance(cfg, AppConfig)
        assert "app" in m.groups()

    def test_register_multiple(self):
        m = ConfigurationManager()
        m.register(AppConfig())
        m.register(DbConfig())
        assert set(m.groups()) == {"app", "database"}

    def test_register_default(self):
        m = ConfigurationManager()
        m.register_default(AppConfig())
        assert "app" in m.groups()

    def test_register_default_skips_if_user_exists(self):
        m = ConfigurationManager()
        user = AppConfig(name="UserApp")
        m.register(user)
        m.register_default(AppConfig(name="DefaultApp"))
        assert m.get("app.name") == "UserApp"


class TestManagerAccess:
    def test_get_simple(self, manager):
        assert manager.get("app.name") == "TestApp"
        assert manager.get("app.debug") is True

    def test_get_nested(self, manager):
        assert manager.get("database.host") == "localhost"
        assert manager.get("database.port") == 5432

    def test_get_default(self, manager):
        assert manager.get("nonexistent.key", "fallback") == "fallback"

    def test_get_group_only(self, manager):
        result = manager.get("app")
        assert result is not None

    def test_getitem(self, manager):
        assert manager["app.name"] == "TestApp"

    def test_getitem_missing_raises(self, manager):
        with pytest.raises(ConfigKeyError):
            _ = manager["nonexistent.key"]

    def test_has(self, manager):
        assert manager.has("app.name") is True
        assert manager.has("nonexistent") is False

    def test_contains(self, manager):
        assert "app.name" in manager
        assert "missing" not in manager


class TestManagerGroup:
    def test_group(self, manager):
        g = manager.group("app")
        assert g is not None
        assert isinstance(g, BaseConfiguration)

    def test_group_missing(self, manager):
        assert manager.group("nonexistent") is None

    def test_group_or_fail(self, manager):
        g = manager.group_or_fail("app")
        assert g is not None

    def test_group_or_fail_raises(self, manager):
        with pytest.raises(ConfigKeyError):
            manager.group_or_fail("nonexistent")


class TestManagerMutations:
    def test_set_override(self, manager):
        manager.set("app.name", "Overridden")
        assert manager.get("app.name") == "Overridden"

    def test_forget_override(self, manager):
        manager.set("app.name", "Overridden")
        assert manager.forget("app.name") is True
        assert manager.get("app.name") == "TestApp"

    def test_forget_nonexistent(self, manager):
        assert manager.forget("nonexistent") is False

    def test_clear_overrides(self, manager):
        manager.set("app.name", "X")
        manager.set("app.debug", False)
        manager.clear_overrides()
        assert manager.get("app.name") == "TestApp"
        assert manager.get("app.debug") is True

    def test_all(self, manager):
        data = manager.all()
        assert "app" in data
        assert "database" in data
        assert data["app"]["name"] == "TestApp"


class TestManagerFreeze:
    def test_freeze(self, manager):
        manager.freeze()
        assert manager.is_frozen is True

    def test_frozen_set_raises(self, manager):
        manager.freeze()
        with pytest.raises(FrozenConfigError):
            manager.set("app.name", "X")

    def test_frozen_forget_raises(self, manager):
        manager.freeze()
        with pytest.raises(FrozenConfigError):
            manager.forget("app.name")

    def test_frozen_clear_overrides_raises(self, manager):
        manager.freeze()
        with pytest.raises(FrozenConfigError):
            manager.clear_overrides()

    def test_frozen_refresh_raises(self, manager):
        manager.freeze()
        with pytest.raises(FrozenConfigError):
            manager.refresh()

    def test_unfreeze(self, manager):
        manager.freeze()
        manager.unfreeze()
        manager.set("app.name", "X")  # should not raise


class TestManagerSnapshot:
    def test_snapshot_rollback(self, manager):
        idx = manager.snapshot()
        manager.set("app.name", "Changed")
        assert manager.get("app.name") == "Changed"

        manager.rollback(idx)
        assert manager.get("app.name") == "TestApp"

    def test_multiple_snapshots(self, manager):
        idx1 = manager.snapshot()
        manager.set("app.name", "V1")

        idx2 = manager.snapshot()
        manager.set("app.name", "V2")

        manager.rollback(idx2)
        assert manager.get("app.name") == "V1"

        manager.rollback(idx1)
        assert manager.get("app.name") == "TestApp"

    def test_rollback_no_snapshots(self, manager):
        with pytest.raises(ConfigError, match="No snapshots"):
            manager.rollback()

    def test_clear_snapshots(self, manager):
        manager.snapshot()
        manager.clear_snapshots()
        with pytest.raises(ConfigError):
            manager.rollback()


class TestManagerValidation:
    def test_validate_all_valid(self, manager):
        errors = manager.validate_all()
        assert errors == {}

    def test_assert_valid(self, manager):
        manager.assert_valid()  # should not raise


class TestManagerChangeCallbacks:
    def test_on_change(self, manager):
        changes = []
        manager.on_change(lambda e: changes.append(e))
        manager.set("app.name", "NewName")
        assert len(changes) == 1
        assert changes[0].key == "app.name"
        assert changes[0].new_value == "NewName"

    def test_no_change_event_same_value(self, manager):
        changes = []
        manager.on_change(lambda e: changes.append(e))
        current = manager.get("app.name")
        manager.set("app.name", current)
        assert len(changes) == 0


class TestManagerSearch:
    def test_search(self, manager):
        results = manager.search("host")
        assert any("host" in k for k in results)

    def test_search_no_results(self, manager):
        results = manager.search("zzz_nonexistent_zzz")
        assert results == {}


class TestManagerExportImport:
    def test_export_import(self, manager, tmp_path):
        path = tmp_path / "config.json"
        manager.export_json(path)
        assert path.exists()

        # New manager, import
        m2 = ConfigurationManager()
        m2.register(AppConfig())
        m2.register(DbConfig())
        assert m2.import_json(path) is True

    def test_import_nonexistent(self, manager, tmp_path):
        assert manager.import_json(tmp_path / "nope.json") is False


class TestManagerLoadFromPath:
    @pytest.mark.asyncio
    async def test_load_from_path(self, config_dir):
        m = ConfigurationManager(base_path=config_dir.parent)
        count = await m.load_from_path(config_dir)
        assert count >= 1
        assert m.is_loaded is True

    @pytest.mark.asyncio
    async def test_load_missing_path(self, tmp_path):
        m = ConfigurationManager()
        count = await m.load_from_path(tmp_path / "nonexistent")
        assert count == 0


class TestManagerEnvHelpers:
    def test_is_debug(self, manager):
        assert manager.is_debug() is True

    def test_is_testing(self):
        m = ConfigurationManager()
        m.register(AppConfig(env="testing"))
        assert m.is_testing() is True

    def test_repr(self, manager):
        r = repr(manager)
        assert "ConfigurationManager" in r
        assert "app" in r
