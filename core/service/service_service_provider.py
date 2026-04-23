from __future__ import annotations

from typing import TYPE_CHECKING

from ..foundation.service_provider import ServiceProvider

if TYPE_CHECKING:
    from .base import Service


class ServiceServiceProvider(ServiceProvider):
    """
    Base provider for services.

    Subclass and override `services()`:

        class AppServiceProvider(ServiceServiceProvider):
            def services(self) -> dict:
                return {
                    UserService: "singleton",
                    PaymentService: "transient",
                    NotificationService: "singleton",
                }
    """

    def services(self) -> dict[type[Service], str]:
        """
        Override to return {ServiceClass: scope}.
        Scope: "singleton", "transient", "scoped"
        """
        return {}

    async def register(self) -> None:
        for service_class, scope in self.services().items():
            if scope == "singleton":
                self.app.singleton(service_class)
            elif scope == "scoped":
                self.app.scoped(service_class)
            else:
                self.app.bind(service_class)

    async def boot(self) -> None:
        pass
