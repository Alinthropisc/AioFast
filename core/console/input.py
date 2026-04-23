from enum import Enum
from typing import Any


class Verbosity(Enum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    VERY_VERBOSE = 3
    DEBUG = 4


class ArgvInput:
    def __init__(self, argv: list[str] | None = None) -> None:
        import sys

        self._raw = argv if argv is not None else sys.argv[1:]
        self._command: str = ""
        self._arguments: list[str] = []
        self._options: dict[str, Any] = {}
        self._verbosity = Verbosity.NORMAL
        self._interactive = True
        self._format: str = "table"
        self._parse()

    @property
    def command(self) -> str:
        return self._command

    @property
    def arguments(self) -> list[str]:
        return list(self._arguments)

    @property
    def options(self) -> dict[str, Any]:
        return dict(self._options)

    @property
    def verbosity(self) -> Verbosity:
        return self._verbosity

    @property
    def is_interactive(self) -> bool:
        return self._interactive

    @property
    def format(self) -> str:
        return self._format

    def has_option(self, name: str) -> bool:
        return name in self._options

    def get_option(self, name: str, default: Any = None) -> Any:
        return self._options.get(name, default)

    def _parse(self) -> None:
        tokens = list(self._raw)
        if not tokens:
            return

        if tokens and not tokens[0].startswith("-"):
            self._command = tokens.pop(0)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token == "--":
                self._arguments.extend(tokens[i + 1 :])
                break

            if token.startswith("--"):
                i = self._parse_long_option(tokens, i)
            elif token.startswith("-") and len(token) > 1:
                i = self._parse_short_option(tokens, i)
            else:
                self._arguments.append(token)
                i += 1

        if "format" in self._options:
            fmt = self._options["format"]
            if isinstance(fmt, str) and fmt in ("table", "json", "csv", "plain"):
                self._format = fmt

    def _parse_long_option(self, tokens: list[str], i: int) -> int:
        token = tokens[i]

        if "=" in token:
            key, value = token.split("=", 1)
            name = key[2:]
            if name in self._options:
                existing = self._options[name]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    self._options[name] = [existing, value]
            else:
                self._options[name] = value
        else:
            name = token[2:]
            if name == "quiet":
                self._verbosity = Verbosity.QUIET
            elif name == "no-interaction":
                self._interactive = False
            self._options[name] = True

        return i + 1

    def _parse_short_option(self, tokens: list[str], i: int) -> int:
        chars = tokens[i][1:]

        if all(c == "v" for c in chars):
            levels = {
                1: Verbosity.VERBOSE,
                2: Verbosity.VERY_VERBOSE,
                3: Verbosity.DEBUG,
            }
            self._verbosity = levels.get(len(chars), Verbosity.DEBUG)
            return i + 1

        for j, char in enumerate(chars):
            is_last = j == len(chars) - 1
            has_next_value = i + 1 < len(tokens) and not tokens[i + 1].startswith("-")

            if is_last and has_next_value:
                self._options[char] = tokens[i + 1]
                return i + 2
            else:
                self._options[char] = True

        return i + 1

    def __repr__(self) -> str:
        return f"<ArgvInput command={self._command!r} args={self._arguments} opts={self._options}>"
