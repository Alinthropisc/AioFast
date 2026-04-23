from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


class Rule(ABC):
    """
    Base validation rule — Strategy pattern.

    Each rule validates a single field value.

    Usage:
        class Uppercase(Rule):
            message = "Must be uppercase"

            def passes(self, field, value):
                return isinstance(value, str) and value.isupper()
    """

    message: str = "Validation failed for {field}"

    @abstractmethod
    def passes(self, field: str, value: Any) -> bool:
        """Return True if value passes validation."""

    def get_message(self, field: str, value: Any) -> str:
        return self.message.format(field=field, value=value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ── String rules ──────────────────────────────────────────


class Required(Rule):
    message = "The {field} field is required"

    def passes(self, field: str, value: Any) -> bool:
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")


class StringRule(Rule):
    message = "The {field} must be a string"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, str)


class MinLength(Rule):
    def __init__(self, min_len: int) -> None:
        self.min_len = min_len
        self.message = "The {field} must be at least " + str(min_len) + " characters"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, (str, list)):
            return False
        return len(value) >= self.min_len


class MaxLength(Rule):
    def __init__(self, max_len: int) -> None:
        self.max_len = max_len
        self.message = "The {field} must not exceed " + str(max_len) + " characters"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, (str, list)):
            return False
        return len(value) <= self.max_len


class Between(Rule):
    def __init__(self, min_len: int, max_len: int) -> None:
        self.min_len = min_len
        self.max_len = max_len
        self.message = f"The {{field}} must be between {min_len} and {max_len} characters"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, (str, list)):
            return False
        return self.min_len <= len(value) <= self.max_len


class Email(Rule):
    message = "The {field} must be a valid email address"
    _pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self._pattern.match(value))


class Url(Rule):
    message = "The {field} must be a valid URL"
    _pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self._pattern.match(value))


class Regex(Rule):
    def __init__(self, pattern: str, message: str = "") -> None:
        self._compiled = re.compile(pattern)
        self.message = message or "The {field} format is invalid"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self._compiled.match(value))


class Alpha(Rule):
    message = "The {field} must only contain letters"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, str) and value.isalpha()


class AlphaNumeric(Rule):
    message = "The {field} must only contain letters and numbers"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, str) and value.isalnum()


class Slug(Rule):
    message = "The {field} must be a valid slug (lowercase, hyphens, no spaces)"
    _pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, str) and bool(self._pattern.match(value))


# ── Numeric rules ─────────────────────────────────────────


class Numeric(Rule):
    message = "The {field} must be a number"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)


class Integer(Rule):
    message = "The {field} must be an integer"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)


class Min(Rule):
    def __init__(self, minimum: int | float) -> None:
        self.minimum = minimum
        self.message = f"The {{field}} must be at least {minimum}"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        return value >= self.minimum


class Max(Rule):
    def __init__(self, maximum: int | float) -> None:
        self.maximum = maximum
        self.message = f"The {{field}} must not exceed {maximum}"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        return value <= self.maximum


class Positive(Rule):
    message = "The {field} must be positive"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


# ── Choice rules ──────────────────────────────────────────


class In(Rule):
    def __init__(self, choices: Sequence[Any]) -> None:
        self.choices = list(choices)
        self.message = f"The {{field}} must be one of: {', '.join(str(c) for c in choices)}"

    def passes(self, field: str, value: Any) -> bool:
        return value in self.choices


class NotIn(Rule):
    def __init__(self, excluded: Sequence[Any]) -> None:
        self.excluded = list(excluded)
        self.message = f"The {{field}} must not be: {', '.join(str(c) for c in excluded)}"

    def passes(self, field: str, value: Any) -> bool:
        return value not in self.excluded


# ── Type rules ────────────────────────────────────────────


class IsType(Rule):
    def __init__(self, expected: type, type_name: str = "") -> None:
        self.expected = expected
        name = type_name or expected.__name__
        self.message = f"The {{field}} must be of type {name}"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, self.expected)


class IsList(Rule):
    message = "The {field} must be a list"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, list)


class IsDict(Rule):
    message = "The {field} must be a dictionary"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, dict)


class IsBool(Rule):
    message = "The {field} must be a boolean"

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, bool)


# ── Comparison rules ──────────────────────────────────────


class Equals(Rule):
    def __init__(self, expected: Any) -> None:
        self.expected = expected
        self.message = f"The {{field}} must equal {expected!r}"

    def passes(self, field: str, value: Any) -> bool:
        return value == self.expected


class Confirmed(Rule):
    """Value must match {field}_confirmation in data."""

    message = "The {field} confirmation does not match"

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        confirm_key = f"{field}_confirmation"
        return self._data.get(confirm_key) == value


# ── Callable rule ─────────────────────────────────────────


class CallableRule(Rule):
    """Wrap a function as a rule."""

    def __init__(self, fn: Callable[[Any], bool], message: str = "The {field} is invalid") -> None:
        self._fn = fn
        self.message = message

    def passes(self, field: str, value: Any) -> bool:
        return self._fn(value)


# ── Factory helpers ───────────────────────────────────────


def rule(fn: Callable[[Any], bool], message: str = "The {field} is invalid") -> CallableRule:
    """Create a rule from a function."""
    return CallableRule(fn, message)


# ── String-based rule parsing (Laravel-like) ──────────────

RULE_MAP: dict[str, Callable[..., Rule]] = {
    "required": lambda: Required(),
    "string": lambda: StringRule(),
    "email": lambda: Email(),
    "url": lambda: Url(),
    "alpha": lambda: Alpha(),
    "alpha_numeric": lambda: AlphaNumeric(),
    "slug": lambda: Slug(),
    "numeric": lambda: Numeric(),
    "integer": lambda: Integer(),
    "positive": lambda: Positive(),
    "list": lambda: IsList(),
    "dict": lambda: IsDict(),
    "bool": lambda: IsBool(),
    "min": lambda v: Min(float(v)),
    "max": lambda v: Max(float(v)),
    "min_length": lambda v: MinLength(int(v)),
    "max_length": lambda v: MaxLength(int(v)),
    "between": lambda a, b: Between(int(a), int(b)),
    "in": lambda *vals: In(list(vals)),
    "not_in": lambda *vals: NotIn(list(vals)),
    "regex": lambda p: Regex(p),
    "confirmed": lambda: Confirmed(),
    "password": lambda: Password(),
    "date": lambda: DateFormat(),
    "date_format": lambda f: DateFormat(f),
    "before": lambda d: DateBefore(d),
    "after": lambda d: DateAfter(d),
    "ip": lambda: IpAddress(),
    "uuid": lambda: Uuid(),
    "json_string": lambda: Json(),
}


def parse_rule_string(rule_str: str) -> Rule:
    """
    Parse Laravel-style rule string into Rule object.

    "required"           → Required()
    "min_length:3"       → MinLength(3)
    "in:active,inactive" → In(["active", "inactive"])
    "between:1,100"      → Between(1, 100)
    """
    if ":" in rule_str:
        name, params_str = rule_str.split(":", 1)
        params = params_str.split(",")
    else:
        name = rule_str
        params = []

    name = name.strip().lower()
    factory = RULE_MAP.get(name)
    if factory is None:
        raise ValueError(f"Unknown validation rule: {name}")

    return factory(*params)


def parse_rules(rules: str | list[Any]) -> list[Rule]:
    """
    Parse rules definition into list of Rule objects.

    Accepts:
        "required|email|max_length:255"           → pipe-separated string
        ["required", "email", MaxLength(255)]     → mixed list
        [Required(), Email()]                     → Rule objects
    """
    if isinstance(rules, str):
        return [parse_rule_string(r.strip()) for r in rules.split("|")]

    result: list[Rule] = []
    for r in rules:
        if isinstance(r, Rule):
            result.append(r)
        elif isinstance(r, str):
            result.append(parse_rule_string(r))
        elif callable(r):
            result.append(CallableRule(r))
        else:
            raise TypeError(f"Invalid rule: {r!r}")
    return result


class Password(Rule):
    """
    Password complexity rule.

    Usage:
        Password()                    # default: min 8
        Password(min_length=12)
        Password(uppercase=True, numbers=True, symbols=True)
    """

    def __init__(
        self,
        min_length: int = 8,
        *,
        uppercase: bool = False,
        lowercase: bool = False,
        numbers: bool = False,
        symbols: bool = False,
    ) -> None:
        self.min_length = min_length
        self.needs_upper = uppercase
        self.needs_lower = lowercase
        self.needs_numbers = numbers
        self.needs_symbols = symbols
        self.message = f"The {{field}} must be at least {min_length} characters"
        self._failure_reason = ""

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False

        if len(value) < self.min_length:
            self._failure_reason = f"at least {self.min_length} characters"
            return False

        if self.needs_upper and not any(c.isupper() for c in value):
            self._failure_reason = "at least one uppercase letter"
            return False

        if self.needs_lower and not any(c.islower() for c in value):
            self._failure_reason = "at least one lowercase letter"
            return False

        if self.needs_numbers and not any(c.isdigit() for c in value):
            self._failure_reason = "at least one number"
            return False

        if self.needs_symbols:
            symbols = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~")
            if not any(c in symbols for c in value):
                self._failure_reason = "at least one special character"
                return False

        return True

    def get_message(self, field: str, value: Any) -> str:
        if self._failure_reason:
            return f"The {field} must contain {self._failure_reason}"
        return self.message.format(field=field)


# ── Date rules ────────────────────────────────────────────


class DateFormat(Rule):
    """Validate date string format."""

    def __init__(self, fmt: str = "%Y-%m-%d") -> None:
        self.fmt = fmt
        self.message = f"The {{field}} must match format {fmt}"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        from datetime import datetime

        try:
            datetime.strptime(value, self.fmt)
            return True
        except ValueError:
            return False


class DateBefore(Rule):
    """Value must be a date before the given date."""

    def __init__(self, before: str, fmt: str = "%Y-%m-%d") -> None:
        self.before_str = before
        self.fmt = fmt
        self.message = f"The {{field}} must be before {before}"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        from datetime import datetime

        try:
            val_date = datetime.strptime(value, self.fmt)
            before_date = datetime.strptime(self.before_str, self.fmt)
            return val_date < before_date
        except ValueError:
            return False


class DateAfter(Rule):
    """Value must be a date after the given date."""

    def __init__(self, after: str, fmt: str = "%Y-%m-%d") -> None:
        self.after_str = after
        self.fmt = fmt
        self.message = f"The {{field}} must be after {after}"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        from datetime import datetime

        try:
            val_date = datetime.strptime(value, self.fmt)
            after_date = datetime.strptime(self.after_str, self.fmt)
            return val_date > after_date
        except ValueError:
            return False


# ── IP / UUID ─────────────────────────────────────────────


class IpAddress(Rule):
    message = "The {field} must be a valid IP address"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        import ipaddress

        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False


class Uuid(Rule):
    message = "The {field} must be a valid UUID"
    _pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

    def passes(self, field: str, value: Any) -> bool:
        return isinstance(value, str) and bool(self._pattern.match(value))


class Json(Rule):
    message = "The {field} must be valid JSON"

    def passes(self, field: str, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        import json

        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
