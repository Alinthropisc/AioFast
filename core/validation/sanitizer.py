from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable  # noqa: TC003
from typing import Any


class Sanitizer:
    """
    Data sanitizer — clean/transform data BEFORE validation.

    Like Laravel's prepareForValidation().

    Usage:
        sanitizer = Sanitizer({
            "name": ["trim", "title_case"],
            "email": ["trim", "lowercase"],
            "bio": ["trim", "strip_tags"],
            "slug": ["trim", "lowercase", "slug"],
            "phone": [strip_non_digits],  # custom callable
        })

        clean = sanitizer.sanitize({
            "name": "  john DOE  ",
            "email": "  John@Example.COM ",
            "bio": "<script>alert('xss')</script>Hello",
        })
        # → {"name": "John Doe", "email": "john@example.com", "bio": "Hello"}
    """

    # Built-in sanitizers
    SANITIZERS: dict[str, Callable[[Any], Any]] = {}  # noqa: RUF012

    def __init__(
        self,
        field_sanitizers: dict[str, list[str | Callable]] = None,  # noqa: RUF013  # ty:ignore[invalid-parameter-default]
        *,
        global_sanitizers: list[str | Callable] | None = None,
    ) -> None:  # ty:ignore[invalid-parameter-default]
        self._field_sanitizers = field_sanitizers or {}
        self._global = global_sanitizers or []

    def sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply sanitizers to data. Returns new dict."""
        result = dict(data)

        # Global sanitizers (apply to all string values)
        for key, _value in result.items():
            for s in self._global:
                result[key] = self._apply(s, result[key])

        # Field-specific sanitizers
        for field, sanitizers in self._field_sanitizers.items():
            if field in result:
                for s in sanitizers:
                    result[field] = self._apply(s, result[field])

        return result

    def _apply(self, sanitizer: str | Callable, value: Any) -> Any:
        if not isinstance(value, str):
            if callable(sanitizer) and not isinstance(sanitizer, str):
                return sanitizer(value)
            return value

        if isinstance(sanitizer, str):
            fn = self.SANITIZERS.get(sanitizer)
            if fn is None:
                raise ValueError(f"Unknown sanitizer: {sanitizer}")
            return fn(value)

        if callable(sanitizer):
            return sanitizer(value)

        return value

    def __repr__(self) -> str:
        return f"<Sanitizer fields={list(self._field_sanitizers.keys())}>"


# ── Register built-in sanitizers ──────────────────────────


def _trim(value: str) -> str:
    return value.strip()


def _ltrim(value: str) -> str:
    return value.lstrip()


def _rtrim(value: str) -> str:
    return value.rstrip()


def _lowercase(value: str) -> str:
    return value.lower()


def _uppercase(value: str) -> str:
    return value.upper()


def _title_case(value: str) -> str:
    return value.title()


def _capitalize(value: str) -> str:
    return value.capitalize()


def _strip_tags(value: str) -> str:
    """Remove HTML tags."""
    return re.sub(r"<[^>]+>", "", value)


def _escape_html(value: str) -> str:
    return html.escape(value)


def _slug(value: str) -> str:
    """Convert to URL slug."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def _strip_whitespace(value: str) -> str:
    """Remove ALL whitespace."""
    return re.sub(r"\s+", "", value)


def _collapse_whitespace(value: str) -> str:
    """Replace multiple spaces with one."""
    return re.sub(r"\s+", " ", value).strip()


def _strip_non_digits(value: str) -> str:
    """Keep only digits."""
    return re.sub(r"\D", "", value)


def _normalize_newlines(value: str) -> str:
    """Normalize to \\n."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _nullify_empty(value: str) -> str | None:
    """Convert empty strings to None."""
    return None if value.strip() == "" else value


# Register all
Sanitizer.SANITIZERS = {
    "trim": _trim,
    "ltrim": _ltrim,
    "rtrim": _rtrim,
    "lowercase": _lowercase,
    "lower": _lowercase,
    "uppercase": _uppercase,
    "upper": _uppercase,
    "title_case": _title_case,
    "title": _title_case,
    "capitalize": _capitalize,
    "strip_tags": _strip_tags,
    "escape_html": _escape_html,
    "escape": _escape_html,
    "slug": _slug,
    "strip_whitespace": _strip_whitespace,
    "collapse_whitespace": _collapse_whitespace,
    "strip_non_digits": _strip_non_digits,
    "digits_only": _strip_non_digits,
    "normalize_newlines": _normalize_newlines,
    "nullify_empty": _nullify_empty,
}
