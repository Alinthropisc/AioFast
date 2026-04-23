from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from .base import Renderer


class TableRenderer(Renderer):
    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        console = Console(record=True)
        t = Table(title=title or None, box=box.ROUNDED, show_lines=False)
        for h in headers:
            t.add_column(h, style="cyan", header_style="bold cyan")
        for row in rows:
            t.add_row(*[str(c) for c in row])
        console.print(t)
        return console.export_text()
