import csv
import io
from typing import Any

from .base import Renderer


class CsvRenderer(Renderer):
    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        return buf.getvalue()
