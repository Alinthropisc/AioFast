from typing import Any


class _MissingSentinel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<MISSING>"

    def __bool__(self) -> bool:
        return False


MISSING = _MissingSentinel()


class Argument:
    def __init__(
        self, type: type = str, default: Any = MISSING, description: str = "", rules: list | None = None
    ) -> None:
        self.type = type
        self.default = default
        self.description = description
        self.rules = rules or []
        self.attr_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name

    @property
    def is_required(self) -> bool:
        return self.default is MISSING

    def cast(self, value: str) -> Any:
        if self.type is bool:
            return value.lower() in ("true", "1", "yes", "y")
        try:
            return self.type(value)
        except (ValueError, TypeError):
            return value

    def validate(self, value: Any) -> list[str]:
        errors: list[str] = []
        for rule in self.rules:
            try:
                rule.validate(self.attr_name, value)
            except Exception as e:
                errors.append(str(e))
        return errors

    def __repr__(self) -> str:
        return f"<Argument {self.attr_name!r} type={self.type.__name__}>"
