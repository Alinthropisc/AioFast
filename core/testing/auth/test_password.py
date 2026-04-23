from __future__ import annotations

import pytest

from core.auth.password import PasswordHasher, PasswordResetManager, PasswordValidator


class TestPasswordHasher:
    def test_hash_and_verify_bcrypt(self):
        h = PasswordHasher(algorithm="bcrypt", rounds=4)
        hashed = h.hash("mypassword")
        assert h.verify("mypassword", hashed) is True
        assert h.verify("wrong", hashed) is False

    def test_hash_and_verify_scrypt(self):
        h = PasswordHasher(algorithm="scrypt")
        hashed = h.hash("mypassword")
        assert h.verify("mypassword", hashed) is True
        assert h.verify("wrong", hashed) is False

    def test_needs_rehash(self):
        h = PasswordHasher(algorithm="bcrypt", rounds=4)
        hashed = h.hash("test")
        assert h.needs_rehash(hashed) is False

        h2 = PasswordHasher(algorithm="bcrypt", rounds=10)
        assert h2.needs_rehash(hashed) is True


class TestPasswordValidator:
    def test_valid(self):
        v = PasswordValidator()
        result = v.validate("MyStr0ng!")
        assert result.valid

    def test_too_short(self):
        v = PasswordValidator(min_length=8)
        result = v.validate("Ab1!")
        assert not result.valid
        assert any("at least" in e for e in result.errors)

    def test_no_uppercase(self):
        v = PasswordValidator(require_uppercase=True)
        result = v.validate("password123")
        assert not result.valid

    def test_common_password(self):
        v = PasswordValidator(disallow_common=True)
        v.validate("Password1")
        # "password" is common
        result2 = v.validate("password")
        assert not result2.valid

    def test_custom_rule(self):
        def no_spaces(pw):
            if " " in pw:
                return "Password must not contain spaces."

        v = PasswordValidator(custom_rules=[no_spaces])
        result = v.validate("my password 1A")
        assert not result.valid


class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_create_and_verify(self):
        mgr = PasswordResetManager(ttl=60)
        token = await mgr.create("user@test.com")
        assert await mgr.verify("user@test.com", token) is True

    @pytest.mark.asyncio
    async def test_wrong_token(self):
        mgr = PasswordResetManager()
        await mgr.create("user@test.com")
        assert await mgr.verify("user@test.com", "wrong") is False

    @pytest.mark.asyncio
    async def test_consume(self):
        mgr = PasswordResetManager()
        token = await mgr.create("user@test.com")
        assert await mgr.consume("user@test.com", token) is True
        assert await mgr.verify("user@test.com", token) is False
