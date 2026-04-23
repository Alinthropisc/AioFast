from __future__ import annotations

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TokenPair:
    """Access + Refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_expires_in: int = 604800  # 7 days


@dataclass
class TokenPayload:
    """Decoded token payload."""

    sub: str  # user ID
    exp: int  # expiration timestamp
    iat: int  # issued at
    jti: str | None = None  # unique token ID
    scopes: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.exp

    @property
    def user_id(self) -> str:
        return self.sub


class TokenManager:
    """
    JWT token management — issue, verify, refresh, revoke.

    Usage:
        manager = TokenManager(
            secret="your-secret-key",
            algorithm="HS256",
            access_ttl=3600,      # 1 hour
            refresh_ttl=604800,   # 7 days
        )

        # Issue tokens:
        pair = manager.issue(user_id="123", scopes=["read", "write"])
        # {"access_token": "ey...", "refresh_token": "ey...", ...}

        # Verify:
        payload = manager.verify_access_token(pair.access_token)
        # TokenPayload(sub="123", ...)

        # Refresh:
        new_pair = manager.refresh(pair.refresh_token)

        # Revoke:
        manager.revoke(pair.access_token)
        manager.revoke_all("123")  # revoke all user tokens
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl: int = 3600,
        refresh_ttl: int = 604800,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer
        self._audience = audience
        self._revoked: set = set()  # In production → Redis/DB
        self._refresh_store: dict[str, dict] = {}  # jti → metadata

    def _get_jwt(self):
        try:
            import jwt

            return jwt
        except ImportError:
            raise ImportError("Install PyJWT: pip install PyJWT")

    # ── Issue ─────────────────────────────────────────────

    def issue(self, user_id: Any, scopes: list[str] | None = None, extra: dict[str, Any] | None = None) -> TokenPair:
        """Issue access + refresh token pair."""
        now = int(time.time())
        jti_access = secrets.token_hex(16)
        jti_refresh = secrets.token_hex(16)

        access_payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self._access_ttl,
            "jti": jti_access,
            "type": "access",
            "scopes": scopes or [],
            **(extra or {}),
        }
        if self._issuer:
            access_payload["iss"] = self._issuer
        if self._audience:
            access_payload["aud"] = self._audience

        refresh_payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self._refresh_ttl,
            "jti": jti_refresh,
            "type": "refresh",
        }

        pyjwt = self._get_jwt()
        access_token = pyjwt.encode(access_payload, self._secret, algorithm=self._algorithm)
        refresh_token = pyjwt.encode(refresh_payload, self._secret, algorithm=self._algorithm)

        # Store refresh token metadata
        self._refresh_store[jti_refresh] = {
            "user_id": str(user_id),
            "access_jti": jti_access,
            "created_at": now,
        }

        logger.debug("Tokens issued for user: %s", user_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_ttl,
            refresh_expires_in=self._refresh_ttl,
        )

    # ── Verify ────────────────────────────────────────────

    def verify_access_token(self, token: str) -> TokenPayload | None:
        """Verify and decode access token."""
        payload = self._decode(token)
        if payload is None:
            return None

        if payload.get("type") != "access":
            return None

        jti = payload.get("jti")
        if jti and jti in self._revoked:
            logger.debug("Token revoked: %s", jti)
            return None

        return TokenPayload(
            sub=payload["sub"],
            exp=payload["exp"],
            iat=payload["iat"],
            jti=jti,
            scopes=payload.get("scopes", []),
            extra={
                k: v
                for k, v in payload.items()
                if k not in ("sub", "exp", "iat", "jti", "type", "scopes", "iss", "aud")
            },
        )

    def verify_refresh_token(self, token: str) -> TokenPayload | None:
        """Verify and decode refresh token."""
        payload = self._decode(token)
        if payload is None:
            return None

        if payload.get("type") != "refresh":
            return None

        jti = payload.get("jti")
        if jti and jti in self._revoked:
            return None

        return TokenPayload(sub=payload["sub"], exp=payload["exp"], iat=payload["iat"], jti=jti)

    # ── Refresh ───────────────────────────────────────────

    def refresh(self, refresh_token: str, scopes: list[str] | None = None) -> TokenPair | None:
        """Refresh — issue new pair, revoke old refresh token."""
        payload = self.verify_refresh_token(refresh_token)
        if payload is None:
            return None

        # Revoke old refresh token
        if payload.jti:
            self._revoked.add(payload.jti)

            # Also revoke the old access token
            meta = self._refresh_store.pop(payload.jti, None)
            if meta and meta.get("access_jti"):
                self._revoked.add(meta["access_jti"])

        # Issue new pair
        return self.issue(payload.sub, scopes=scopes)

    # ── Revoke ────────────────────────────────────────────

    def revoke(self, token: str) -> bool:
        """Revoke a specific token."""
        payload = self._decode(token)
        if payload and payload.get("jti"):
            self._revoked.add(payload["jti"])
            logger.debug("Token revoked: %s", payload["jti"])
            return True
        return False

    def revoke_by_jti(self, jti: str) -> None:
        """Revoke by token ID."""
        self._revoked.add(jti)

    def revoke_all(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user."""
        count = 0
        to_remove = []
        for jti, meta in self._refresh_store.items():
            if meta.get("user_id") == user_id:
                self._revoked.add(jti)
                if meta.get("access_jti"):
                    self._revoked.add(meta["access_jti"])
                to_remove.append(jti)
                count += 1
        for jti in to_remove:
            del self._refresh_store[jti]
        logger.info("Revoked %d tokens for user: %s", count, user_id)
        return count

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked

    # ── Scopes ────────────────────────────────────────────

    def has_scope(self, token: str, scope: str) -> bool:
        """Check if token has a specific scope."""
        payload = self.verify_access_token(token)
        if payload is None:
            return False
        return scope in payload.scopes

    def has_any_scope(self, token: str, scopes: list[str]) -> bool:
        payload = self.verify_access_token(token)
        if payload is None:
            return False
        return bool(set(scopes) & set(payload.scopes))

    def has_all_scopes(self, token: str, scopes: list[str]) -> bool:
        payload = self.verify_access_token(token)
        if payload is None:
            return False
        return set(scopes).issubset(set(payload.scopes))

    # ── Internal ──────────────────────────────────────────

    def _decode(self, token: str) -> dict | None:
        pyjwt = self._get_jwt()
        try:
            kwargs = {}
            if self._audience:
                kwargs["audience"] = self._audience
            if self._issuer:
                kwargs["issuer"] = self._issuer

            return pyjwt.decode(token, self._secret, algorithms=[self._algorithm], **kwargs)
        except pyjwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except pyjwt.InvalidTokenError as e:
            logger.debug("Invalid token: %s", e)
            return None

    def __repr__(self) -> str:
        return f"<TokenManager algorithm={self._algorithm} access_ttl={self._access_ttl}s refresh_ttl={self._refresh_ttl}s>"


# ── Personal Access Token ─────────────────────────────────


@dataclass
class PersonalAccessToken:
    """
    Personal Access Token — like GitHub PAT.

    User-created tokens with custom names and scopes.
    """

    id: int | None = None
    user_id: str = ""
    name: str = ""
    token_hash: str = ""
    scopes: list[str] = field(default_factory=list)
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        import datetime

        exp = datetime.datetime.fromisoformat(self.expires_at)
        return datetime.datetime.now(datetime.timezone.utc) > exp


class PersonalAccessTokenManager:
    """
    Manages personal access tokens.

    Usage:
        pat_manager = PersonalAccessTokenManager(repository)

        # Create:
        plain_token, pat = await pat_manager.create(
            user_id="123",
            name="My CLI Token",
            scopes=["read", "write"],
            expires_in_days=90,
        )
        # plain_token = "pat_abc123..." (show once)
        # pat = PersonalAccessToken(token_hash="sha256...")

        # Verify:
        pat = await pat_manager.verify("pat_abc123...")
        if pat:
            print(pat.user_id, pat.scopes)

        # Revoke:
        await pat_manager.revoke(token_id=1)

        # List user tokens:
        tokens = await pat_manager.list_for_user("123")
    """

    TOKEN_PREFIX = "pat_"

    def __init__(self, store: Any | None = None) -> None:
        self._store = store  # Repository or dict
        self._memory: dict[str, PersonalAccessToken] = {}  # hash → PAT

    async def create(
        self, user_id: str, name: str, scopes: list[str] | None = None, expires_in_days: int | None = None
    ) -> tuple:
        """Create new PAT. Returns (plain_token, PersonalAccessToken)."""
        plain = self.TOKEN_PREFIX + secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain.encode()).hexdigest()

        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        expires = None
        if expires_in_days:
            expires = (now + datetime.timedelta(days=expires_in_days)).isoformat()

        pat = PersonalAccessToken(
            user_id=str(user_id),
            name=name,
            token_hash=token_hash,
            scopes=scopes or [],
            expires_at=expires,
            created_at=now.isoformat(),
        )

        # Store
        self._memory[token_hash] = pat

        if self._store and hasattr(self._store, "create"):
            saved = await self._store.create(
                **{
                    "user_id": pat.user_id,
                    "name": pat.name,
                    "token_hash": pat.token_hash,
                    "scopes": ",".join(pat.scopes),
                    "expires_at": pat.expires_at,
                }
            )
            pat.id = getattr(saved, "id", None)

        logger.info("PAT created: '%s' for user %s", name, user_id)
        return plain, pat

    async def verify(self, plain_token: str) -> PersonalAccessToken | None:
        """Verify a plain token, return PAT if valid."""
        if not plain_token.startswith(self.TOKEN_PREFIX):
            return None

        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        pat = self._memory.get(token_hash)
        if pat is None and self._store:
            found = await self._store.find_by(token_hash=token_hash)
            if found:
                pat = PersonalAccessToken(
                    id=found.id,
                    user_id=found.user_id,
                    name=found.name,
                    token_hash=found.token_hash,
                    scopes=found.scopes.split(",") if isinstance(found.scopes, str) else [],
                    expires_at=str(found.expires_at) if found.expires_at else None,
                )

        if pat is None:
            return None

        if pat.is_expired:
            return None

        return pat

    async def revoke(self, token_id: int | None = None, token_hash: str | None = None) -> bool:
        """Revoke a PAT."""
        if token_hash:
            self._memory.pop(token_hash, None)
        if token_id and self._store:
            return await self._store.delete_by_id(token_id)
        return True

    async def revoke_all(self, user_id: str) -> int:
        """Revoke all PATs for a user."""
        count = 0
        to_remove = [h for h, p in self._memory.items() if p.user_id == user_id]
        for h in to_remove:
            del self._memory[h]
            count += 1
        return count

    async def list_for_user(self, user_id: str) -> list[PersonalAccessToken]:
        """List all PATs for a user (without plain tokens)."""
        result = [p for p in self._memory.values() if p.user_id == user_id]
        return result
