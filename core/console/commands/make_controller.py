"""``make:controller`` — generate an HTTP controller."""

from __future__ import annotations

from ._generator import GeneratorCommand, snake


class MakeControllerCommand(GeneratorCommand):
    name = "make:controller"
    description = "Create a new HTTP controller"

    stub = "controller"
    target_dir = "app/http/controllers"
    suffix = "Controller"
    type_label = "Controller"

    def variables(self) -> dict[str, str]:
        base = self.class_name()
        if base.endswith("Controller"):
            base = base[: -len("Controller")]
        return {"routePath": "/" + snake(base).replace("_", "-")}
