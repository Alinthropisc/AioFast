from __future__ import annotations

from typing import Any

from .errors import ErrorBag
from .rules import Rule, parse_rules


class NestedValidator:
    """
    Validate nested data with wildcard support.

    Like Laravel's array validation:
        "items": "required|list",
        "items.*.name": "required|string",
        "items.*.price": "required|numeric|positive",
        "address.city": "required|string",
        "address.zip": "required|regex:^\\d{5}$",

    Usage:
        v = NestedValidator(data, {
            "items": "required|list",
            "items.*.name": "required|string|min_length:2",
            "items.*.quantity": "required|integer|min:1",
            "shipping.address.line1": "required|string",
        })
        if v.fails():
            print(v.errors)
            # {"items.0.name": ["Required"], "items.2.quantity": ["Must be at least 1"]}
    """

    def __init__(self, data: dict[str, Any], rules: dict[str, str | list[Any]]) -> None:
        self._data = data
        self._rules_raw = rules
        self._errors: ErrorBag | None = None
        self._validated: dict[str, Any] | None = None

    def validate(self) -> dict[str, Any]:
        self._run()
        if self._errors and self._errors.has_errors:
            from .errors import ValidationError

            raise ValidationError(self._errors.errors)
        return self._validated or {}

    def fails(self) -> bool:
        self._run()
        return self._errors is not None and self._errors.has_errors

    def passes(self) -> bool:
        return not self.fails()

    @property
    def errors(self) -> ErrorBag:
        if self._errors is None:
            self._run()
        return self._errors  # type: ignore

    def _run(self) -> None:
        if self._errors is not None:
            return
        bag = ErrorBag()
        validated: dict[str, Any] = {}

        for rule_key, rules_def in self._rules_raw.items():
            parsed = parse_rules(rules_def)
            # Inject data into data-aware rules
            from .conditional import DATA_AWARE_RULES

            for r in parsed:
                if isinstance(r, DATA_AWARE_RULES):
                    r.set_data(self._data)

            if "*" in rule_key:
                # Wildcard — expand to real paths
                paths = self._expand_wildcard(rule_key, self._data)
                for real_path in paths:
                    value = self._get_nested(real_path, self._data)
                    self._validate_field(real_path, value, parsed, bag, validated)
            else:
                value = self._get_nested(rule_key, self._data)
                self._validate_field(rule_key, value, parsed, bag, validated)
        self._errors = bag
        self._validated = validated

    def _validate_field(
        self, field: str, value: Any, rules: list[Rule], bag: ErrorBag, validated: dict[str, Any]
    ) -> None:
        field_valid = True

        for r in rules:
            if not r.passes(field, value):
                bag.add(field, r.get_message(field, value))
                field_valid = False

        if field_valid and value is not None:
            self._set_nested(validated, field, value)

    @staticmethod
    def _get_nested(path: str, data: Any) -> Any:
        """Get value from nested dict by dot path."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    @staticmethod
    def _set_nested(data: dict, path: str, value: Any) -> None:
        """Set value in nested dict by dot path."""
        parts = path.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current:
                # Check if next part is numeric (list index)
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    @staticmethod
    def _expand_wildcard(pattern: str, data: Any) -> list[str]:
        """
        Expand wildcard pattern to real paths.

        "items.*.name" with data={"items": [{"name":"A"}, {"name":"B"}]}
        → ["items.0.name", "items.1.name"]
        """
        parts = pattern.split(".")
        return NestedValidator._expand_parts(parts, data, [])

    @staticmethod
    def _expand_parts(parts: list[str], data: Any, prefix: list[str]) -> list[str]:
        if not parts:
            return [".".join(prefix)]
        current = parts[0]
        remaining = parts[1:]

        if current == "*":
            results: list[str] = []
            if isinstance(data, (list, tuple)):
                for i in range(len(data)):
                    results.extend(NestedValidator._expand_parts(remaining, data[i], [*prefix, str(i)]))
            elif isinstance(data, dict):
                for key in data:
                    results.extend(NestedValidator._expand_parts(remaining, data[key], [*prefix, key]))
            return results
        else:
            if isinstance(data, dict) and current in data:
                return NestedValidator._expand_parts(remaining, data[current], [*prefix, current])
            elif isinstance(data, (list, tuple)):
                try:
                    idx = int(current)
                    return NestedValidator._expand_parts(remaining, data[idx], [*prefix, current])
                except (ValueError, IndexError):
                    pass
            return [".".join(prefix + parts)]
