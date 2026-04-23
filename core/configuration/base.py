from __future__ import annotations

import os
import re
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound="BaseConfiguration")


class NestedConfig(BaseModel):
    model_config = SettingsConfigDict(extra="ignore", validate_default=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class BaseConfiguration(BaseSettings):
    __config_name__: ClassVar[str] = ""
    __env_prefix__: ClassVar[str | None] = None
    __frozen__: ClassVar[bool] = False  # 🆕 freeze support

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
        arbitrary_types_allowed=True,
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        skip_names = {
            "BaseConfiguration",
            "NestedConfig",
            "EnvironmentAwareConfig",
        }
        if cls.__name__ in skip_names:
            return
        prefix = cls._get_prefix()
        if prefix:
            parent_config: dict[str, Any] = {}
            if hasattr(cls, "model_config") and cls.model_config:
                parent_config = dict(cls.model_config)  # ty:ignore[no-matching-overload]
            parent_config.pop("env_prefix", None)
            cls.model_config = SettingsConfigDict(**parent_config, env_prefix=prefix)

    @classmethod
    def _get_prefix(cls) -> str:
        if cls.__env_prefix__ is not None:
            prefix = cls.__env_prefix__
            return prefix if prefix.endswith("_") else f"{prefix}_"
        name = cls.__name__
        for suffix in ("Configuration", "Config", "Settings"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()
        return f"{snake}_"

    @classmethod
    def config_name(cls) -> str:
        if cls.__config_name__:
            return cls.__config_name__
        name = cls.__name__
        for suffix in ("Configuration", "Config", "Settings"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        return name.lower()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name in self.model_fields:
            value = getattr(self, field_name)
            if isinstance(value, SecretStr):
                result[field_name] = "***SECRET***"
            elif hasattr(value, "to_dict") and callable(value.to_dict):
                result[field_name] = value.to_dict()
            elif isinstance(value, list):
                result[field_name] = [v.to_dict() if hasattr(v, "to_dict") else v for v in value]
            elif isinstance(value, dict):
                result[field_name] = {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in value.items()}
            else:
                result[field_name] = value
        return result

    def to_safe_dict(self) -> dict[str, Any]:
        """🆕 Like to_dict but masks ALL sensitive fields."""
        result = self.to_dict()
        sensitive = {"key", "secret", "password", "token", "dsn", "credential"}
        return self._mask_recursive(result, sensitive)

    @staticmethod
    def _mask_recursive(data: dict, patterns: set[str]) -> dict:
        result = {}
        for k, v in data.items():
            if any(p in k.lower() for p in patterns):
                result[k] = "***MASKED***"
            elif isinstance(v, dict):
                result[k] = BaseConfiguration._mask_recursive(v, patterns)
            else:
                result[k] = v
        return result

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        value: Any = self
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def has(self, key: str) -> bool:
        return key in self.model_fields or hasattr(self, key)

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def keys(self) -> list[str]:
        """🆕 List all field names."""
        return list(self.model_fields.keys())

    def merge(self, other: dict[str, Any] | BaseConfiguration) -> BaseConfiguration:
        current = self.model_dump()
        other_data = other.model_dump() if isinstance(other, BaseConfiguration) else other
        merged = self._deep_merge(current, other_data)
        return self.__class__.model_validate(merged)

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = BaseConfiguration._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def from_env_file(cls: type[T], path: str) -> T:
        return cls(_env_file=path)  # ty:ignore[unknown-argument]

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        return cls.model_validate(data)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.config_name()!r} prefix={self._get_prefix()!r}>"


class EnvironmentAwareConfig(BaseConfiguration):
    @model_validator(mode="after")
    def apply_environment_overrides(self) -> EnvironmentAwareConfig:
        env = os.getenv("APP_ENV", "local")
        method_name = f"configure_{env}"
        if hasattr(self, method_name):
            getattr(self, method_name)()
        return self
