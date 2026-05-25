"""``make:model`` — generate a database model."""

from __future__ import annotations

from ._generator import GeneratorCommand, snake


class MakeModelCommand(GeneratorCommand):
    name = "make:model"
    description = "Create a new database model"

    stub = "model"
    target_dir = "app/models"
    suffix = ""
    type_label = "Model"

    def variables(self) -> dict[str, str]:
        return {"tableName": snake(self.class_name()) + "s"}
