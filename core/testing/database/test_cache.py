from __future__ import annotations

import asyncio

import pytest

from core.database.cache import QueryCache, make_cache_key


class TestQueryCacheMemory:
    @pytest.mark.asyncio
    async def test_put_and_get(self):
        cache = QueryCache()
        await cache.put("key1", {"data": "hello"}, ttl=60)
        result = await cache.get("key1")
        assert result == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_get_missing(self):
        cache = QueryCache()
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        cache = QueryCache()
        await cache.put("short", "value", ttl=1)
        assert await cache.get("short") == "value"

        await asyncio.sleep(1.1)
        assert await cache.get("short") is None

    @pytest.mark.asyncio
    async def test_remember_cache_hit(self):
        cache = QueryCache()
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]

        # First call — cache miss
        result1 = await cache.remember("data", 60, fetch)
        assert result1 == [1, 2, 3]
        assert call_count == 1

        # Second call — cache hit
        result2 = await cache.remember("data", 60, fetch)
        assert result2 == [1, 2, 3]
        assert call_count == 1  # NOT called again

    @pytest.mark.asyncio
    async def test_remember_sync_callback(self):
        cache = QueryCache()
        result = await cache.remember("sync", 60, lambda: "sync_value")
        assert result == "sync_value"

    @pytest.mark.asyncio
    async def test_forget(self):
        cache = QueryCache()
        await cache.put("key", "val", ttl=60)
        assert await cache.forget("key") is True
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_forget_missing(self):
        cache = QueryCache()
        assert await cache.forget("nope") is False

    @pytest.mark.asyncio
    async def test_forget_pattern(self):
        cache = QueryCache()
        await cache.put("users:1", "a", ttl=60)
        await cache.put("users:2", "b", ttl=60)
        await cache.put("posts:1", "c", ttl=60)

        count = await cache.forget_pattern("users:*")
        assert count == 2
        assert await cache.get("users:1") is None
        assert await cache.get("posts:1") == "c"

    @pytest.mark.asyncio
    async def test_flush(self):
        cache = QueryCache()
        await cache.put("a", 1, ttl=60)
        await cache.put("b", 2, ttl=60)
        await cache.flush()
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_has(self):
        cache = QueryCache()
        await cache.put("exists", "yes", ttl=60)
        assert await cache.has("exists") is True
        assert await cache.has("nope") is False

    @pytest.mark.asyncio
    async def test_size(self):
        cache = QueryCache()
        assert cache.size == 0
        await cache.put("a", 1, ttl=60)
        await cache.put("b", 2, ttl=60)
        assert cache.size == 2

    def test_repr(self):
        cache = QueryCache()
        assert "memory" in repr(cache)


class TestTaggedCache:
    @pytest.mark.asyncio
    async def test_tagged_put_and_get(self):
        cache = QueryCache()
        tagged = cache.tags("users")

        await tagged.put("list", [1, 2, 3], ttl=60)
        result = await tagged.get("list")
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_tagged_remember(self):
        cache = QueryCache()
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return "data"

        tagged = cache.tags("users")
        r1 = await tagged.remember("active", 60, fetch)
        r2 = await tagged.remember("active", 60, fetch)

        assert r1 == r2 == "data"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_tagged_flush(self):
        cache = QueryCache()

        await cache.tags("users").put("list", [1], ttl=60)
        await cache.tags("users").put("count", 5, ttl=60)
        await cache.tags("posts").put("list", [2], ttl=60)

        count = await cache.tags("users").flush()
        assert count == 2

        # Posts should remain
        assert await cache.tags("posts").get("list") == [2]

    @pytest.mark.asyncio
    async def test_different_tags_different_keys(self):
        cache = QueryCache()
        await cache.tags("users").put("list", "users_data", ttl=60)
        await cache.tags("posts").put("list", "posts_data", ttl=60)

        assert await cache.tags("users").get("list") == "users_data"
        assert await cache.tags("posts").get("list") == "posts_data"


class TestMakeCacheKey:
    def test_deterministic(self):
        k1 = make_cache_key("users", "SELECT * FROM users", {"id": 1})
        k2 = make_cache_key("users", "SELECT * FROM users", {"id": 1})
        assert k1 == k2

    def test_different_queries(self):
        k1 = make_cache_key("x", "SELECT 1", None)
        k2 = make_cache_key("x", "SELECT 2", None)
        assert k1 != k2
