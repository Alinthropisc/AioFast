from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """
    Structured validation error.

    Holds per-field error messages in a dict.

    Usage:
        raise ValidationError({
            "email": ["Invalid email format"],
            "age": ["Must be at least 18", "Must be a number"],
        })

        except ValidationError as e:
            print(e.errors)   → {"email": [...], "age": [...]}
            print(e.first())  → "Invalid email format"
            print(e.to_response())  → {"success": False, ...}
    """

    def __init__(self, errors: dict[str, list[str]] | str | list[str], message: str = "Validation failed") -> None:
        self.message = message

        if isinstance(errors, str):
            self.errors: dict[str, list[str]] = {"_general": [errors]}
        elif isinstance(errors, list):
            self.errors = {"_general": errors}
        else:
            self.errors = errors
        super().__init__(message)

    @property
    def failed_fields(self) -> list[str]:
        """List of fields that failed validation."""
        return [k for k in self.errors if k != "_general"]

    @property
    def all_messages(self) -> list[str]:
        """Flat list of all error messages."""
        result: list[str] = []
        for msgs in self.errors.values():
            result.extend(msgs)
        return result

    def first(self, field: str | None = None) -> str | None:
        """Get first error message for a field (or first overall)."""
        if field:
            msgs = self.errors.get(field, [])
            return msgs[0] if msgs else None
        for msgs in self.errors.values():
            if msgs:
                return msgs[0]
        return None

    def has(self, field: str) -> bool:
        """Check if field has errors."""
        return field in self.errors and len(self.errors[field]) > 0

    def get(self, field: str) -> list[str]:
        """Get error messages for a field."""
        return self.errors.get(field, [])

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "message": self.message,
            "errors": self.errors,
        }

    def to_response(self, status: int = 422) -> dict[str, Any]:
        """Convert to standard API error response."""
        return {
            "success": False,
            "message": self.message,
            "status": status,
            "errors": self.errors,
        }

    def merge(self, other: ValidationError) -> ValidationError:
        """Merge errors from another ValidationError."""
        for field, msgs in other.errors.items():
            if field in self.errors:
                self.errors[field].extend(msgs)
            else:
                self.errors[field] = list(msgs)
        return self

    def __bool__(self) -> bool:
        """True if there are errors."""
        return bool(self.errors)

    def __len__(self) -> int:
        return sum(len(msgs) for msgs in self.errors.values())

    def __repr__(self) -> str:
        count = len(self)
        fields = len(self.errors)
        return f"<ValidationError fields={fields} messages={count}>"


class FieldError:
    """Builder for field-level errors."""

    __slots__ = ("_field", "_messages")

    def __init__(self, field: str) -> None:
        self._field = field
        self._messages: list[str] = []

    def add(self, message: str) -> FieldError:
        self._messages.append(message)
        return self

    @property
    def field(self) -> str:
        return self._field

    @property
    def messages(self) -> list[str]:
        return list(self._messages)

    @property
    def has_errors(self) -> bool:
        return len(self._messages) > 0


class ErrorBag:
    """
    Collects field errors before raising.

    Usage:
        bag = ErrorBag()
        bag.add("email", "Required")
        bag.add("email", "Invalid format")
        bag.add("age", "Must be 18+")

        if bag.has_errors:
            raise bag.to_exception()
    """

    def __init__(self) -> None:
        self._errors: dict[str, list[str]] = {}

    def get(self, field, default=None):
        return self._errors.get(field, default)

    def add(self, field: str, message: str) -> ErrorBag:
        if field not in self._errors:
            self._errors[field] = []
        self._errors[field].append(message)
        return self

    def add_many(self, field: str, messages: list[str]) -> ErrorBag:
        for msg in messages:
            self.add(field, msg)
        return self

    def merge(self, errors: dict[str, list[str]]) -> ErrorBag:
        for field, msgs in errors.items():
            self.add_many(field, msgs)
        return self

    @property
    def has_errors(self) -> bool:
        return bool(self._errors)

    @property
    def errors(self) -> dict[str, list[str]]:
        return dict(self._errors)

    def first(self, field: str | None = None) -> str | None:
        if field:
            msgs = self._errors.get(field, [])
            return msgs[0] if msgs else None
        for msgs in self._errors.values():
            if msgs:
                return msgs[0]
        return None

    def to_exception(self, message: str = "Validation failed") -> ValidationError:
        return ValidationError(self._errors, message)

    def raise_if_errors(self, message: str = "Validation failed") -> None:
        if self.has_errors:
            raise self.to_exception(message)

    def clear(self) -> None:
        self._errors.clear()

    def __bool__(self) -> bool:
        return self.has_errors

    def __len__(self) -> int:
        return sum(len(msgs) for msgs in self._errors.values())

    def __repr__(self) -> str:
        return f"<ErrorBag errors={len(self._errors)} messages={len(self)}>"
