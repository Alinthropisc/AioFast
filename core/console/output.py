import json as json_module
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from .input import Verbosity
from .renderers import RendererManager


class ConsoleOutput:
    def __init__(self, verbosity: Verbosity = Verbosity.NORMAL, quiet: bool = False) -> None:
        self._console = Console()
        self._error_console = Console(stderr=True)
        self._verbosity = verbosity
        self._quiet = quiet
        self._buffer: list[str] = []
        self._buffering = False
        self._renderer_manager = RendererManager()

    @property
    def console(self) -> Console:
        return self._console

    @property
    def verbosity(self) -> Verbosity:
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value: Verbosity) -> None:
        self._verbosity = value

    @property
    def renderers(self) -> RendererManager:
        return self._renderer_manager

    # ── Basic Output ──────────────────────────────────────

    def line(self, message: str = "", style: str = "") -> None:
        if self._quiet and not self._buffering:
            return
        if self._buffering:
            self._buffer.append(message)
            return
        if style:
            self._console.print(f"[{style}]{message}[/{style}]")
        else:
            self._console.print(message)

    def newline(self, count: int = 1) -> None:
        for _ in range(count):
            self.line()

    def info(self, message: str) -> None:
        self.line(f"  ℹ  {message}", "blue")

    def success(self, message: str) -> None:
        self.line(f"  ✔  {message}", "green")

    def warn(self, message: str) -> None:
        self.line(f"  ⚠  {message}", "yellow")

    def error(self, message: str) -> None:
        if self._buffering:
            self._buffer.append(f"ERROR: {message}")
            return
        self._error_console.print(f"[bold red]  ✖  {message}[/bold red]")

    def comment(self, message: str) -> None:
        self.line(f"  // {message}", "dim")

    def debug(self, message: str) -> None:
        if self._verbosity.value >= Verbosity.DEBUG.value:
            self.line(f"  🐛 {message}", "dim cyan")

    def verbose(self, message: str) -> None:
        if self._verbosity.value >= Verbosity.VERBOSE.value:
            self.line(f"  → {message}", "dim")

    # ── Rich Components ───────────────────────────────────

    def table(self, headers: list[str], rows: list[list[Any]], title: str = "") -> None:
        if self._quiet and not self._buffering:
            return
        t = Table(title=title or None, box=box.ROUNDED, show_lines=False)
        for h in headers:
            t.add_column(h, style="cyan", header_style="bold cyan")
        for row in rows:
            t.add_row(*[str(c) for c in row])

        if self._buffering:
            c = Console(record=True)
            c.print(t)
            self._buffer.append(c.export_text())
        else:
            self._console.print(t)

    def json(self, data: Any, indent: int = 2) -> None:
        if self._quiet and not self._buffering:
            return
        formatted = json_module.dumps(
            data,
            indent=indent,
            default=str,
            ensure_ascii=False,
        )
        if self._buffering:
            self._buffer.append(formatted)
        else:
            syntax = Syntax(formatted, "json", theme="monokai")
            self._console.print(syntax)

    def panel(self, content: str, title: str = "", style: str = "blue") -> None:
        if self._buffering:
            self._buffer.append(f"[{title}] {content}")
            return
        self._console.print(Panel(content, title=title or None, border_style=style))

    def rule(self, title: str = "") -> None:
        if self._buffering:
            self._buffer.append(f"--- {title} ---" if title else "---")
            return
        self._console.rule(title)

    # ── Interactive Input ─────────────────────────────────

    def ask(self, question: str, default: str = "") -> str:
        return Prompt.ask(f"[bold cyan] ? [/bold cyan] {question}", default=default or None) or default

    def secret(self, question: str) -> str:
        return Prompt.ask(f"[bold cyan] ? [/bold cyan] {question}", password=True) or ""

    def confirm(self, question: str, default: bool = False) -> bool:
        return Confirm.ask(f"[bold cyan] ? [/bold cyan] {question}", default=default)

    def choice(self, question: str, choices: list[str], default: str = "") -> str:
        choices_str = ", ".join(choices)
        self.line(f"  Choices: {choices_str}", "dim")
        while True:
            answer = self.ask(question, default)
            if answer in choices:
                return answer
            self.error(f"Invalid choice. Must be one of: {choices_str}")

    # ── Progress & Spinner ────────────────────────────────

    def progress(self, description: str = "Processing...", total: int = 100):
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
        )

    def progress_bar(self, items: Any, description: str = "Processing..."):
        from rich.progress import track

        return track(items, description=description, console=self._console)

    def spinner(self, message: str = "Loading..."):
        return self._console.status(f"[bold blue]{message}")

    # ── Renderer-based Output ─────────────────────────────

    def format_data(self, headers: list[str], rows: list[list[Any]], fmt: str = "", title: str = "") -> None:
        fmt = fmt or self._renderer_manager.default
        rendered = self._renderer_manager.render(fmt, headers, rows, title)

        if fmt == "table":
            self._console.print(rendered, end="")
        else:
            self.line(rendered)

    # ── Buffering ─────────────────────────────────────────

    def start_buffering(self) -> None:
        self._buffering = True
        self._buffer.clear()

    def stop_buffering(self) -> str:
        self._buffering = False
        output = "\n".join(self._buffer)
        self._buffer.clear()
        return output

    def set_quiet(self, quiet: bool = True) -> None:
        self._quiet = quiet
