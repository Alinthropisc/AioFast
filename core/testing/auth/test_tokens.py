from __future__ import annotations

import time

import pytest

from core.auth.tokens import PersonalAccessTokenManager, TokenManager

# Длинный ключ чтобы не было InsecureKeyLengthWarning
SECRET = "aiofast-test-secret-key-minimum-32-bytes-long!"


class TestTokenManager:
    @pytest.fixture
    def tm(self):
        return TokenManager(secret=SECRET, access_ttl=3600, refresh_ttl=86400)

    def test_issue(self, tm):
        pair = tm.issue("user_1", scopes=["read", "write"])
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "Bearer"

    def test_verify_access(self, tm):
        pair = tm.issue("user_1")
        payload = tm.verify_access_token(pair.access_token)
        assert payload is not None
        assert payload.sub == "user_1"
        assert payload.user_id == "user_1"

    def test_verify_refresh(self, tm):
        pair = tm.issue("user_1")
        payload = tm.verify_refresh_token(pair.refresh_token)
        assert payload is not None
        assert payload.sub == "user_1"

    def test_access_not_refresh(self, tm):
        pair = tm.issue("user_1")
        assert tm.verify_access_token(pair.refresh_token) is None
        assert tm.verify_refresh_token(pair.access_token) is None

    def test_scopes(self, tm):
        pair = tm.issue("user_1", scopes=["read", "write"])
        assert tm.has_scope(pair.access_token, "read") is True
        assert tm.has_scope(pair.access_token, "delete") is False
        assert tm.has_all_scopes(pair.access_token, ["read", "write"]) is True
        assert tm.has_all_scopes(pair.access_token, ["read", "admin"]) is False
        assert tm.has_any_scope(pair.access_token, ["admin", "read"]) is True
        assert tm.has_any_scope(pair.access_token, ["admin", "super"]) is False

    def test_revoke(self, tm):
        pair = tm.issue("user_1")
        assert tm.verify_access_token(pair.access_token) is not None
        tm.revoke(pair.access_token)
        assert tm.verify_access_token(pair.access_token) is None

    def test_refresh_flow(self, tm):
        pair = tm.issue("user_1")
        new_pair = tm.refresh(pair.refresh_token)
        assert new_pair is not None
        assert new_pair.access_token != pair.access_token
        # Old refresh should be revoked
        assert tm.verify_refresh_token(pair.refresh_token) is None

    def test_refresh_invalid(self, tm):
        assert tm.refresh("garbage") is None

    def test_revoke_all(self, tm):
        tm.issue("user_1")
        tm.issue("user_1")
        count = tm.revoke_all("user_1")
        assert count == 2

    def test_revoke_by_jti(self, tm):
        pair = tm.issue("user_1")
        payload = tm.verify_access_token(pair.access_token)
        tm.revoke_by_jti(payload.jti)
        assert tm.verify_access_token(pair.access_token) is None

    def test_is_revoked(self, tm):
        pair = tm.issue("user_1")
        payload = tm.verify_access_token(pair.access_token)
        assert tm.is_revoked(payload.jti) is False
        tm.revoke(pair.access_token)
        assert tm.is_revoked(payload.jti) is True

    def test_invalid_token(self, tm):
        assert tm.verify_access_token("garbage") is None

    def test_expired_token(self):
        tm = TokenManager(secret=SECRET, access_ttl=0)
        pair = tm.issue("user_1")
        time.sleep(0.1)
        assert tm.verify_access_token(pair.access_token) is None

    def test_extra_claims(self, tm):
        pair = tm.issue("user_1", extra={"org": "acme", "tier": "pro"})
        payload = tm.verify_access_token(pair.access_token)
        assert payload is not None
        assert payload.extra["org"] == "acme"
        assert payload.extra["tier"] == "pro"

    def test_repr(self, tm):
        r = repr(tm)
        assert "TokenManager" in r
        assert "HS256" in r


class TestPersonalAccessTokenManager:
    @pytest.mark.asyncio
    async def test_create_and_verify(self):
        mgr = PersonalAccessTokenManager()
        plain, pat = await mgr.create("user_1", "My Token", scopes=["read"])
        assert plain.startswith("pat_")
        assert pat.user_id == "user_1"
        assert pat.name == "My Token"

        verified = await mgr.verify(plain)
        assert verified is not None
        assert verified.name == "My Token"
        assert "read" in verified.scopes

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        mgr = PersonalAccessTokenManager()
        assert await mgr.verify("pat_invalid") is None

    @pytest.mark.asyncio
    async def test_not_pat_prefix(self):
        mgr = PersonalAccessTokenManager()
        assert await mgr.verify("not_a_pat_token") is None

    @pytest.mark.asyncio
    async def test_revoke(self):
        mgr = PersonalAccessTokenManager()
        plain, pat = await mgr.create("user_1", "Token")
        await mgr.revoke(token_hash=pat.token_hash)
        assert await mgr.verify(plain) is None

    @pytest.mark.asyncio
    async def test_revoke_all(self):
        mgr = PersonalAccessTokenManager()
        await mgr.create("user_1", "T1")
        await mgr.create("user_1", "T2")
        await mgr.create("user_2", "T3")
        count = await mgr.revoke_all("user_1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_list(self):
        mgr = PersonalAccessTokenManager()
        await mgr.create("user_1", "Token1")
        await mgr.create("user_1", "Token2")
        await mgr.create("user_2", "Token3")
        tokens = await mgr.list_for_user("user_1")
        assert len(tokens) == 2
        names = {t.name for t in tokens}
        assert names == {"Token1", "Token2"}
