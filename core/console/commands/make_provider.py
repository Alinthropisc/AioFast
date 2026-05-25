"""``make:provider`` — generate a service provider."""

from __future__ import annotations

from ._generator import GeneratorCommand


class MakeProviderCommand(GeneratorCommand):
    name = "make:provider"
    description = "Create a new service provider"

    stub = "provider"
    target_dir = "app/providers"
    suffix = "ServiceProvider"
    type_label = "Provider"
