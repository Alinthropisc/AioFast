from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class QueryCache:
    """
    Query result caching — in-memory or Redis.

    Usage:
        cache = QueryCache()  # in-memory
        cache = QueryCache(redis=redis_client)  # Redis

        # Manual:
        result = await cache.remember("users:active", ttl=60, callback=fetch_users)

        # With repository:
        class CachedUserRepo(BaseRepository[User]):
            def __init__(self, session, cache):
                super().__init__(session)
                self.cache = cache

            async def active_users(self):
                return await self.cache.remember(
                    "users:active", 60,
                    lambda: self.where(is_active=True)
                )

        # Invalidate:
        await cache.forget("users:active")
        await cache.forget_pattern("users:*")
        await cache.flush()

        # Tags:
        await cache.tags("users").remember("list", 60, fetch)
        await cache.tags("users").flush()
    """

    def __init__(self, redis: Any = None) -> None:
        self._redis = redis
        self._memory: dict[str, _CacheEntry] = {}

    # ── Core ──────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        """Get cached value or None."""
        if self._redis:
            return await self._redis_get(key)
        return self._memory_get(key)

    async def put(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store value with TTL (seconds)."""
        if self._redis:
            await self._redis_put(key, value, ttl)
        else:
            self._memory_put(key, value, ttl)

    async def remember(self, key: str, ttl: int, callback: Callable) -> Any:
        """Get from cache or compute + store."""
        cached = await self.get(key)
        if cached is not None:
            logger.debug("Cache HIT: %s", key)
            return cached

        logger.debug("Cache MISS: %s", key)
        import asyncio

        if asyncio.iscoroutinefunction(callback):
            value = await callback()
        else:
            value = callback()

        await self.put(key, value, ttl)
        return value

    async def forget(self, key: str) -> bool:
        """Remove from cache."""
        if self._redis:
            return await self._redis_forget(key)
        return self._memory_forget(key)

    async def forget_pattern(self, pattern: str) -> int:
        """Remove keys matching pattern (e.g. 'users:*')."""
        if self._redis:
            return await self._redis_forget_pattern(pattern)
        return self._memory_forget_pattern(pattern)

    async def flush(self) -> None:
        """Clear entire cache."""
        if self._redis:
            await self._redis.flushdb()
        else:
            self._memory.clear()
        logger.info("Cache flushed")

    async def has(self, key: str) -> bool:
        return await self.get(key) is not None

    # ── Tags ──────────────────────────────────────────────

    def tags(self, *tags: str) -> _TaggedCache:
        """Create tagged cache instance."""
        return _TaggedCache(self, set(tags))

    # ── Stats ─────────────────────────────────────────────

    @property
    def size(self) -> int:
        if self._redis:
            return 0  # Use redis info
        return len(self._memory)

    # ── In-memory implementation ──────────────────────────

    def _memory_get(self, key: str) -> Any | None:
        entry = self._memory.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._memory[key]
            return None
        return entry.value

    def _memory_put(self, key: str, value: Any, ttl: int) -> None:
        self._memory[key] = _CacheEntry(value, ttl)

    def _memory_forget(self, key: str) -> bool:
        return self._memory.pop(key, None) is not None

    def _memory_forget_pattern(self, pattern: str) -> int:
        import fnmatch

        keys_to_delete = [k for k in self._memory if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._memory[k]
        return len(keys_to_delete)

    # ── Redis implementation ──────────────────────────────

    async def _redis_get(self, key: str) -> Any | None:
        raw = await self._redis.get(f"qcache:{key}")
        if raw is None:
            return None
        return json.loads(raw)

    async def _redis_put(self, key: str, value: Any, ttl: int) -> None:
        await self._redis.setex(f"qcache:{key}", ttl, json.dumps(value, default=str))

    async def _redis_forget(self, key: str) -> bool:
        return await self._redis.delete(f"qcache:{key}") > 0

    async def _redis_forget_pattern(self, pattern: str) -> int:
        keys = []
        async for key in self._redis.scan_iter(f"qcache:{pattern}"):
            keys.append(key)
        if keys:
            return await self._redis.delete(*keys)
        return 0

    def __repr__(self) -> str:
        backend = "redis" if self._redis else "memory"
        return f"<QueryCache backend={backend} size={self.size}>"


class _CacheEntry:
    __slots__ = ("expires_at", "value")

    def __init__(self, value: Any, ttl: int) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class _TaggedCache:
    """Cache operations scoped to tags."""

    def __init__(self, cache: QueryCache, tags: set) -> None:
        self._cache = cache
        self._tags = tags
        self._prefix = "tag:" + ":".join(sorted(tags)) + ":"

    async def remember(self, key: str, ttl: int, callback: Callable) -> Any:
        full_key = self._prefix + key
        result = await self._cache.remember(full_key, ttl, callback)
        # Track key in tag set
        await self._track(full_key)
        return result

    async def get(self, key: str) -> Any | None:
        return await self._cache.get(self._prefix + key)

    async def put(self, key: str, value: Any, ttl: int = 300) -> None:
        full_key = self._prefix + key
        await self._cache.put(full_key, value, ttl)
        await self._track(full_key)

    async def flush(self) -> int:
        """Flush all keys with these tags."""
        return await self._cache.forget_pattern(self._prefix + "*")

    async def _track(self, key: str) -> None:
        """Track which keys belong to tag group."""
        tag_key = f"_tags:{self._prefix}"
        existing = await self._cache.get(tag_key) or []
        if key not in existing:
            existing.append(key)
            await self._cache.put(tag_key, existing, ttl=86400)


# ── Helper: cache key from query ──────────────────────────


def make_cache_key(prefix: str, query: Any, params: Any = None) -> str:
    """Generate deterministic cache key from SQL query."""
    raw = f"{prefix}:{query!s}:{params!s}"
    return hashlib.md5(raw.encode()).hexdigest()
