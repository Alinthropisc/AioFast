from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class ConfigCache:
    """
    Cache config to file for fast boot — like `php artisan config:cache`.

    Usage:
        cache = ConfigCache("bootstrap/cache")

        # Save
        cache.store(manager.all())

        # Load (returns None if stale/missing)
        data = cache.load(max_age=3600)

        # Clear
        cache.clear()
    """

    DEFAULT_FILE = "config.json"

    def __init__(self, cache_dir: str | Path = "bootstrap/cache", filename: str = DEFAULT_FILE) -> None:
        self._dir = Path(cache_dir)
        self._file = self._dir / filename
        self._hash_file = self._dir / f"{filename}.hash"

    def store(self, data: dict[str, Any], *, source_hash: str | None = None) -> Path:
        """Serialize config to cache file."""
        self._dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "_cached_at": time.time(),
            "_hash": source_hash or self._compute_hash(data),
            "data": data,
        }

        self._file.write_text(json.dumps(payload, default=str, indent=2, ensure_ascii=False), encoding="utf-8")
        return self._file

    def load(self, *, max_age: float | None = None) -> dict[str, Any] | None:
        """Load cached config. Returns None if missing/stale."""
        if not self._file.exists():
            return None

        try:
            payload = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check age
        if max_age is not None:
            cached_at = payload.get("_cached_at", 0)
            if time.time() - cached_at > max_age:
                return None
        return payload.get("data")

    def is_cached(self) -> bool:
        return self._file.exists()

    def is_stale(self, current_data: dict[str, Any]) -> bool:
        """Check if cache is stale compared to current config."""
        if not self._file.exists():
            return True
        try:
            payload = json.loads(self._file.read_text(encoding="utf-8"))
            cached_hash = payload.get("_hash", "")
            current_hash = self._compute_hash(current_data)
            return cached_hash != current_hash
        except Exception:
            return True

    def clear(self) -> bool:
        """Remove cache file."""
        removed = False
        if self._file.exists():
            self._file.unlink()
            removed = True
        if self._hash_file.exists():
            self._hash_file.unlink()
        return removed

    @property
    def path(self) -> Path:
        return self._file

    @staticmethod
    def _compute_hash(data: dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def __repr__(self) -> str:
        status = "cached" if self.is_cached() else "empty"
        return f"<ConfigCache path={self._file} [{status}]>"
