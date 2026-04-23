import asyncio
import os
import sys
from typing import Any

from .console_application import ConsoleApplication
from .kernel import ConsoleKernel


def run(
    app: Any = None,
    argv: list[str] | None = None,
    name: str = "AioFast",
    version: str = "1.0.0",
    binary: str = "aiocraft",
    commands_path: str = "",
    commands_module: str = "",
) -> None:
    container = None

    if app is not None:
        container = getattr(app, "container", None)
        name = getattr(app, "name", name)
        version = getattr(app, "version", version)
    kernel = ConsoleKernel(app)

    if commands_path:
        kernel.add_path(commands_path, commands_module)
    elif app and hasattr(app, "base_path"):
        cmd_path = os.path.join(str(app.base_path), "app", "commands")
        kernel.add_path(cmd_path, "app.commands")
    # Built-in framework commands path
    builtin_path = os.path.join(os.path.dirname(__file__), "commands")

    if os.path.exists(builtin_path):
        kernel.add_path(builtin_path, "aiofast.console.commands")
    console_app = ConsoleApplication(name=name, version=version, kernel=kernel, container=container, binary=binary)
    exit_code = asyncio.run(_execute(console_app, argv))
    sys.exit(exit_code)


async def _execute(app: "ConsoleApplication", argv: list[str] | None) -> int:
    try:
        return await app.run(argv)
    except Exception:
        return 1
