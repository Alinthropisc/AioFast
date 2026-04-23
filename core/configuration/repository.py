from __future__ import annotations

from typing import Any

_MISSING = object()


class Repository:
    def __init__(self, items: dict[str, Any] | None = None) -> None:
        self._items: dict[str, Any] = items or {}

    # ── Read ──────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with dot-notation support."""
        parts = key.split(".")
        current: Any = self._items

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return default

        return current

    def has(self, key: str) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    def all(self) -> dict[str, Any]:
        return dict(self._items)

    def keys(self) -> list[str]:
        return list(self._items.keys())

    # ── Write ─────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """Set value with dot-notation support."""
        parts = key.split(".")
        current = self._items

        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def forget(self, key: str) -> bool:
        """Remove a key. Returns True if existed."""
        parts = key.split(".")
        current = self._items

        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return dict(self._items)

    def merge(self, other: dict[str, Any]) -> Repository:
        """Return new Repository with merged data."""
        merged = _deep_merge(self._items, other)
        return Repository(merged)

    def __getitem__(self, key: str) -> Any:
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __repr__(self) -> str:
        return f"<Repository keys={list(self._items.keys())}>"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
