from __future__ import annotations

from typing import Any

# Lazy references — set by providers
_cache_manager = None
_encryptor = None
_hash_manager = None


def set_cache_manager(manager) -> None:
    global _cache_manager
    _cache_manager = manager


def set_encryptor(encryptor) -> None:
    global _encryptor
    _encryptor = encryptor


def set_hash_manager(manager) -> None:
    global _hash_manager
    _hash_manager = manager


# ── Cache Helpers ──────────────────────────────────


async def cache_get(key: str, default: Any = None) -> Any:
    """Get from default cache store."""
    _require(_cache_manager, "CacheManager")
    return await _cache_manager.get(key, default)  # ty:ignore[unresolved-attribute]


async def cache_put(key: str, value: Any, ttl: int | None = None) -> bool:
    """Put into default cache store."""
    _require(_cache_manager, "CacheManager")
    return await _cache_manager.put(key, value, ttl)  # ty:ignore[unresolved-attribute]


async def cache_forget(key: str) -> bool:
    """Remove from default cache store."""
    _require(_cache_manager, "CacheManager")
    return await _cache_manager.forget(key)  # ty:ignore[unresolved-attribute]


async def cache_has(key: str) -> bool:
    """Check if key exists in default cache store."""
    _require(_cache_manager, "CacheManager")
    return await _cache_manager.has(key)  # ty:ignore[unresolved-attribute]


async def cache_remember(key: str, ttl: int, callback) -> Any:
    """Get or compute & store."""
    _require(_cache_manager, "CacheManager")
    return await _cache_manager.remember(key, ttl, callback)  # ty:ignore[unresolved-attribute]


# ── Encryption Helpers ─────────────────────────────


def encrypt(value: str) -> str:
    """Encrypt a string."""
    _require(_encryptor, "Encryptor")
    return _encryptor.encrypt(value)  # ty:ignore[unresolved-attribute]


def decrypt(payload: str) -> str:
    """Decrypt a payload."""
    _require(_encryptor, "Encryptor")
    return _encryptor.decrypt(payload)  # ty:ignore[unresolved-attribute]


# ── Hashing Helpers ────────────────────────────────


async def hash_make(value: str, **options) -> str:
    """Hash a value (for passwords)."""
    _require(_hash_manager, "HashManager")
    return await _hash_manager.make(value, **options)  # ty:ignore[unresolved-attribute]


async def hash_check(plain: str, hashed: str) -> bool:
    """Check a plain value against a hash."""
    _require(_hash_manager, "HashManager")
    return await _hash_manager.check(plain, hashed)  # ty:ignore[unresolved-attribute]


def hash_needs_rehash(hashed: str) -> bool:
    """Check if hash needs rehashing."""
    _require(_hash_manager, "HashManager")
    return _hash_manager.needs_rehash(hashed)  # ty:ignore[unresolved-attribute]


def _require(instance, name: str) -> None:
    if instance is None:
        raise RuntimeError(f"{name} not initialized. Did you register the corresponding ServiceProvider?")
