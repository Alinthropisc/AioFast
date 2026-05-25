#!/usr/bin/env python
"""AioFast console entry point — the ``aiocraft`` CLI.

Usage:
    python aiocraft.py <command> [arguments] [options]
    python aiocraft.py list
    python aiocraft.py serve
    python aiocraft.py make:controller UserController
"""

from __future__ import annotations

import asyncio
import os
import sys

from bootstrap.app import BASE_PATH, create_application
from core.console import ConsoleApplication
from core.console.kernel import ConsoleKernel


def _build_console(app) -> ConsoleApplication:
    kernel = ConsoleKernel(app)
    # Built-in framework commands.
    kernel.add_path(os.path.join(str(BASE_PATH), "core", "console", "commands"), "core.console.commands")
    # User commands (optional).
    kernel.add_path(os.path.join(str(BASE_PATH), "app", "commands"), "app.commands")
    return ConsoleApplication(
        name=getattr(app, "name", "AioFast"),
        version=getattr(app, "version", "1.0.0"),
        kernel=kernel,
        container=app,
        binary="aiocraft",
    )


def main() -> None:
    app = create_application()
    console = _build_console(app)
    exit_code = asyncio.run(console.run(sys.argv[1:]))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
