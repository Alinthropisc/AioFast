from __future__ import annotations

from ..foundation.service_provider import ServiceProvider


class ControllerServiceProvider(ServiceProvider):
    """
    Base provider for controllers.

    Subclass and override `controllers()` to register controllers:

        class AppControllerProvider(ControllerServiceProvider):
            def controllers(self):
                return [UserController, PostController]
    """

    def controllers(self) -> list:
        """Override to return controller classes."""
        return []

    async def register(self) -> None:
        # Register each controller class as transient (new instance per resolve)
        for ctrl_class in self.controllers():
            self.app.bind(ctrl_class)

    async def boot(self) -> None:
        pass
