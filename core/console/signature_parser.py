import re

from .descriptors.argument import MISSING, Argument
from .descriptors.option import Option


class SignatureParser:
    """
    Parse Laravel-style command signature strings.

    {name}                → required argument
    {name?}               → optional argument (default=None)
    {name=default}        → argument with default
    {name : description}  → argument with description
    {--flag}              → boolean option
    {--flag|-f}           → option with shortcut
    {--option=}           → option requiring a value
    {--option=default}    → option with default value
    """

    _TOKEN_RE = re.compile(r"\{([^}]+)\}")

    @classmethod
    def parse(cls, signature: str) -> tuple[list[Argument], list[Option]]:
        arguments: list[Argument] = []
        options: list[Option] = []

        for match in cls._TOKEN_RE.finditer(signature):
            token = match.group(1).strip()
            if token.startswith("--"):
                options.append(cls._parse_option(token))
            else:
                arguments.append(cls._parse_argument(token))

        return arguments, options

    @classmethod
    def _parse_argument(cls, token: str) -> Argument:
        description = ""
        if " : " in token:
            token, description = token.split(" : ", 1)
            token = token.strip()
            description = description.strip()

        if token.endswith("?"):
            name = token[:-1].strip()
            arg = Argument(type=str, default=None, description=description)
            arg.attr_name = name
            return arg

        if "=" in token:
            name, default = token.split("=", 1)
            arg = Argument(type=str, default=default.strip(), description=description)
            arg.attr_name = name.strip()
            return arg

        arg = Argument(type=str, default=MISSING, description=description)
        arg.attr_name = token.strip()
        return arg

    @classmethod
    def _parse_option(cls, token: str) -> Option:
        description = ""
        if " : " in token:
            token, description = token.split(" : ", 1)
            token = token.strip()
            description = description.strip()

        short = ""
        if "|" in token:
            parts = token.split("|", 1)
            token = parts[0].strip()
            short = parts[1].strip()

        if "=" in token:
            name_part, default = token.split("=", 1)
            name = name_part.lstrip("-").strip()
            opt = Option(
                long=f"--{name}",
                short=short,
                type=str,
                default=default.strip() if default.strip() else MISSING,
                description=description,
            )
            opt.attr_name = name.replace("-", "_")
            return opt

        name = token.lstrip("-").strip()
        opt = Option(long=f"--{name}", short=short, type=bool, default=False, description=description)
        opt.attr_name = name.replace("-", "_")
        return opt
