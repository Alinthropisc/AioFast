from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default RBAC model
RBAC_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""

# RBAC with resource roles
RBAC_RESOURCE_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _
g2 = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && g2(r.obj, p.obj) && r.act == p.act
"""

# ABAC model
ABAC_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
"""


class CasbinGuard:
    """
    PyCasbin wrapper for RBAC/ABAC authorization.

    Usage:
        guard = CasbinGuard()

        # Option 1: File-based policy
        await guard.init_from_file("model.conf", "policy.csv")

        # Option 2: Built-in RBAC model + in-memory
        await guard.init_rbac()

        # Option 3: With database adapter
        await guard.init_with_adapter(adapter)

        # Manage roles
        await guard.add_role_for_user("alice", "admin")
        await guard.add_permission_for_role("admin", "posts", "delete")

        # Check
        allowed = await guard.enforce("alice", "posts", "delete")  # True
        has_role = await guard.has_role("alice", "admin")  # True

        # Cleanup
        await guard.close()
    """

    def __init__(self) -> None:
        self._enforcer: Any | None = None
        self._initialized: bool = False

    # ── Initialization ────────────────────────────────────

    async def init_from_file(self, model_path: str, policy_path: str) -> None:
        """Initialize from model.conf and policy.csv files."""
        import casbin

        self._enforcer = casbin.Enforcer(model_path, policy_path)
        self._initialized = True
        logger.info("Casbin initialized from files")

    async def init_rbac(self) -> None:
        """Initialize with built-in RBAC model (in-memory)."""
        import os
        import tempfile

        import casbin

        # Write model to temp file (casbin needs a file path, not a handle).
        model_file = tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False)  # noqa: SIM115
        model_file.write(RBAC_MODEL)
        model_file.close()
        self._enforcer = casbin.Enforcer(model_file.name)
        os.unlink(model_file.name)
        self._initialized = True
        logger.info("Casbin RBAC initialized (in-memory)")

    async def init_with_adapter(self, adapter: Any, model_text: str = RBAC_MODEL) -> None:
        """Initialize with custom adapter (DB, Redis, etc.)."""
        import os
        import tempfile

        import casbin

        model_file = tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False)  # noqa: SIM115
        model_file.write(model_text)
        model_file.close()
        self._enforcer = casbin.Enforcer(model_file.name, adapter)
        os.unlink(model_file.name)
        self._initialized = True
        logger.info("Casbin initialized with adapter")

    # ── Enforce ───────────────────────────────────────────

    async def enforce(self, sub: str, obj: str, act: str) -> bool:
        """Check if subject can perform action on object."""
        self._check_init()
        return self._enforcer.enforce(sub, obj, act)  # ty:ignore[unresolved-attribute]

    async def enforce_ex(self, sub: str, obj: str, act: str) -> tuple:
        """Enforce with explanation (returns matched rule)."""
        self._check_init()
        return self._enforcer.enforce_ex(sub, obj, act)  # ty:ignore[unresolved-attribute]

    # ── Role Management ───────────────────────────────────

    async def add_role_for_user(self, user: str, role: str) -> bool:
        """Assign role to user."""
        self._check_init()
        return self._enforcer.add_role_for_user(user, role)  # ty:ignore[unresolved-attribute]

    async def delete_role_for_user(self, user: str, role: str) -> bool:
        """Remove role from user."""
        self._check_init()
        return self._enforcer.delete_role_for_user(user, role)  # ty:ignore[unresolved-attribute]

    async def has_role(self, user: str, role: str) -> bool:
        """Check if user has role."""
        self._check_init()
        roles = self._enforcer.get_roles_for_user(user)  # ty:ignore[unresolved-attribute]
        return role in roles

    async def get_roles(self, user: str) -> list[str]:
        """Get all roles for user."""
        self._check_init()
        return self._enforcer.get_roles_for_user(user)  # ty:ignore[unresolved-attribute]

    async def get_users_for_role(self, role: str) -> list[str]:
        """Get all users with a role."""
        self._check_init()
        return self._enforcer.get_users_for_role(role)  # ty:ignore[unresolved-attribute]

    async def delete_role(self, role: str) -> None:
        """Delete a role entirely."""
        self._check_init()
        self._enforcer.delete_role(role)  # ty:ignore[unresolved-attribute]

    async def delete_user(self, user: str) -> None:
        """Remove all roles/permissions for user."""
        self._check_init()
        self._enforcer.delete_user(user)  # ty:ignore[unresolved-attribute]

    # ── Permission Management ─────────────────────────────

    async def add_permission(self, sub: str, obj: str, act: str) -> bool:
        """Add permission policy rule."""
        self._check_init()
        return self._enforcer.add_policy(sub, obj, act)  # ty:ignore[unresolved-attribute]

    async def add_permission_for_role(self, role: str, obj: str, act: str) -> bool:
        """Add permission for a role."""
        return await self.add_permission(role, obj, act)

    async def add_permission_for_user(self, user: str, obj: str, act: str) -> bool:
        """Add direct permission for a user."""
        return await self.add_permission(user, obj, act)

    async def remove_permission(self, sub: str, obj: str, act: str) -> bool:
        """Remove permission policy rule."""
        self._check_init()
        return self._enforcer.remove_policy(sub, obj, act)  # ty:ignore[unresolved-attribute]

    async def get_permissions(self, sub: str) -> list[list[str]]:
        """Get all permissions for subject."""
        self._check_init()
        return self._enforcer.get_permissions_for_user(sub)  # ty:ignore[unresolved-attribute]

    async def has_permission(self, sub: str, obj: str, act: str) -> bool:
        """Check if subject has specific permission."""
        self._check_init()
        return self._enforcer.has_policy(sub, obj, act)  # ty:ignore[unresolved-attribute]

    # ── Bulk Operations ───────────────────────────────────

    async def add_policies(self, rules: list[list[str]]) -> bool:
        """Add multiple policy rules at once."""
        self._check_init()
        return self._enforcer.add_policies(rules)  # ty:ignore[unresolved-attribute]

    async def remove_policies(self, rules: list[list[str]]) -> bool:
        """Remove multiple policy rules."""
        self._check_init()
        return self._enforcer.remove_policies(rules)  # ty:ignore[unresolved-attribute]

    # ── Save / Load ───────────────────────────────────────

    async def save_policy(self) -> None:
        """Save policy to adapter."""
        self._check_init()
        self._enforcer.save_policy()  # ty:ignore[unresolved-attribute]

    async def load_policy(self) -> None:
        """Reload policy from adapter."""
        self._check_init()
        self._enforcer.load_policy()  # ty:ignore[unresolved-attribute]

    # ── Info ──────────────────────────────────────────────

    async def get_all_roles(self) -> list[str]:
        """Get all defined roles."""
        self._check_init()
        return self._enforcer.get_all_roles()  # ty:ignore[unresolved-attribute]

    async def get_all_subjects(self) -> list[str]:
        """Get all subjects in policy."""
        self._check_init()
        return self._enforcer.get_all_subjects()  # ty:ignore[unresolved-attribute]

    async def get_all_objects(self) -> list[str]:
        """Get all objects in policy."""
        self._check_init()
        return self._enforcer.get_all_objects()  # ty:ignore[unresolved-attribute]

    async def get_all_actions(self) -> list[str]:
        """Get all actions in policy."""
        self._check_init()
        return self._enforcer.get_all_actions()  # ty:ignore[unresolved-attribute]

    # ── Lifecycle ─────────────────────────────────────────

    async def close(self) -> None:
        """Cleanup."""
        self._enforcer = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ── Internal ──────────────────────────────────────────

    def _check_init(self) -> None:
        if not self._initialized or self._enforcer is None:
            raise RuntimeError("CasbinGuard not initialized. Call init_rbac() or init_from_file() first.")

    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "not initialized"
        return f"<CasbinGuard [{status}]>"
