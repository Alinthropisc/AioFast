from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import ErrorBag
from .rules import Confirmed, Rule, parse_rules

if TYPE_CHECKING:
    from ..foundation import Application


class Validator:
    """
    Laravel-like validator.

    Usage:
        # String rules (Laravel-style)
        v = Validator(data, {
            "name": "required|string|min_length:2|max_length:50",
            "email": "required|email",
            "age": "required|integer|min:18",
            "role": "required|in:admin,user,moderator",
        })

        # Rule objects
        v = Validator(data, {
            "name": [Required(), StringRule(), MinLength(2)],
            "email": [Required(), Email()],
        })

        # Mixed
        v = Validator(data, {
            "name": "required|string",
            "email": [Required(), Email()],
            "bio": ["string", MaxLength(500)],
        })

        # Validate
        if v.fails():
            return v.error_response()

        clean = v.validated()

        # Or raise
        clean = v.validate()  # raises ValidationError
    """

    def __init__(
        self,
        data: dict[str, Any],
        rules: dict[str, str | list[Any]],
        *,
        messages: dict[str, str] | None = None,
        stop_on_first: bool = False,
        app: Application | None = None,
    ) -> None:  # ty:ignore[unresolved-reference]
        self._data = data
        self._rules_raw = rules
        self._custom_messages = messages or {}
        self._stop_on_first = stop_on_first
        self._app = app
        self._errors: ErrorBag | None = None
        self._validated: dict[str, Any] | None = None
        self._parsed_rules: dict[str, list] = {}
        self._parse()

    def _parse(self) -> None:
        from .conditional import DATA_AWARE_RULES

        for field, rules_def in self._rules_raw.items():
            parsed = parse_rules(rules_def) if isinstance(rules_def, str) else self._parse_mixed(rules_def)

            for r in parsed:
                if isinstance(r, Confirmed):
                    r.set_data(self._data)
                if isinstance(r, DATA_AWARE_RULES):
                    r.set_data(self._data)

            self._parsed_rules[field] = parsed

    def _parse_mixed(self, rules_def: list) -> list:
        """Parse a mixed list of strings, Rule objects, and AsyncRule objects."""
        from .async_rules import AsyncRule

        result = []
        for r in rules_def:
            if isinstance(r, (Rule, AsyncRule)):
                result.append(r)
            elif isinstance(r, str):
                from .rules import parse_rule_string

                result.append(parse_rule_string(r))
            elif callable(r):
                from .rules import CallableRule

                result.append(CallableRule(r))
            else:
                raise TypeError(f"Invalid rule: {r!r}")
        return result

    # ── sync validation ───────────────────────────────────

    def validate(self) -> dict[str, Any]:
        self._run_sync()
        if self._errors and self._errors.has_errors:
            raise self._errors.to_exception()
        return self._validated or {}

    def fails(self) -> bool:
        self._run_sync()
        return self._errors is not None and self._errors.has_errors

    def passes(self) -> bool:
        return not self.fails()

    def validated(self) -> dict[str, Any]:
        if self._validated is None:
            self._run_sync()
        return self._validated or {}

    # ── async validation ──────────────────────────────────

    async def validate_async(self) -> dict[str, Any]:
        """Validate including async rules."""
        self._run_sync()

        # Run async rules
        await self._run_async()

        if self._errors and self._errors.has_errors:
            raise self._errors.to_exception()
        return self._validated or {}

    # ── errors ────────────────────────────────────────────

    @property
    def errors(self) -> ErrorBag:
        if self._errors is None:
            self._run_sync()
        return self._errors  # type: ignore

    def error_messages(self) -> dict[str, list[str]]:
        return self.errors.errors

    def error_response(self, status: int = 422) -> dict[str, Any]:
        return {
            "success": False,
            "message": "Validation failed",
            "status": status,
            "errors": self.errors.errors,
        }

    # ── internals ─────────────────────────────────────────

    def _run_sync(self) -> None:
        if self._errors is not None:
            return

        bag = ErrorBag()
        validated: dict[str, Any] = {}

        for field, rules in self._parsed_rules.items():
            value = self._get_value(field)
            field_valid = True

            for r in rules:
                # Skip async rules in sync mode
                from .async_rules import AsyncRule

                if isinstance(r, AsyncRule):
                    continue

                if not r.passes(field, value):
                    msg = self._get_message(field, r)
                    bag.add(field, msg)
                    field_valid = False
                    if self._stop_on_first:
                        break

            if field_valid and value is not None:
                validated[field] = value

        self._errors = bag
        self._validated = validated

    async def _run_async(self) -> None:
        from .async_rules import AsyncRule

        if self._errors is None:
            self._errors = ErrorBag()

        for field, rules in self._parsed_rules.items():
            value = self._get_value(field)

            for r in rules:
                if not isinstance(r, AsyncRule):
                    continue
                if self._app:
                    r.set_app(self._app)

                if not await r.passes_async(field, value):
                    msg = self._get_message(field, r)
                    self._errors.add(field, msg)

                    if field in (self._validated or {}):
                        del self._validated[field]  # ty:ignore[not-subscriptable]

    def _get_value(self, field: str) -> Any:
        if "." not in field:
            return self._data.get(field)
        parts = field.split(".")
        current: Any = self._data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _get_message(self, field: str, r: Any) -> str:
        rule_name = type(r).__name__.lower()
        custom_key = f"{field}.{rule_name}"
        if custom_key in self._custom_messages:
            return self._custom_messages[custom_key]
        if field in self._custom_messages:
            return self._custom_messages[field]
        return r.get_message(field, self._get_value(field))

    def __repr__(self) -> str:
        fields = len(self._parsed_rules)
        status = "validated" if self._errors is not None else "pending"
        return f"<Validator fields={fields} [{status}]>"


# ── Convenience function ──────────────────────────────────


def validate(
    data: dict[str, Any], rules: dict[str, str | list[Any]], *, messages: dict[str, str] | None = None
) -> dict[str, Any]:
    return Validator(data, rules, messages=messages).validate()


async def validate_async(
    data: dict[str, Any],
    rules: dict[str, str | list[Any]],
    *,
    messages: dict[str, str] | None = None,
    app: Application | None = None,
) -> dict[str, Any]:  # ty:ignore[unresolved-reference]
    return await Validator(data, rules, messages=messages, app=app).validate_async()
