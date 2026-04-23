from __future__ import annotations

import contextlib
import copy
import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import (
    Any,
    TypeVar,
)

from ..exceptions import ConfigError, ConfigKeyError, FrozenConfigError
from .base import BaseConfiguration

T = TypeVar("T", bound=BaseConfiguration)


class ConfigResult:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return self._data

    def model_dump(self) -> dict[str, Any]:
        return self._data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data  # ✅ Для "app" in data

    def __iter__(self):
        return iter(self._data)  # ✅ Для итерации

    def __eq__(self, other) -> bool:
        if isinstance(other, ConfigResult):
            return self._data == other._data
        return self._data == other  # ✅ Для results == {}

    def __repr__(self) -> str:
        return f"ConfigResult({self._data})"

    def keys(self):
        return self._data.keys()


class ConfigSnapshot:
    def __init__(self, index: int, data: dict[str, Any]) -> None:
        self.index = index  # ty:ignore[unresolved-reference]
        self._data = data  # ty:ignore[unresolved-reference]

    def to_dict(self) -> dict[str, Any]:
        return self._data

    def model_dump(self) -> dict[str, Any]:
        return self._data

    def __int__(self) -> int:
        return self.index

    def __repr__(self) -> str:
        return f"ConfigSnapshot(index={self.index})"


class ConfigChangeEvent:
    """Lightweight event — no dependency on events module."""

    def __init__(self, key: str, old_value: Any, new_value: Any) -> None:
        self.key = key
        self.old_value = old_value
        self.new_value = new_value


class ConfigurationManager:
    def __init__(self, base_path: Path | None = None, *, log: Any | None = None) -> None:
        self._configs: dict[str, BaseConfiguration] = {}
        self._defaults: dict[str, BaseConfiguration] = {}
        self._overrides: dict[str, Any] = {}
        self._cache: dict[str, Any] = {}
        self._base_path = base_path or Path.cwd()
        self._loaded = False
        self._frozen = False
        self._snapshots: list[dict[str, Any]] = []
        self._on_change: list[Callable[[ConfigChangeEvent], None]] = []
        self._log = log

    async def load_from_path(self, path: Path | str) -> int:
        """Load config files, return count loaded."""
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = self._base_path / config_path

        if not config_path.exists():
            self._debug("Config path not found: %s", config_path)
            return 0

        loaded = 0
        for file in sorted(config_path.glob("*.py")):
            if file.name.startswith("_"):
                continue
            try:
                await self._load_config_file(file)
                loaded += 1
            except Exception as e:
                self._error("Failed to load config %s: %s", file.name, e)
                raise ConfigError(f"Failed to load config {file}: {e}") from e

        self._loaded = True
        self._info("Loaded %d config files from %s: %s", loaded, config_path, list(self._configs.keys()))
        return loaded

    async def _load_config_file(self, file: Path) -> None:
        module_name = f"config.{file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # ✅ Вариант 1: Ищем классы BaseConfiguration
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseConfiguration)
                and attr is not BaseConfiguration
                and not attr.__name__.startswith("_")
            ):
                try:
                    config_instance = attr()
                    config_name = config_instance.config_name()
                    self._configs[config_name] = config_instance
                    self._debug("Registered config class: %s → %s", config_name, attr.__name__)
                except Exception as e:
                    self._error("Failed to instantiate %s: %s", attr.__name__, e)

        # ✅ Вариант 2: Ищем словарь config = {...} (для совместимости)
        if hasattr(module, "config") and isinstance(module.config, dict):
            config_name = file.stem
            self._configs[config_name] = module.config
            self._debug("Registered config dict: %s", config_name)

    def register(self, config: BaseConfiguration, name: str | None = None) -> None:
        self._assert_not_frozen()
        config_name = name or config.config_name()
        self._configs[config_name] = config
        self._invalidate_cache()
        self._debug("Registered config: %s", config_name)

    def register_class(self, config_class: type[T], name: str | None = None) -> T:
        instance = config_class()
        self.register(instance, name)
        return instance

    def register_default(self, config: BaseConfiguration, name: str | None = None) -> None:
        config_name = name or config.config_name()
        self._defaults[config_name] = config
        if config_name not in self._configs:
            self._configs[config_name] = config

    def merge_defaults(self) -> None:
        for name, default_config in self._defaults.items():
            if name in self._configs:
                user_config = self._configs[name]
                if user_config is not default_config:
                    merged = default_config.merge(user_config.model_dump())
                    self._configs[name] = merged

    def get(self, key: str, default: Any = None) -> Any:
        cache_key = f"{key}:{id(default)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if key in self._overrides:
            return self._overrides[key]

        parts = key.split(".")
        if not parts:
            return default

        config_name = parts[0]
        if config_name not in self._configs:
            return default

        config = self._configs[config_name]
        if len(parts) == 1:
            value = config
        else:
            value: Any = config
            for part in parts[1:]:
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, (dict, Mapping)) and part in value:
                    value = value[part]  # ty:ignore[invalid-argument-type]
                else:
                    value = default
                    break

        self._cache[cache_key] = value
        return value

    def __getitem__(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise ConfigKeyError(f"Configuration key not found: {key}")
        return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def set(self, key: str, value: Any) -> None:
        self._assert_not_frozen()
        old = self.get(key)
        self._overrides[key] = value
        self._invalidate_cache()
        self._fire_change(key, old, value)

    def forget(self, key: str) -> bool:
        self._assert_not_frozen()
        if key in self._overrides:
            del self._overrides[key]
            self._invalidate_cache()
            return True
        return False

    def clear_overrides(self) -> None:
        self._assert_not_frozen()
        self._overrides.clear()
        self._invalidate_cache()

    def group(self, name: str) -> BaseConfiguration | None:
        return self._configs.get(name)

    def group_or_fail(self, name: str) -> BaseConfiguration:
        config = self._configs.get(name)
        if config is None:
            raise ConfigKeyError(f"Config group not found: {name}")
        return config

    def groups(self) -> list[str]:
        return list(self._configs.keys())

    def all(self) -> dict[str, Any]:
        result = {}
        for name, config in self._configs.items():
            result[name] = config.to_dict()
        return ConfigResult(result)  # ty:ignore[invalid-return-type]

    def freeze(self) -> ConfigurationManager:
        """Freeze config — no mutations allowed."""
        self._frozen = True
        self._info("Configuration frozen")
        return self

    def unfreeze(self) -> ConfigurationManager:
        self._frozen = False
        return self

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def _assert_not_frozen(self) -> None:
        if self._frozen:
            raise FrozenConfigError(
                "Configuration is frozen. Cannot modify in production. Use unfreeze() only in testing."
            )

    def snapshot(self) -> int:
        """Save current state. Returns snapshot index."""
        state = {
            "configs": {name: cfg.model_dump() for name, cfg in self._configs.items()},
            "overrides": copy.deepcopy(self._overrides),
        }
        self._snapshots.append(state)
        idx = len(self._snapshots) - 1
        self._debug("Snapshot saved: #%d", idx)
        return ConfigSnapshot(idx, state)  # ty:ignore[invalid-return-type]

    def rollback(self, index: int = -1) -> None:
        """Restore from snapshot."""
        self._assert_not_frozen()
        if not self._snapshots:
            raise ConfigError("No snapshots to rollback to")

        if isinstance(index, ConfigSnapshot):
            index = index.index

        state = self._snapshots[index]
        self._overrides = copy.deepcopy(state["overrides"])
        for name, data in state["configs"].items():
            if name in self._configs:
                cls = self._configs[name].__class__
                self._configs[name] = cls.model_validate(data)
        self._invalidate_cache()
        self._debug("Rolled back to snapshot #%d", index)

    def clear_snapshots(self) -> None:
        self._snapshots.clear()

    def validate_all(self) -> dict[str, list[str]]:
        """
        Validate all registered configs.
        Returns dict of {config_name: [errors]}.
        Empty dict = all valid.
        """
        errors: dict[str, list[str]] = {}
        for name, config in self._configs.items():
            if isinstance(config, dict):
                continue

            try:
                config.__class__.model_validate(config.model_dump())
            except Exception as e:
                errors[name] = [str(e)]
        return errors

    def assert_valid(self) -> None:
        """Raise if any config is invalid."""
        errors = self.validate_all()
        if errors:
            lines = []
            for name, errs in errors.items():
                for err in errs:
                    lines.append(f"  [{name}] {err}")
            raise ConfigError("Configuration validation failed:\n" + "\n".join(lines))

    def on_change(self, callback: Callable[[ConfigChangeEvent], None]) -> ConfigurationManager:
        """Register a callback for config changes."""
        self._on_change.append(callback)
        return self

    def _fire_change(self, key: str, old: Any, new: Any) -> None:
        if old == new:
            return
        event = ConfigChangeEvent(key, old, new)
        for cb in self._on_change:
            with contextlib.suppress(Exception):
                cb(event)

    def export_json(self, path: Path | str) -> None:
        """
        Export all config to JSON file — for fast production boot.
        Like Laravel's `php artisan config:cache`.
        """
        data = self.all()
        if hasattr(data, "_data"):
            data = data._data
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, default=str, indent=2, ensure_ascii=False), encoding="utf-8")
        self._info("Config exported to %s", path)

    def import_json(self, path: Path | str) -> bool:
        path = Path(path)

        if not path.exists():
            return False

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)

            for name, values in data.items():
                if name in self._configs:
                    cls = self._configs[name].__class__
                    self._configs[name] = cls.model_validate(values)

            for name, values in data.items():
                if name in self._configs:
                    cls = self._configs[name].__class__
                    self._configs[name] = cls.model_validate(values)
                else:
                    pass
            self._invalidate_cache()
            self._loaded = True
            return True
        except Exception:
            import traceback

            traceback.print_exc()
            return False

    def search(self, pattern: str) -> dict[str, Any]:
        """Search config keys by pattern (substring match)."""
        results = {}
        for name, config in self._configs.items():
            data = config.to_dict()
            self._search_recursive(name, data, pattern.lower(), results)
        return ConfigResult(results)  # ty:ignore[invalid-return-type]

    def _search_recursive(self, prefix: str, data: Any, pattern: str, results: dict[str, Any]) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}"
                if pattern in full_key.lower():
                    results[full_key] = value
                self._search_recursive(full_key, value, pattern, results)

    def refresh(self, name: str | None = None) -> None:
        self._assert_not_frozen()
        if name:
            if name in self._configs:
                config_class = self._configs[name].__class__
                self._configs[name] = config_class()
        else:
            for config_name in list(self._configs.keys()):
                config_class = self._configs[config_name].__class__
                self._configs[config_name] = config_class()
        self._invalidate_cache()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def is_production(self) -> bool:
        return self.get("app.env", "local") == "production"

    def is_local(self) -> bool:
        return self.get("app.env", "local") == "local"

    def is_testing(self) -> bool:
        return self.get("app.env", "local") in ("testing", "test")

    def is_debug(self) -> bool:
        return self.get("app.debug", False)

    def _debug(self, msg: str, *args: Any) -> None:
        if self._log and hasattr(self._log, "debug"):
            self._log.debug(msg.format(*args) if args else msg)

    def _info(self, msg: str, *args: Any) -> None:
        if self._log and hasattr(self._log, "info"):
            self._log.info(msg.format(*args) if args else msg)

    def _error(self, msg: str, *args: Any) -> None:
        if self._log and hasattr(self._log, "error"):
            self._log.error(msg.format(*args) if args else msg)

    def _invalidate_cache(self) -> None:
        self._cache.clear()

    def __repr__(self) -> str:
        status = "frozen" if self._frozen else "mutable"
        groups = list(self._configs.keys())
        return f"<ConfigurationManager groups={groups} [{status}]>"
