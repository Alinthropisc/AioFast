from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..configuration.manager import ConfigurationManager

_config_manager: ConfigurationManager | None = None


def set_config_manager(manager) -> None:
    global _config_manager
    _config_manager = manager


def config(key: str, default: Any = None) -> Any:

    if _config_manager is None:
        raise RuntimeError("ConfigurationManager not initialized. Did you forget to register ConfigServiceProvider?")
    return _config_manager.get(key, default)
