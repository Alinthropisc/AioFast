from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from .errors import ValidationError

T = TypeVar("T", bound="DTO")


class DTO(BaseModel):
    """
    Data Transfer Object — pydantic-based.

    Like Laravel's FormRequest but simpler.
    Validates and transforms input data.

    Usage:
        class CreateUserDTO(DTO):
            name: str
            email: str
            age: int = 18

        # From dict
        dto = CreateUserDTO.from_data({"name": "Alice", "email": "a@b.com"})

        # From dict with validation error formatting
        try:
            dto = CreateUserDTO.create(raw_data)
        except ValidationError as e:
            return e.to_response()

        # Access validated data
        print(dto.name, dto.email)
        print(dto.to_dict())
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_default=True)

    @classmethod
    def create(cls: type[T], data: dict[str, Any]) -> T:
        """Create DTO from dict. Raises our ValidationError on failure."""
        try:
            return cls.model_validate(data)
        except PydanticValidationError as e:
            raise cls._convert_pydantic_errors(e) from e

    @classmethod
    def create_or_none(cls: type[T], data: dict[str, Any]) -> T | None:
        """Create DTO or return None if invalid."""
        try:
            return cls.create(data)
        except ValidationError:
            return None

    @classmethod
    def create_many(cls: type[T], items: list[dict[str, Any]]) -> list[T]:
        """Create multiple DTOs from list of dicts."""
        return [cls.create(item) for item in items]

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """Convert to dict."""
        return self.model_dump(exclude_none=exclude_none)

    def to_dict_only(self, *fields: str) -> dict[str, Any]:
        """Convert to dict with only specified fields."""
        return self.model_dump(include=set(fields))

    def to_dict_except(self, *fields: str) -> dict[str, Any]:
        """Convert to dict excluding specified fields."""
        return self.model_dump(exclude=set(fields))

    @classmethod
    def fields(cls) -> list[str]:
        """List field names."""
        return list(cls.model_fields.keys())

    @classmethod
    def required_fields(cls) -> list[str]:
        """List required field names."""
        return [name for name, field in cls.model_fields.items() if field.is_required()]

    @classmethod
    def _convert_pydantic_errors(cls, exc: PydanticValidationError) -> ValidationError:
        """Convert pydantic errors to our ValidationError format."""
        errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            if field not in errors:
                errors[field] = []
            errors[field].append(msg)
        return ValidationError(errors)

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"<{self.__class__.__name__} {fields}>"


class UpdateDTO(DTO):
    """
    DTO for update operations — all fields optional.

    Usage:
        class UpdateUserDTO(UpdateDTO):
            name: Optional[str] = None
            email: Optional[str] = None
            age: Optional[int] = None

        dto = UpdateUserDTO.create({"name": "New Name"})
        changes = dto.changes()  # {"name": "New Name"} — only non-None
    """

    def changes(self) -> dict[str, Any]:
        """Return only fields that were explicitly set (non-None)."""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    @property
    def has_changes(self) -> bool:
        return bool(self.changes())
