"""``about`` — display application & environment information."""

from __future__ import annotations

import os
import platform
import sys
from typing import Any

from core.console import Command
from core.foundation import Application


class AboutCommand(Command):
    name = "about"
    description = "Display application information"

    async def handle(self, **kwargs: Any) -> int:
        app = self._app.container if self._app else None
        self.table(
            ["Key", "Value"],
            [
                ["Application", getattr(app, "name", "AioFast")],
                ["Version", Application.VERSION],
                ["Environment", os.environ.get("APP_ENV", "local")],
                ["Debug", str(getattr(app, "is_debug", False))],
                ["Python", sys.version.split()[0]],
                ["Platform", platform.platform()],
                ["Base path", str(getattr(app, "base_path", "."))],
            ],
            title="AioFast",
        )
        return self.SUCCESS
