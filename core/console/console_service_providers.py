from __future__ import annotations

from pathlib import Path
from typing import Any

# Import conditionally to avoid circular imports at module level
# ServiceProvider is imported by the user's app


class ConsoleServiceProvider:
    """
    Register ConsoleKernel + ConsoleApplication in the container.

    Auto-discovers commands from:
      - app/commands/            (user commands)
      - aiofast/console/commands/ (built-in commands)

    No manual registration needed — just drop a Command file in app/commands/.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def register(self) -> None:
        from .console_application import ConsoleApplication
        from .kernel import ConsoleKernel
        from .lock import CommandLock

        base = getattr(self.app, "base_path", None) or Path.cwd()
        base = Path(base)
        # ── Kernel ────────────────────────────────────
        kernel = ConsoleKernel(self.app)
        # User commands
        user_commands = base / "app" / "commands"

        if user_commands.exists():
            kernel.add_path(str(user_commands), "app.commands")
        # Bilt-in framework commands
        builtin = Path(__file__).parent / "commands"

        if builtin.exists():
            kernel.add_path(str(builtin), "aiofast.console.commands")
        self.app.instance(ConsoleKernel, kernel)
        self.app.instance("console.kernel", kernel)
        # ── Lock manager ──────────────────────────────
        locks_dir = base / "storage" / "locks"
        lock_manager = CommandLock(str(locks_dir))
        self.app.instance(CommandLock, lock_manager)
        self.app.instance("console.lock", lock_manager)
        # ── Application ──────────────────────────────
        app_name = getattr(self.app, "name", "AioFast")
        app_version = getattr(self.app, "version", "1.0.0")
        console_app = ConsoleApplication(
            name=app_name,
            version=app_version,
            kernel=kernel,
            container=getattr(self.app, "container", self.app),
            binary="aiocraft",
            locks_dir=str(locks_dir),
        )

        self.app.instance(ConsoleApplication, console_app)
        self.app.instance("console", console_app)

    async def boot(self) -> None:
        from .kernel import ConsoleKernel

        kernel: ConsoleKernel = await self.app.make(ConsoleKernel)
        await kernel.bootstrap()
