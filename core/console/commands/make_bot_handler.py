"""``make:bot-handler`` — generate an Aiogram bot handler."""

from __future__ import annotations

from ._generator import GeneratorCommand, snake


class MakeBotHandlerCommand(GeneratorCommand):
    name = "make:bot-handler"
    description = "Create a new Aiogram bot handler"

    stub = "bot_handler"
    target_dir = "app/bot/handlers"
    suffix = "Handler"
    type_label = "Bot handler"

    def variables(self) -> dict[str, str]:
        base = self.class_name()
        if base.endswith("Handler"):
            base = base[: -len("Handler")]
        return {"command": snake(base)}
