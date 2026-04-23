from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.configuration import ConfigCache

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def cache(tmp_path: Path) -> ConfigCache:
    return ConfigCache(tmp_path / "cache")


@pytest.fixture
def sample_data() -> dict:
    return {
        "app": {"name": "Test", "debug": True},
        "database": {"host": "localhost", "port": 5432},
    }


class TestConfigCacheStore:
    def test_store_creates_file(self, cache, sample_data):
        path = cache.store(sample_data)
        assert path.exists()

    def test_is_cached(self, cache, sample_data):
        assert cache.is_cached() is False
        cache.store(sample_data)
        assert cache.is_cached() is True


class TestConfigCacheLoad:
    def test_load(self, cache, sample_data):
        cache.store(sample_data)
        loaded = cache.load()
        assert loaded is not None
        assert loaded["app"]["name"] == "Test"
        assert loaded["database"]["port"] == 5432

    def test_load_missing(self, cache):
        assert cache.load() is None

    def test_load_max_age(self, cache, sample_data):
        cache.store(sample_data)
        # Should be fresh
        assert cache.load(max_age=10) is not None

    def test_load_stale(self, cache, sample_data):
        cache.store(sample_data)
        # Immediately stale with 0 max_age
        assert cache.load(max_age=0) is None


class TestConfigCacheStale:
    def test_is_stale_no_cache(self, cache, sample_data):
        assert cache.is_stale(sample_data) is True

    def test_is_stale_same_data(self, cache, sample_data):
        cache.store(sample_data)
        assert cache.is_stale(sample_data) is False

    def test_is_stale_different_data(self, cache, sample_data):
        cache.store(sample_data)
        modified = {**sample_data, "app": {"name": "Changed"}}
        assert cache.is_stale(modified) is True


class TestConfigCacheClear:
    def test_clear(self, cache, sample_data):
        cache.store(sample_data)
        assert cache.clear() is True
        assert cache.is_cached() is False

    def test_clear_empty(self, cache):
        assert cache.clear() is False


class TestConfigCacheRepr:
    def test_repr(self, cache, sample_data):
        assert "empty" in repr(cache)
        cache.store(sample_data)
        assert "cached" in repr(cache)
