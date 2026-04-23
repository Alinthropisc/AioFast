import re
from abc import ABC, abstractmethod
from typing import Any


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Rule(ABC):
    @abstractmethod
    def validate(self, name: str, value: Any) -> None:
        pass


class Required(Rule):
    def validate(self, name: str, value: Any) -> None:
        if value is None or value == "":
            raise ValidationError(f"The '{name}' field is required")


class Email(Rule):
    _pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def validate(self, name: str, value: Any) -> None:
        if value is not None and not self._pattern.match(str(value)):
            raise ValidationError(f"The '{name}' must be a valid email address")


class Min(Rule):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    def validate(self, name: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, (int, float)) and value < self.minimum:
            raise ValidationError(f"The '{name}' must be at least {self.minimum}")
        if isinstance(value, str) and len(value) < self.minimum:
            raise ValidationError(f"The '{name}' must be at least {self.minimum} characters")


class Max(Rule):
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum

    def validate(self, name: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, (int, float)) and value > self.maximum:
            raise ValidationError(f"The '{name}' must not exceed {self.maximum}")
        if isinstance(value, str) and len(value) > self.maximum:
            raise ValidationError(f"The '{name}' must not exceed {self.maximum} characters")


class InChoices(Rule):
    def __init__(self, choices: list) -> None:
        self.choices = choices

    def validate(self, name: str, value: Any) -> None:
        if value is not None and value not in self.choices:
            opts = ", ".join(map(str, self.choices))
            raise ValidationError(f"The '{name}' must be one of: {opts}")


class Regex(Rule):
    def __init__(self, pattern: str, message: str = "") -> None:
        self.pattern = re.compile(pattern)
        self._message = message

    def validate(self, name: str, value: Any) -> None:
        if value is not None and not self.pattern.match(str(value)):
            msg = self._message or f"The '{name}' format is invalid"
            raise ValidationError(msg)


class MinLength(Rule):
    def __init__(self, length: int) -> None:
        self.length = length

    def validate(self, name: str, value: Any) -> None:
        if value is not None and len(str(value)) < self.length:
            raise ValidationError(f"The '{name}' must be at least {self.length} characters")


class MaxLength(Rule):
    def __init__(self, length: int) -> None:
        self.length = length

    def validate(self, name: str, value: Any) -> None:
        if value is not None and len(str(value)) > self.length:
            raise ValidationError(f"The '{name}' must not exceed {self.length} characters")
