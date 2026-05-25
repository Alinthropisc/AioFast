"""``make:command`` — generate a console command."""

from __future__ import annotations

from ._generator import GeneratorCommand, snake


class MakeCommandCommand(GeneratorCommand):
    name = "make:command"
    description = "Create a new console command"

    stub = "command"
    target_dir = "app/commands"
    suffix = "Command"
    type_label = "Command"

    def variables(self) -> dict[str, str]:
        base = self.class_name()
        if base.endswith("Command"):
            base = base[: -len("Command")]
        return {
            "commandName": snake(base).replace("_", ":"),
            "description": f"{base} command",
        }
