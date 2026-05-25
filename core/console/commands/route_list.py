"""``route:list`` — display all registered routes."""

from __future__ import annotations

from typing import Any

from core.console import Command


class RouteListCommand(Command):
    name = "route:list"
    description = "List all registered routes"

    async def handle(self, **kwargs: Any) -> int:
        from core.registry import AdapterManager

        app = self._app.container if self._app else None
        if app is None:
            self.error("No application container available.")
            return self.FAILURE
        # Providers register (and routes attach to the AdapterManager) during
        # boot, so boot the app before reading the route table.
        if not app.is_booted:
            await app.boot()

        if not app.has(AdapterManager):
            self.error("AdapterManager not registered.")
            return self.FAILURE

        manager: AdapterManager = await app.make(AdapterManager)
        rows = manager.route_table()

        if not rows:
            self.warn("No routes registered.")
            return self.SUCCESS

        self.table(
            ["Method", "Path", "Name", "Type", "Handler"],
            [[r["methods"], r["path"], r["name"], r["type"], r["handler"]] for r in rows],
            title=f"Routes ({len(rows)})",
        )
        return self.SUCCESS
