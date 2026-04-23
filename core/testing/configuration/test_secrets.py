from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.configuration import SecretsResolver

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def secrets_dir(tmp_path: Path) -> Path:
    """Создаёт директорию с файлами секретов."""
    secrets_path = tmp_path / "secrets"
    secrets_path.mkdir()

    (secrets_path / "DB_PASSWORD").write_text("my_db_pass", encoding="utf-8")
    (secrets_path / "API_KEY").write_text("key-123-abc", encoding="utf-8")
    (secrets_path / "SECRET_KEY").write_text("super-secret-key-12345", encoding="utf-8")

    return secrets_path


@pytest.fixture
def resolver(secrets_dir: Path) -> SecretsResolver:
    r = SecretsResolver()
    r.add_file_backend(secrets_dir)
    return r


class TestSecretsResolverEnv:
    def test_resolve_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "env_value")
        r = SecretsResolver()
        assert r.resolve("MY_SECRET") == "env_value"

    def test_resolve_missing(self):
        r = SecretsResolver()
        assert r.resolve("DEFINITELY_MISSING_XYZ") is None
        assert r.resolve("DEFINITELY_MISSING_XYZ", "fallback") == "fallback"


class TestSecretsResolverMany:
    def test_resolve_many(self, resolver, env_file: Path, tmp_path: Path):
        from core.configuration.environment import Environment

        env = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        resolver = SecretsResolver(env)  # ty:ignore[too-many-positional-arguments]
        result = resolver.resolve_many(["DB_PASSWORD", "API_KEY", "MISSING"])
        assert result["DB_PASSWORD"] == "my_db_pass"
        assert result["API_KEY"] == "key-123-abc"
        assert result["MISSING"] is None

    def test_file_not_found(self, resolver):
        assert resolver.resolve("NONEXISTENT_FILE") is None


class TestSecretsResolverCustom:
    def test_custom_resolver(self):
        vault = {"vault_secret": "vault_value"}
        r = SecretsResolver()
        r.add_resolver("vault", lambda key: vault.get(key))
        assert r.resolve("vault_secret") == "vault_value"
        assert r.resolve("missing") is None

    def test_prefix_mapping(self):
        vault = {"my_key": "from_vault"}
        r = SecretsResolver()
        r.add_resolver("vault", lambda key: vault.get(key))
        r.map_prefix("vault://", "vault")
        assert r.resolve("vault://my_key") == "from_vault"


class TestSecretsResolverCache:
    def test_caches_results(self, resolver):
        val1 = resolver.resolve("PASSWORD")
        val2 = resolver.resolve("PASSWORD")
        assert val1 == val2

    def test_clear_cache(self, resolver):
        resolver.resolve("PASSWORD")
        resolver.clear_cache()
        assert resolver._cache == {}


class TestSecretsResolverMany:
    def test_resolve_many(self, resolver):
        result = resolver.resolve_many(["DB_PASSWORD", "API_KEY", "MISSING"])
        assert result["DB_PASSWORD"] == "my_db_pass"
        assert result["API_KEY"] == "key-123-abc"
        assert result["MISSING"] is None


class TestSecretsBase64:
    def test_decode_base64(self):
        import base64

        encoded = base64.b64encode(b"hello world").decode()
        assert SecretsResolver.decode_base64(encoded) == "hello world"

    def test_decode_base64_with_prefix(self):
        import base64

        encoded = "base64:" + base64.b64encode(b"secret123").decode()
        assert SecretsResolver.decode_base64(encoded) == "secret123"


class TestSecretsRepr:
    def test_repr(self, resolver):
        r = repr(resolver)
        assert "SecretsResolver" in r
