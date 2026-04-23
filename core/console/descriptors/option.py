from typing import Any

from .argument import MISSING


class Option:
    def __init__(
        self,
        long: str = "",
        short: str = "",
        type: type = bool,
        default: Any = MISSING,
        description: str = "",
        rules: list | None = None,
        is_list: bool = False,
    ) -> None:
        self.long = long
        self.short = short
        self.type = type
        self.default = default
        self.description = description
        self.rules = rules or []
        self.is_list = is_list
        self.attr_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name
        if not self.long:
            self.long = f"--{name.replace('_', '-')}"

    @property
    def is_flag(self) -> bool:
        return self.type is bool and self.default is MISSING

    @property
    def effective_default(self) -> Any:
        if self.default is not MISSING:
            return self.default
        if self.type is bool:
            return False
        if self.is_list:
            return []
        return None

    def cast(self, value: Any) -> Any:
        if self.type is bool:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "y")
        if self.type is int:
            return int(value)
        if self.type is float:
            return float(value)
        return value

    def validate(self, value: Any) -> list[str]:
        errors: list[str] = []
        for rule in self.rules:
            try:
                rule.validate(self.attr_name, value)
            except Exception as e:
                errors.append(str(e))
        return errors

    def matches(self, token: str) -> bool:
        name = token.split("=", 1)[0]
        return name == self.long or name == self.short

    def __repr__(self) -> str:
        flags = self.long
        if self.short:
            flags += f"|{self.short}"
        return f"<Option {flags} type={self.type.__name__}>"
