from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .descriptors.argument import MISSING, Argument
from .descriptors.option import Option
from .signals import SignalManager
from .signature_parser import SignatureParser
from .wizard import Wizard

if TYPE_CHECKING:
    from .console_application import ConsoleApplication
    from .input import ArgvInput
    from .output import ConsoleOutput


class Command(ABC):
    name: str = ""
    description: str = ""
    help_text: str = ""
    aliases: list[str] = []
    hidden: bool = False
    isolated: bool = False
    production_guard: bool = False
    signature: str = ""
    middleware: list[Any] = []
    lock: bool = False

    SUCCESS = 0
    FAILURE = 1
    INVALID = 2

    # ── Descriptor collection (metaclass-free) ────────────

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._arg_defs: list[Argument] = []
        cls._opt_defs: list[Option] = []
        cls._collect_descriptors()

    @classmethod
    def _collect_descriptors(cls) -> None:
        for attr_name, value in list(cls.__dict__.items()):
            if isinstance(value, Argument):
                if not value.attr_name:
                    value.attr_name = attr_name
                cls._arg_defs.append(value)
            elif isinstance(value, Option):
                if not value.attr_name:
                    value.attr_name = attr_name
                if not value.long:
                    value.long = f"--{attr_name.replace('_', '-')}"
                cls._opt_defs.append(value)

        if cls.signature:
            sig_args, sig_opts = SignatureParser.parse(cls.signature)
            cls._arg_defs.extend(sig_args)
            cls._opt_defs.extend(sig_opts)

    # ── Setup ─────────────────────────────────────────────

    def setup(self, input_: ArgvInput, output: ConsoleOutput, app: ConsoleApplication | None = None) -> None:
        self._input = input_
        self._output = output
        self._output.verbosity = input_.verbosity
        self._app = app
        self._signal_manager = SignalManager.get_instance()
        self._parsed_arguments: dict[str, Any] = {}
        self._parsed_options: dict[str, Any] = {}
        self._start_time: float = 0
        self._bind_arguments()
        self._bind_options()

    def _bind_arguments(self) -> None:
        input_args = self._input.arguments if self._input else []
        for i, arg_def in enumerate(self._arg_defs):
            if i < len(input_args):
                value = arg_def.cast(input_args[i])
            elif arg_def.default is not MISSING:
                value = arg_def.default
            else:
                value = None
            self._parsed_arguments[arg_def.attr_name] = value
            setattr(self, arg_def.attr_name, value)

    def _bind_options(self) -> None:
        if not self._input:
            return
        for opt_def in self._opt_defs:
            value = opt_def.effective_default
            long_name = opt_def.long.lstrip("-")
            short_name = opt_def.short.lstrip("-") if opt_def.short else ""
            raw = None
            if long_name in self._input.options:
                raw = self._input.options[long_name]
            elif short_name and short_name in self._input.options:
                raw = self._input.options[short_name]

            if raw is not None:
                if opt_def.is_list or isinstance(raw, list):
                    items = raw if isinstance(raw, list) else [raw]
                    value = [opt_def.cast(v) for v in items]
                else:
                    value = opt_def.cast(raw)

            self._parsed_options[opt_def.attr_name] = value
            setattr(self, opt_def.attr_name, value)

    # ── Validation ────────────────────────────────────────

    def validate(self) -> list[str]:
        errors: list[str] = []
        for arg_def in self._arg_defs:
            value = self._parsed_arguments.get(arg_def.attr_name)
            if arg_def.is_required and value is None:
                errors.append(f"Missing required argument: '{arg_def.attr_name}'")
            errors.extend(arg_def.validate(value))

        for opt_def in self._opt_defs:
            value = self._parsed_options.get(opt_def.attr_name)
            errors.extend(opt_def.validate(value))
        return errors

    # ── Template Method — Lifecycle ───────────────────────

    @abstractmethod
    async def handle(self, **kwargs: Any) -> int:
        pass

    async def before(self) -> bool:
        """Hook before handle(). Return False to abort."""
        return True

    async def after(self, exit_code: int) -> None:
        """Hook always runs after handle(), even on error."""
        pass

    async def on_success(self) -> None:
        """Hook runs only when handle() returned SUCCESS."""
        pass

    async def on_failure(self, exit_code: int) -> None:
        """Hook runs when handle() returned non-zero."""
        pass

    async def on_error(self, error: Exception) -> int:
        """Hook on unhandled exception. Return exit code or re-raise."""
        raise error

    # ── Signals ───────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._signal_manager.is_running

    @property
    def is_shutting_down(self) -> bool:
        return self._signal_manager.is_shutting_down

    # ── Argument / Option access ──────────────────────────

    def argument(self, name: str, default: Any = None) -> Any:
        return self._parsed_arguments.get(name, default)

    def option(self, name: str, default: Any = None) -> Any:
        return self._parsed_options.get(name, default)

    def all_arguments(self) -> dict[str, Any]:
        return dict(self._parsed_arguments)

    def all_options(self) -> dict[str, Any]:
        return dict(self._parsed_options)

    # ── Output shortcuts ──────────────────────────────────

    def line(self, message: str = "", style: str = "") -> None:
        self._output.line(message, style)

    def newline(self, count: int = 1) -> None:
        self._output.newline(count)

    def info(self, message: str) -> None:
        self._output.info(message)

    def success(self, message: str) -> None:
        self._output.success(message)

    def warn(self, message: str) -> None:
        self._output.warn(message)

    def error(self, message: str) -> None:
        self._output.error(message)

    def comment(self, message: str) -> None:
        self._output.comment(message)

    def debug(self, message: str) -> None:
        self._output.debug(message)

    def verbose(self, message: str) -> None:
        self._output.verbose(message)

    def table(self, headers: list[str], rows: list[list[Any]], title: str = "") -> None:
        self._output.table(headers, rows, title)

    def json(self, data: Any) -> None:
        self._output.json(data)

    def panel(self, content: str, title: str = "", style: str = "blue") -> None:
        self._output.panel(content, title, style)

    def rule(self, title: str = "") -> None:
        self._output.rule(title)

    def format_data(self, headers: list[str], rows: list[list[Any]], title: str = "") -> None:
        fmt = self._input.format if self._input else "table"
        self._output.format_data(headers, rows, fmt, title)

    # ── Interactive ───────────────────────────────────────

    def ask(self, question: str, default: str = "") -> str:
        return self._output.ask(question, default)

    def secret(self, question: str) -> str:
        return self._output.secret(question)

    def confirm(self, question: str, default: bool = False) -> bool:
        return self._output.confirm(question, default)

    def choice(self, question: str, choices: list[str], default: str = "") -> str:
        return self._output.choice(question, choices, default)

    def confirm_production(self) -> bool:
        if not self.production_guard:
            return True
        env = os.getenv("APP_ENV", "local")
        if env not in ("production", "prod"):
            return True
        if self._parsed_options.get("force", False):
            return True
        return self.confirm("You are in PRODUCTION. Are you sure?", default=False)

    # ── Wizard ────────────────────────────────────────────

    def wizard(self, title: str) -> Wizard:
        return Wizard(title, self._output)

    # ── Progress ──────────────────────────────────────────

    def progress(self, description: str = "Processing...", total: int = 100):
        return self._output.progress(description, total)

    def progress_bar(self, items: Any, description: str = "Processing..."):
        return self._output.progress_bar(items, description)

    def spinner(self, message: str = "Loading..."):
        return self._output.spinner(message)

    # ── Call other commands ───────────────────────────────

    async def call(self, command_name: str, **kwargs: Any) -> int:
        if self._app is None:
            raise RuntimeError("Cannot call commands without ConsoleApplication")
        return await self._app.call(command_name, **kwargs)

    async def call_silently(self, command_name: str, **kwargs: Any) -> int:
        if self._app is None:
            raise RuntimeError("Cannot call commands without ConsoleApplication")
        return await self._app.call(command_name, quiet=True, **kwargs)

    # ── Command Chaining ──────────────────────────────────

    async def chain(self, commands: list[tuple[str, dict]]) -> int:
        for cmd_name, kwargs in commands:
            self.comment(f"Running: {cmd_name}")
            code = await self.call(cmd_name, **kwargs)
            if code != self.SUCCESS:
                self.error(f"Command '{cmd_name}' failed (exit={code}), chain aborted")
                return code
            self.success(f"Completed: {cmd_name}")
        return self.SUCCESS

    # ── Help ──────────────────────────────────────────────

    def get_help(self) -> str:
        lines: list[str] = []
        lines.append(f"[bold]{self.name}[/bold]")
        if self.description:
            lines.append(f"  {self.description}")
        if self.help_text:
            lines.append(f"\n{self.help_text}")

        if self._arg_defs:
            lines.append("\n[bold]Arguments:[/bold]")
            for arg in self._arg_defs:
                req = " (required)" if arg.is_required else ""
                default = f" [default: {arg.default}]" if arg.default is not MISSING else ""
                lines.append(f"  [green]{arg.attr_name}[/green]{req}{default}")
                if arg.description:
                    lines.append(f"    {arg.description}")

        if self._opt_defs:
            lines.append("\n[bold]Options:[/bold]")
            for opt in self._opt_defs:
                flags = opt.long
                if opt.short:
                    flags += f", {opt.short}"
                default = ""
                if opt.effective_default is not None:
                    default = f" [default: {opt.effective_default}]"
                lines.append(f"  [green]{flags}[/green]{default}")
                if opt.description:
                    lines.append(f"    {opt.description}")

        if self.aliases:
            lines.append(f"\n[bold]Aliases:[/bold] {', '.join(self.aliases)}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<Command {self.name!r}>"
