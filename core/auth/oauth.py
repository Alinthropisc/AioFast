from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OAuthUser:
    """Normalized user data from OAuth provider."""

    provider: str
    provider_id: str
    email: str | None = None
    name: str | None = None
    avatar: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=list)
    authorize_url: str = ""
    token_url: str = ""
    user_info_url: str = ""


class OAuthProvider:
    """
    Base OAuth2 provider.

    Usage:
        provider = GitHubProvider(OAuthConfig(
            client_id="...",
            client_secret="...",
            redirect_uri="http://localhost/callback",
        ))

        # Step 1: Redirect user
        url = provider.get_authorize_url(state="random_state")

        # Step 2: Handle callback
        user = await provider.handle_callback(code="...", state="...")
        # OAuthUser(provider="github", provider_id="123", email="...", name="...")
    """

    name: str = "base"

    def __init__(self, config: OAuthConfig) -> None:
        self.config = config

    def get_authorize_url(self, state: str | None = None) -> str:
        """Build authorization URL."""
        import urllib.parse

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "response_type": "code",
            "state": state,
        }

        return f"{self.config.authorize_url}?{urllib.parse.urlencode(params)}"

    async def handle_callback(self, code: str, state: str | None = None) -> OAuthUser:
        """Exchange code for token, fetch user info."""
        token = await self._exchange_code(code)
        return await self._fetch_user(token)

    async def _exchange_code(self, code: str) -> str:
        """Exchange authorization code for access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError("Install httpx: pip install httpx")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            data = response.json()
            return data.get("access_token", "")

    async def _fetch_user(self, token: str) -> OAuthUser:
        """Fetch user info from provider. Override in subclasses."""
        raise NotImplementedError

    def generate_state(self) -> str:
        return secrets.token_urlsafe(32)


# ── GitHub ────────────────────────────────────────────────


class GitHubProvider(OAuthProvider):
    name = "github"

    def __init__(self, config: OAuthConfig) -> None:
        config.authorize_url = config.authorize_url or "https://github.com/login/oauth/authorize"
        config.token_url = config.token_url or "https://github.com/login/oauth/access_token"
        config.user_info_url = config.user_info_url or "https://api.github.com/user"
        config.scopes = config.scopes or ["user:email"]
        super().__init__(config)

    async def _fetch_user(self, token: str) -> OAuthUser:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.config.user_info_url, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()

            # Fetch email separately if needed
            email = data.get("email")
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails", headers={"Authorization": f"Bearer {token}"}
                )
                emails = email_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                if primary:
                    email = primary["email"]

        return OAuthUser(
            provider="github",
            provider_id=str(data["id"]),
            email=email,
            name=data.get("name") or data.get("login"),
            avatar=data.get("avatar_url"),
            raw=data,
        )


# ── Google ────────────────────────────────────────────────


class GoogleProvider(OAuthProvider):
    name = "google"

    def __init__(self, config: OAuthConfig) -> None:
        config.authorize_url = config.authorize_url or "https://accounts.google.com/o/oauth2/v2/auth"
        config.token_url = config.token_url or "https://oauth2.googleapis.com/token"
        config.user_info_url = config.user_info_url or "https://www.googleapis.com/oauth2/v2/userinfo"
        config.scopes = config.scopes or ["openid", "email", "profile"]
        super().__init__(config)

    async def _fetch_user(self, token: str) -> OAuthUser:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.config.user_info_url, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()

        return OAuthUser(
            provider="google",
            provider_id=data["id"],
            email=data.get("email"),
            name=data.get("name"),
            avatar=data.get("picture"),
            raw=data,
        )


# ── Discord ───────────────────────────────────────────────


class DiscordProvider(OAuthProvider):
    name = "discord"

    def __init__(self, config: OAuthConfig) -> None:
        config.authorize_url = config.authorize_url or "https://discord.com/api/oauth2/authorize"
        config.token_url = config.token_url or "https://discord.com/api/oauth2/token"
        config.user_info_url = config.user_info_url or "https://discord.com/api/users/@me"
        config.scopes = config.scopes or ["identify", "email"]
        super().__init__(config)

    async def _fetch_user(self, token: str) -> OAuthUser:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.config.user_info_url, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
        avatar = None

        if data.get("avatar"):
            avatar = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png"

        return OAuthUser(
            provider="discord",
            provider_id=data["id"],
            email=data.get("email"),
            name=data.get("username"),
            avatar=avatar,
            raw=data,
        )


# ── OAuth Manager ─────────────────────────────────────────


class OAuthManager:
    """
    Central OAuth manager.

    Usage:
        oauth = OAuthManager()
        oauth.register("github", GitHubProvider(config))
        oauth.register("google", GoogleProvider(config))

        url = oauth.provider("github").get_authorize_url()
        user = await oauth.provider("github").handle_callback(code="...")
    """

    def __init__(self) -> None:
        self._providers: dict[str, OAuthProvider] = {}

    def register(self, name: str, provider: OAuthProvider) -> OAuthManager:
        self._providers[name] = provider
        return self

    def provider(self, name: str) -> OAuthProvider:
        p = self._providers.get(name)
        if p is None:
            raise KeyError(f"OAuth provider '{name}' not registered")
        return p

    @property
    def providers(self) -> list[str]:
        return list(self._providers.keys())

    def __repr__(self) -> str:
        return f"<OAuthManager providers={self.providers}>"
