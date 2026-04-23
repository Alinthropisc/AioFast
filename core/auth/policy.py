from __future__ import annotations

import logging
from typing import Any

from ..exceptions import AuthorizationException
from .gate import Response

logger = logging.getLogger(__name__)


class Policy:
    """
    Policy — class-based authorization for a model.

    Like Laravel's Policy. Methods map to abilities:
      view, view_any, create, update, delete, restore, force_delete

    Usage:
        class PostPolicy(Policy):
            def view(self, user, post) -> bool:
                return True  # everyone can view

            def update(self, user, post) -> bool:
                return user.id == post.author_id

            def delete(self, user, post) -> bool:
                return user.is_admin or user.id == post.author_id

            def before(self, user, ability) -> Optional[bool]:
                if user.is_super_admin:
                    return True  # super admin can do anything
                return None  # continue to specific check
    """

    def before(self, user: Any, ability: str) -> bool | None:
        """
        Run before any check.
        Return True → allow, False → deny, None → continue.
        """
        return None

    def view(self, user: Any, resource: Any) -> bool:
        return False

    def view_any(self, user: Any) -> bool:
        return False

    def create(self, user: Any) -> bool:
        return False

    def update(self, user: Any, resource: Any) -> bool:
        return False

    def delete(self, user: Any, resource: Any) -> bool:
        return False

    def restore(self, user: Any, resource: Any) -> bool:
        return False

    def force_delete(self, user: Any, resource: Any) -> bool:
        return False


class PolicyRegistry:
    """
    Registry mapping models → policies.

    Usage:
        registry = PolicyRegistry()
        registry.register(Post, PostPolicy())
        registry.register(Comment, CommentPolicy())

        # Check:
        policy = registry.for_model(Post)
        allowed = await registry.check(user, 'update', post)
    """

    def __init__(self) -> None:
        self._policies: dict[type, Policy] = {}

    def register(self, model: type, policy: Policy) -> PolicyRegistry:
        """Map a model class to its policy."""
        self._policies[model] = policy
        logger.debug("Policy registered: %s → %s", model.__name__, policy.__class__.__name__)
        return self

    def for_model(self, model_or_instance: Any) -> Policy | None:
        """Get policy for a model class or instance."""
        if isinstance(model_or_instance, type):
            return self._policies.get(model_or_instance)
        return self._policies.get(type(model_or_instance))

    async def check(self, user: Any, ability: str, resource: Any = None) -> bool:
        """Check ability against the policy for the resource's model."""
        model_type = type(resource) if resource is not None else None
        policy = self._policies.get(model_type) if model_type else None

        if policy is None:
            return False

        # before hook
        before_result = policy.before(user, ability)
        if before_result is True:
            return True
        if before_result is False:
            return False

        # Get method
        method = getattr(policy, ability, None)
        if method is None:
            # Try snake_case conversion
            method = getattr(policy, ability.replace("-", "_"), None)

        if method is None:
            logger.warning("Policy %s has no method '%s'", policy.__class__.__name__, ability)
            return False

        import asyncio
        import inspect

        # Call with correct args
        sig = inspect.signature(method)
        param_count = len(sig.parameters)  # excluding self

        result = method(user, resource) if resource is not None and param_count >= 2 else method(user)

        if asyncio.iscoroutine(result):
            result = await result

        if isinstance(result, Response):
            return result.allowed
        return bool(result)

    async def authorize(self, user: Any, ability: str, resource: Any = None) -> None:
        """Check and raise if denied."""
        if not await self.check(user, ability, resource):
            raise AuthorizationException(f"Cannot {ability} this resource.", ability=ability, resource=resource)

    @property
    def registered_models(self) -> list[type]:
        return list(self._policies.keys())

    def __repr__(self) -> str:
        models = [m.__name__ for m in self._policies]
        return f"<PolicyRegistry models={models}>"
