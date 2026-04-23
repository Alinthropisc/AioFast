from __future__ import annotations

from pydantic import Field, SecretStr

from core.configuration import BaseConfiguration


class SimpleConfig(BaseConfiguration):
    __config_name__ = "simple"
    __env_prefix__ = "SIMPLE_"
    name: str = Field(default="Simple")
    count: int = Field(default=10)


class AutoPrefixConfig(BaseConfiguration):
    name: str = Field(default="Auto")


class SecretConfig(BaseConfiguration):
    __config_name__ = "secret_test"
    __env_prefix__ = "SECRET_TEST_"
    api_key: SecretStr = Field(default=SecretStr("default-key"))
    password: str = Field(default="pass123")


class NestedAppConfig(BaseConfiguration):
    __config_name__ = "nested"
    __env_prefix__ = "NESTED_"
    name: str = Field(default="Nested")
    db: dict = Field(default={"host": "localhost", "port": 5432})


class TestBaseConfigName:
    def test_explicit_name(self):
        assert SimpleConfig.config_name() == "simple"

    def test_auto_name(self):
        assert AutoPrefixConfig.config_name() == "autoprefix"


class TestBaseConfigPrefix:
    def test_explicit_prefix(self):
        assert SimpleConfig._get_prefix() == "SIMPLE_"

    def test_auto_prefix(self):
        prefix = AutoPrefixConfig._get_prefix()
        assert prefix == "AUTO_PREFIX_"


class TestBaseConfigToDict:
    def test_to_dict(self):
        cfg = SimpleConfig()
        d = cfg.to_dict()
        assert d["name"] == "Simple"
        assert d["count"] == 10

    def test_to_dict_masks_secrets(self):
        cfg = SecretConfig()
        d = cfg.to_dict()
        assert d["api_key"] == "***SECRET***"

    def test_to_safe_dict(self):
        cfg = SecretConfig()
        d = cfg.to_safe_dict()
        assert d["password"] == "***MASKED***"


class TestBaseConfigGet:
    def test_get_simple(self):
        cfg = SimpleConfig()
        assert cfg.get("name") == "Simple"
        assert cfg.get("count") == 10

    def test_get_nested(self):
        cfg = NestedAppConfig()
        assert cfg.get("db.host") == "localhost"
        assert cfg.get("db.port") == 5432

    def test_get_default(self):
        cfg = SimpleConfig()
        assert cfg.get("nonexistent", "fallback") == "fallback"


class TestBaseConfigKeys:
    def test_keys(self):
        cfg = SimpleConfig()
        assert "name" in cfg
        assert "count" in cfg


class TestBaseConfigMerge:
    def test_merge_dict(self):
        cfg = SimpleConfig()
        merged = cfg.merge({"name": "Merged", "count": 99})
        assert merged.name == "Merged"  # ty:ignore[unresolved-attribute]
        assert merged.count == 99  # ty:ignore[unresolved-attribute]

    def test_merge_config(self):
        cfg1 = SimpleConfig(name="A")
        cfg2 = SimpleConfig(name="B", count=42)
        merged = cfg1.merge(cfg2)
        assert merged.name == "B"  # ty:ignore[unresolved-attribute]
        assert merged.count == 42  # ty:ignore[unresolved-attribute]


class TestBaseConfigFromDict:
    def test_from_dict(self):
        cfg = SimpleConfig.from_dict({"name": "FromDict", "count": 5})
        assert cfg.name == "FromDict"
        assert cfg.count == 5


class TestBaseConfigRepr:
    def test_repr(self):
        cfg = SimpleConfig()
        r = repr(cfg)
        assert "SimpleConfig" in r
        assert "simple" in r
