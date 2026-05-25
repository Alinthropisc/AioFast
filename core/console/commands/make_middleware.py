"""``make:middleware`` — generate an HTTP middleware."""

from __future__ import annotations

from ._generator import GeneratorCommand


class MakeMiddlewareCommand(GeneratorCommand):
    name = "make:middleware"
    description = "Create a new HTTP middleware"

    stub = "middleware"
    target_dir = "app/http/middleware"
    suffix = "Middleware"
    type_label = "Middleware"
