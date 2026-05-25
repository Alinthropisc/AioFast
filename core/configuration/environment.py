from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

from pydantic import SecretStr

from ..exceptions import EnvironmentError, EnvironmentKeyError

if TYPE_CHECKING:
    import builtins

T = TypeVar("T")


class Environment:
    BOOL_TRUE_VALUES: builtins.set[str] = {
        "true",
        "1",
        "yes",
        "on",
        "enabled",
        "enable",
    }
    BOOL_FALSE_VALUES: builtins.set[str] = {
        "false",
        "0",
        "no",
        "off",
        "disabled",
        "disable",
        "",
    }

    def __init__(
        self,
        env_file: str | Path | None = None,
        env_files: builtins.list[str | Path] | None = None,
        *,
        load_system_env: builtins.bool = True,
        interpolate: builtins.bool = True,
        override: builtins.bool = True,
        base_path: str | Path | None = None,
    ) -> None:
        self._values: dict[str, str] = {}
        self._cache: dict[str, Any] = {}
        self._loaded_files: list[Path] = []
        self._interpolate = interpolate
        self._override = override
        self._base_path = Path(base_path) if base_path else Path.cwd()
        self._frozen: bool = False  # 🆕

        if load_system_env:
            self._values.update(os.environ)

        files_to_load: list[Path] = []
        if env_files:
            files_to_load.extend(self._resolve_path(f) for f in env_files)
        elif env_file:
            files_to_load.append(self._resolve_path(env_file))
        else:
            files_to_load = self._discover_env_files()

        for file in files_to_load:
            self._load_file(file)

    def get(self, key: str, default: Any = None) -> Any:
        cache_key = f"get:{key}:{type(default).__name__}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        raw = self._values.get(key)
        if raw is None:
            return default
        value = self._cast_to_type(raw, type(default)) if default is not None else raw
        self._cache[cache_key] = value
        return value

    def require(self, key: str) -> str:
        value = self._values.get(key)
        if value is None:
            raise EnvironmentKeyError(f"Required environment variable '{key}' is not set")
        return value

    def string(self, key: str, default: str = "") -> str:
        value = self._values.get(key)
        return value if value is not None else default

    def bool(self, key: str, default: bool = False) -> bool:  # ty:ignore[invalid-type-form]
        value = self._values.get(key)
        if value is None:
            return default
        lower = value.lower().strip()
        if lower in self.BOOL_TRUE_VALUES:
            return True
        if lower in self.BOOL_FALSE_VALUES:
            return False
        return default

    def int(self, key: str, default: int = 0) -> int:  # ty:ignore[invalid-type-form]
        value = self._values.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def float(self, key: str, default: float = 0.0) -> float:  # ty:ignore[invalid-type-form]
        value = self._values.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def list(
        self, key: str, default: builtins.list[str] | None = None, separator: str = ",", strip: builtins.bool = True
    ) -> builtins.list[str]:
        if default is None:
            default = []
        value = self._values.get(key)
        if value is None or value == "":
            return default
        items = value.split(separator)
        if strip:
            items = [item.strip() for item in items]
        return [item for item in items if item]

    def int_list(self, key: str, default: builtins.list[int] | None = None, separator: str = ",") -> builtins.list[int]:  # ty:ignore[invalid-type-form]
        if default is None:
            default = []
        str_list = self.list(key, [], separator)
        if not str_list:
            return default
        try:
            return [int(x) for x in str_list]
        except ValueError:
            return default

    def dict(self, key: str, default: builtins.dict[str, Any] | None = None) -> builtins.dict[str, Any]:
        if default is None:
            default = {}
        value = self._values.get(key)
        if value is None or value == "":
            return default
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else default
        except json.JSONDecodeError:
            return default

    def json(self, key: str, default: Any = None) -> Any:
        value = self._values.get(key)
        if value is None or value == "":
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def secret(self, key: str, default: str = "") -> SecretStr:
        return SecretStr(self.string(key, default))

    def path(self, key: str, default: Path | None = None) -> Path | None:
        value = self._values.get(key)
        if value is None:
            return default
        return Path(value)

    def url(self, key: str, default: str = "") -> str:
        value = self.string(key, default)
        return value.rstrip("/") if value else default

    def enum(self, key: str, allowed: builtins.list[str], default: str | None = None) -> str | None:
        value = self._values.get(key)
        if value is None or value not in allowed:
            return default
        return value

    def set(self, key: str, value: Any) -> None:
        self._assert_not_frozen()
        self._values[key] = str(value)
        self._invalidate_cache()

    def unset(self, key: str) -> bool:  # ty:ignore[invalid-type-form]
        self._assert_not_frozen()
        if key in self._values:
            del self._values[key]
            self._invalidate_cache()
            return True
        return False

    def clear(self) -> None:
        self._assert_not_frozen()
        self._values.clear()
        self._invalidate_cache()

    def has(self, key: str) -> bool:  # ty:ignore[invalid-type-form]
        return key in self._values

    def all(self) -> builtins.dict[str, str]:
        return self._values.copy()

    def keys(self) -> builtins.list[str]:
        return list(self._values.keys())

    def loaded_files(self) -> builtins.list[Path]:
        return self._loaded_files.copy()

    def validate(self, required: builtins.list[str]) -> builtins.list[str]:
        return [key for key in required if key not in self._values]

    def assert_required(self, required: builtins.list[str]) -> None:
        missing = self.validate(required)
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    def freeze(self) -> Environment:
        """Freeze — no more mutations allowed."""
        self._frozen = True
        return self

    def unfreeze(self) -> Environment:
        self._frozen = False
        return self

    @property
    def is_frozen(self) -> bool:  # ty:ignore[invalid-type-form]
        return self._frozen

    def _assert_not_frozen(self) -> None:
        if self._frozen:
            raise EnvironmentError("Environment is frozen, cannot modify")

    def prefix(self, prefix: str) -> builtins.dict[str, str]:
        """Get all vars with given prefix, stripped of prefix."""
        result = {}
        for key, value in self._values.items():
            if key.startswith(prefix):
                stripped = key[len(prefix) :]
                result[stripped] = value
        return result

    def snapshot(self) -> builtins.dict[str, str]:
        """Save current state for later rollback."""
        return self._values.copy()

    def rollback(self, snapshot: builtins.dict[str, str]) -> None:
        """Restore from snapshot."""
        self._assert_not_frozen()
        self._values = snapshot.copy()
        self._invalidate_cache()

    def reload(self) -> None:
        self._assert_not_frozen()
        files = self._loaded_files.copy()
        self._values.clear()
        self._loaded_files.clear()
        self._invalidate_cache()
        self._values.update(os.environ)
        for file in files:
            self._load_file(file)

    def load(self, path: str | Path | None = None) -> None:
        self._assert_not_frozen()
        if path:
            self._load_file(self._resolve_path(path))
        else:
            # Повторная логика обнаружения файлов из __init__
            files_to_load = self._discover_env_files()
            for file in files_to_load:
                self._load_file(file)
        self._invalidate_cache()

    def load_file(self, path: str | Path) -> bool:  # ty:ignore[invalid-type-form]
        return self._load_file(self._resolve_path(path))

    def dump(self, mask_secrets: bool = True, patterns: builtins.list[str] | None = None) -> builtins.dict[str, str]:  # ty:ignore[invalid-type-form]
        secret_patterns = [
            "secret",
            "password",
            "key",
            "token",
            "auth",
            "credential",
            "private",
            "dsn",
        ]
        if patterns:
            secret_patterns.extend(patterns)
        result = {}
        for key, value in sorted(self._values.items()):
            if mask_secrets:
                key_lower = key.lower()
                if any(p in key_lower for p in secret_patterns):
                    result[key] = "***MASKED***"
                    continue
            result[key] = value
        return result

    def _resolve_path(self, path: str | Path) -> Path:
        p = Path(path)
        if not p.is_absolute():
            return self._base_path / p
        return p

    def _discover_env_files(self) -> builtins.list[Path]:
        app_env = os.getenv("APP_ENV", "local")
        candidates = [
            ".env",
            ".env.local",
            f".env.{app_env}",
            f".env.{app_env}.local",
        ]
        if "pytest" in sys.modules:
            candidates.append(".env.testing")
        return [self._base_path / name for name in candidates if (self._base_path / name).exists()]

    def _load_file(self, path: Path) -> bool:  # ty:ignore[invalid-type-form]
        if not path.exists():
            return False
        try:
            content = path.read_text(encoding="utf-8")
            parsed = self._parse_env_content(content)
            if self._override:
                self._values.update(parsed)
            else:
                for key, value in parsed.items():
                    if key not in self._values:
                        self._values[key] = value
            self._loaded_files.append(path)
            self._invalidate_cache()
            return True
        except Exception as e:
            raise EnvironmentError(f"Failed to load {path}: {e}") from e

    def _parse_env_content(self, content: str) -> builtins.dict[str, str]:
        result: dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not (value.startswith('"') or value.startswith("'")):
                comment_idx = value.find("#")
                if comment_idx > 0:
                    value = value[:comment_idx].strip()
            if len(value) >= 2:  # noqa: SIM102
                if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                    value = value[1:-1]
            result[key] = value
        if self._interpolate:
            result = self._interpolate_values(result)
        return result

    def _interpolate_values(self, values: builtins.dict[str, str]) -> builtins.dict[str, str]:
        pattern = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
        result = values.copy()
        for _ in range(10):
            changed = False
            for key, value in list(result.items()):
                if not isinstance(value, str) or "$" not in value:
                    continue

                def replace(match: re.Match) -> str:
                    var_name = match.group(1) or match.group(2)
                    if var_name in result:
                        return result[var_name]
                    if var_name in self._values:
                        return self._values[var_name]
                    return match.group(0)

                new_value = pattern.sub(replace, value)

                if new_value != value:
                    result[key] = new_value
                    changed = True
            if not changed:
                break
        return result

    def _cast_to_type(self, value: str, target_type: type) -> Any:
        if target_type is bool:
            return value.lower().strip() in self.BOOL_TRUE_VALUES
        if target_type is int:
            try:
                return int(value)
            except ValueError:
                return 0
        if target_type is float:
            try:
                return float(value)
            except ValueError:
                return 0.0
        if target_type is list:
            return value.split(",") if value else []
        if target_type is dict:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        return value

    def _invalidate_cache(self) -> None:
        self._cache.clear()

    def __call__(self, key: str, default: Any = None) -> Any:
        return self.get(key, default)

    def __contains__(self, key: str) -> bool:  # ty:ignore[invalid-type-form]
        return self.has(key)

    def __getitem__(self, key: str) -> str:
        return self.require(key)

    def __len__(self) -> int:  # ty:ignore[invalid-type-form]
        return len(self._values)

    def __repr__(self) -> str:
        status = "frozen" if self._frozen else "mutable"
        return f"<Environment keys={len(self._values)} files={len(self._loaded_files)} [{status}]>"
