from __future__ import annotations

from typing import Any

from ..configuration import Environment

_env_instance: Environment | None = None


def get_env() -> Environment:
    global _env_instance

    if _env_instance is None:
        _env_instance = Environment()

    return _env_instance


def set_environment(environment) -> None:
    global _env_instance
    _env_instance = environment


def env(key: str, default: Any = None) -> Any:
    if _env_instance is not None:
        return _env_instance.get(key, default)

    # Fallback to os.environ
    import os

    value = os.getenv(key)
    if value is None:
        return default

    # Auto-cast based on default type
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value
