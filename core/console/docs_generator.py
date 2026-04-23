from __future__ import annotations

from typing import TYPE_CHECKING

from .descriptors.argument import MISSING

if TYPE_CHECKING:
    from .command import Command


class DocsGenerator:
    def __init__(self, commands: dict[str, type[Command]], app_name: str = "AioFast", binary: str = "aiocraft") -> None:
        self._commands = commands
        self._app_name = app_name
        self._binary = binary

    def generate(self, fmt: str = "markdown") -> str:
        generators = {
            "markdown": self._markdown,
            "md": self._markdown,
            "html": self._html,
        }
        gen = generators.get(fmt, self._markdown)
        return gen()

    def _markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# {self._app_name} — CLI Commands\n")
        grouped = self._group()

        for group, cmds in grouped.items():
            if group:
                lines.append(f"\n## {group}\n")
            else:
                lines.append("\n## General\n")

            for cmd_cls in cmds:
                if cmd_cls.hidden:
                    continue
                lines.append(f"### `{cmd_cls.name}`\n")

                if cmd_cls.description:
                    lines.append(f"{cmd_cls.description}\n")
                lines.append(f"```bash\n{self._binary} {cmd_cls.name}")

                for arg in cmd_cls._arg_defs:
                    if arg.is_required:
                        lines[-1] += f" <{arg.attr_name}>"
                    else:
                        lines[-1] += f" [{arg.attr_name}]"

                for opt in cmd_cls._opt_defs:
                    lines[-1] += f" [{opt.long}]"
                lines.append("```\n")

                if cmd_cls._arg_defs:
                    lines.append("**Arguments:**\n")
                    lines.append("| Name | Required | Default | Description |")
                    lines.append("|------|----------|---------|-------------|")
                    for arg in cmd_cls._arg_defs:
                        req = "Yes" if arg.is_required else "No"
                        default = arg.default if arg.default is not MISSING else "-"
                        lines.append(f"| `{arg.attr_name}` | {req} | {default} | {arg.description} |")
                    lines.append("")

                if cmd_cls._opt_defs:
                    lines.append("**Options:**\n")
                    lines.append("| Flag | Short | Default | Description |")
                    lines.append("|------|-------|---------|-------------|")
                    for opt in cmd_cls._opt_defs:
                        short = opt.short or "-"
                        default = opt.effective_default
                        lines.append(f"| `{opt.long}` | {short} | {default} | {opt.description} |")
                    lines.append("")
                lines.append("---\n")
        return "\n".join(lines)

    def _html(self) -> str:
        lines: list[str] = []
        lines.append("<!DOCTYPE html>")
        lines.append("<html><head>")
        lines.append(f"<title>{self._app_name} CLI</title>")
        lines.append("<style>")
        lines.append("body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px}")
        lines.append("code{background:#f4f4f4;padding:2px 6px;border-radius:3px}")
        lines.append("table{border-collapse:collapse;width:100%}")
        lines.append("td,th{border:1px solid #ddd;padding:8px;text-align:left}")
        lines.append("th{background:#f8f8f8}")
        lines.append("</style></head><body>")
        lines.append(f"<h1>{self._app_name} — CLI Commands</h1>")
        grouped = self._group()

        for group, cmds in grouped.items():
            title = group if group else "General"
            lines.append(f"<h2>{title}</h2>")

            for cmd_cls in cmds:
                if cmd_cls.hidden:
                    continue
                lines.append(f"<h3><code>{cmd_cls.name}</code></h3>")
                if cmd_cls.description:
                    lines.append(f"<p>{cmd_cls.description}</p>")

                if cmd_cls._arg_defs:
                    lines.append("<h4>Arguments</h4>")
                    lines.append("<table><tr><th>Name</th><th>Required</th><th>Default</th><th>Description</th></tr>")
                    for arg in cmd_cls._arg_defs:
                        req = "Yes" if arg.is_required else "No"
                        default = arg.default if arg.default is not MISSING else "-"
                        lines.append(
                            f"<tr><td><code>{arg.attr_name}</code></td><td>{req}</td><td>{default}</td><td>{arg.description}</td></tr>"
                        )
                    lines.append("</table>")

                if cmd_cls._opt_defs:
                    lines.append("<h4>Options</h4>")
                    lines.append("<table><tr><th>Flag</th><th>Short</th><th>Default</th><th>Description</th></tr>")
                    for opt in cmd_cls._opt_defs:
                        short = opt.short or "-"
                        default = opt.effective_default
                        lines.append(
                            f"<tr><td><code>{opt.long}</code></td><td>{short}</td><td>{default}</td><td>{opt.description}</td></tr>"
                        )
                    lines.append("</table>")
                lines.append("<hr>")
        lines.append("</body></html>")
        return "\n".join(lines)

    def _group(self) -> dict[str, list[type[Command]]]:
        groups: dict[str, list[type[Command]]] = {}
        for name, cls in sorted(self._commands.items()):
            group = name.split(":")[0] if ":" in name else ""
            groups.setdefault(group, []).append(cls)
        return groups
