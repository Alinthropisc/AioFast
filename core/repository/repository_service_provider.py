from __future__ import annotations

from typing import TYPE_CHECKING

from ..foundation.service_provider import ServiceProvider

if TYPE_CHECKING:
    from .base import BaseRepository


class RepositoryServiceProvider(ServiceProvider):
    """
    Base provider for repositories.

    Subclass and override `repositories()`:

        class AppRepositoryProvider(RepositoryServiceProvider):
            def repositories(self) -> dict:
                return {
                    UserRepository: User,
                    PostRepository: Post,
                }
    """

    def repositories(self) -> dict[type[BaseRepository], type]:
        """Override: {RepositoryClass: ModelClass}."""
        return {}

    async def register(self) -> None:
        for repo_class, _model_class in self.repositories().items():
            self.app.scoped(repo_class)

    async def boot(self) -> None:
        pass
