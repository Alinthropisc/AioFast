"""``make:service`` — generate a service class."""

from __future__ import annotations

from ._generator import GeneratorCommand


class MakeServiceCommand(GeneratorCommand):
    name = "make:service"
    description = "Create a new service class"

    stub = "service"
    target_dir = "app/services"
    suffix = "Service"
    type_label = "Service"
