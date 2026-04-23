from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class SecretsResolver:
    """
    Resolve secrets from multiple backends.

    Supports:
      - Environment variables (default)
      - Files (/run/secrets/*, Docker secrets)
      - Custom resolvers (Vault, AWS SSM, etc.)

    Usage:
        secrets = SecretsResolver()
        secrets.add_file_backend("/run/secrets")
        secrets.add_resolver("vault", vault_resolver)

        db_password = secrets.resolve("DB_PASSWORD")
        # Tries: env → files → custom resolvers
    """

    def __init__(self) -> None:
        self._file_paths: list[Path] = []
        self._resolvers: dict[str, Callable[[str], str | None]] = {}
        self._cache: dict[str, str] = {}
        self._prefix_map: dict[str, str] = {}  # env prefix → resolver

    def add_file_backend(self, path: str | Path) -> SecretsResolver:
        """Add a directory to search for secret files (e.g. Docker secrets)."""
        p = Path(path)
        if p.exists() and p.is_dir():
            self._file_paths.append(p)
        return self

    def add_resolver(self, name: str, resolver: Callable[[str], str | None]) -> SecretsResolver:
        """Add custom resolver function. Called with key, returns value or None."""
        self._resolvers[name] = resolver
        return self

    def map_prefix(self, prefix: str, resolver_name: str) -> SecretsResolver:
        """Map env prefix to a specific resolver.
        e.g. map_prefix("vault://", "vault")
        """
        self._prefix_map[prefix] = resolver_name
        return self

    def resolve(self, key: str, default: str | None = None) -> str | None:
        """Resolve a secret by key. Priority: cache → prefix → env → files → resolvers."""
        if key in self._cache:
            return self._cache[key]

        # Check prefix mappings
        for prefix, resolver_name in self._prefix_map.items():
            if key.startswith(prefix):
                real_key = key[len(prefix) :]
                resolver = self._resolvers.get(resolver_name)
                if resolver:
                    value = resolver(real_key)
                    if value is not None:
                        self._cache[key] = value
                        return value

        # Environment variable
        env_value = os.environ.get(key)
        if env_value is not None:
            self._cache[key] = env_value
            return env_value

        # File-based secrets
        for dir_path in self._file_paths:
            file_path = dir_path / key
            if file_path.is_file():
                value = file_path.read_text(encoding="utf-8").strip()
                self._cache[key] = value
                return value

            # Try lowercase
            file_path_lower = dir_path / key.lower()
            if file_path_lower.is_file():
                value = file_path_lower.read_text(encoding="utf-8").strip()
                self._cache[key] = value
                return value

        # Custom resolvers (in order)
        for _name, resolver in self._resolvers.items():
            try:
                value = resolver(key)
                if value is not None:
                    self._cache[key] = value
                    return value
            except Exception:
                continue
        return default

    def resolve_many(self, keys: list[str]) -> dict[str, str | None]:
        """Resolve multiple secrets at once."""
        return {key: self.resolve(key) for key in keys}

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def decode_base64(value: str) -> str:
        """Decode a base64-encoded secret."""
        if value.startswith("base64:"):
            value = value[7:]
        return base64.b64decode(value).decode("utf-8")

    def __repr__(self) -> str:
        return f"<SecretsResolver file_paths={len(self._file_paths)} resolvers={list(self._resolvers.keys())} cached={len(self._cache)}>"
