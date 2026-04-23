from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .rules import Rule

if TYPE_CHECKING:
    from collections.abc import Callable


class RequiredIf(Rule):
    """
    Required only if another field has a specific value.

    Usage:
        "payment_method": "required",
        "card_number": [RequiredIf("payment_method", "credit_card")],
    """

    def __init__(self, other_field: str, other_value: Any) -> None:
        self.other_field = other_field
        self.other_value = other_value
        self.message = f"The {{field}} is required when {other_field} is {other_value!r}"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        actual = self._data.get(self.other_field)
        if actual != self.other_value:
            return True  # condition not met, skip
        # Condition met — value required
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")


class RequiredUnless(Rule):
    """Required unless another field has a specific value."""

    def __init__(self, other_field: str, other_value: Any) -> None:
        self.other_field = other_field
        self.other_value = other_value
        self.message = f"The {{field}} is required unless {other_field} is {other_value!r}"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        actual = self._data.get(self.other_field)
        if actual == self.other_value:
            return True  # condition met, skip
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")


class RequiredWith(Rule):
    """Required when ANY of the other fields are present."""

    def __init__(self, *fields: str) -> None:
        self.fields = list(fields)
        self.message = "The {field} is required when " + ", ".join(fields) + " is present"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        any_present = any(self._data.get(f) is not None for f in self.fields)
        if not any_present:
            return True  # none present, skip
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")


class RequiredWithout(Rule):
    """Required when ANY of the other fields are NOT present."""

    def __init__(self, *fields: str) -> None:
        self.fields = list(fields)
        self.message = "The {field} is required when " + ", ".join(fields) + " is not present"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        any_missing = any(self._data.get(f) is None for f in self.fields)
        if not any_missing:
            return True
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")


class Same(Rule):
    """Value must match another field."""

    def __init__(self, other_field: str) -> None:
        self.other_field = other_field
        self.message = f"The {{field}} must match {other_field}"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        return value == self._data.get(self.other_field)


class Different(Rule):
    """Value must be different from another field."""

    def __init__(self, other_field: str) -> None:
        self.other_field = other_field
        self.message = f"The {{field}} must be different from {other_field}"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        return value != self._data.get(self.other_field)


class RequiredWithAll(Rule):
    """Required when ALL of the other fields are present."""

    def __init__(self, *fields: str) -> None:
        self.fields = list(fields)
        self.message = "The {field} is required"
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data

    def passes(self, field: str, value: Any) -> bool:
        all_present = all(self._data.get(f) is not None for f in self.fields)
        if not all_present:
            return True
        return value is not None and (not isinstance(value, str) or value.strip() != "")


class When(Rule):
    """
    Apply a rule only when a condition is met.

    Usage:
        When(lambda data: data.get("type") == "business", MinLength(5))
    """

    def __init__(self, condition: Callable[[dict], bool], then_rule: Rule) -> None:
        self._condition = condition
        self._then_rule = then_rule
        self.message = then_rule.message
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data
        if hasattr(self._then_rule, "set_data"):
            self._then_rule.set_data(data)  # ty:ignore[call-non-callable]

    def passes(self, field: str, value: Any) -> bool:
        if not self._condition(self._data):
            return True  # condition not met, skip
        return self._then_rule.passes(field, value)

    def get_message(self, field: str, value: Any) -> str:
        return self._then_rule.get_message(field, value)


# Data-aware rules need data injected — mark them
DATA_AWARE_RULES = (RequiredIf, RequiredUnless, RequiredWith, RequiredWithout, RequiredWithAll, Same, Different, When)
