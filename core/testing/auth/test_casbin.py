from __future__ import annotations

import pytest

from core.auth.casbin_guard import CasbinGuard


@pytest.fixture
async def guard():
    g = CasbinGuard()
    await g.init_rbac()
    yield g
    await g.close()


class TestCasbinGuard:
    @pytest.mark.asyncio
    async def test_init(self, guard):
        assert guard.is_initialized

    @pytest.mark.asyncio
    async def test_add_role_and_check(self, guard):
        await guard.add_role_for_user("alice", "admin")
        assert await guard.has_role("alice", "admin") is True
        assert await guard.has_role("alice", "editor") is False

    @pytest.mark.asyncio
    async def test_permission_via_role(self, guard):
        await guard.add_role_for_user("alice", "admin")
        await guard.add_permission_for_role("admin", "posts", "delete")

        assert await guard.enforce("alice", "posts", "delete") is True
        assert await guard.enforce("alice", "posts", "create") is False

    @pytest.mark.asyncio
    async def test_direct_permission(self, guard):
        await guard.add_permission_for_user("bob", "profile", "edit")

        assert await guard.enforce("bob", "profile", "edit") is True
        assert await guard.enforce("bob", "profile", "delete") is False

    @pytest.mark.asyncio
    async def test_get_roles(self, guard):
        await guard.add_role_for_user("alice", "admin")
        await guard.add_role_for_user("alice", "editor")

        roles = await guard.get_roles("alice")
        assert "admin" in roles
        assert "editor" in roles

    @pytest.mark.asyncio
    async def test_delete_role_for_user(self, guard):
        await guard.add_role_for_user("alice", "admin")
        await guard.delete_role_for_user("alice", "admin")

        assert await guard.has_role("alice", "admin") is False

    @pytest.mark.asyncio
    async def test_get_users_for_role(self, guard):
        await guard.add_role_for_user("alice", "admin")
        await guard.add_role_for_user("bob", "admin")

        users = await guard.get_users_for_role("admin")
        assert "alice" in users
        assert "bob" in users

    @pytest.mark.asyncio
    async def test_remove_permission(self, guard):
        await guard.add_permission("admin", "posts", "delete")
        await guard.remove_permission("admin", "posts", "delete")

        assert await guard.enforce("admin", "posts", "delete") is False

    @pytest.mark.asyncio
    async def test_delete_user(self, guard):
        await guard.add_role_for_user("temp", "admin")
        await guard.delete_user("temp")

        assert await guard.has_role("temp", "admin") is False

    @pytest.mark.asyncio
    async def test_get_all_roles(self, guard):
        await guard.add_role_for_user("alice", "admin")
        await guard.add_role_for_user("bob", "editor")

        roles = await guard.get_all_roles()
        assert "admin" in roles
        assert "editor" in roles

    @pytest.mark.asyncio
    async def test_not_initialized_raises(self):
        guard = CasbinGuard()
        with pytest.raises(RuntimeError, match="not initialized"):
            await guard.enforce("a", "b", "c")

    @pytest.mark.asyncio
    async def test_has_permission(self, guard):
        await guard.add_permission("admin", "users", "read")
        assert await guard.has_permission("admin", "users", "read") is True
        assert await guard.has_permission("admin", "users", "write") is False

    @pytest.mark.asyncio
    async def test_get_permissions(self, guard):
        await guard.add_permission("editor", "posts", "read")
        await guard.add_permission("editor", "posts", "write")

        perms = await guard.get_permissions("editor")
        assert len(perms) == 2
