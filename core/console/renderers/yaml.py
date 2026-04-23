from typing import Any

from .base import Renderer


class YamlRenderer(Renderer):
    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        try:
            import yaml

            data = [dict(zip(headers, row, strict=False)) for row in rows]
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        except ImportError:
            lines = []
            for row in rows:
                lines.append("- " + ", ".join(f"{h}: {v}" for h, v in zip(headers, row, strict=False)))
            return "\n".join(lines)
