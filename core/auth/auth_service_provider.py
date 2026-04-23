from __future__ import annotations

import os

from ..foundation.service_provider import ServiceProvider
from .access import AccessManager
from .auth_events import AuthEventDispatcher
from .casbin_guard import CasbinGuard
from .gate import Gate
from .guards import GuardManager
from .mfa import MFAManager
from .oauth import OAuthManager
from .password import PasswordHasher, PasswordResetManager, PasswordValidator
from .policy import PolicyRegistry
from .session_manager import SessionManager
from .throttle import LoginThrottle
from .tokens import PersonalAccessTokenManager, TokenManager


class AuthorizationServiceProvider(ServiceProvider):
    """
    Registers all auth components:
      - Gate, PolicyRegistry, AccessManager
      - GuardManager, TokenManager
      - PasswordHasher, PasswordValidator
      - MFAManager, OAuthManager
      - SessionManager, LoginThrottle
      - AuthEventDispatcher
    """

    async def register(self) -> None:
        # Core auth
        gate = Gate()
        policies = PolicyRegistry()
        access = AccessManager()

        self.app.instance(Gate, gate)
        self.app.instance("gate", gate)
        self.app.instance(PolicyRegistry, policies)
        self.app.instance("policies", policies)
        self.app.instance(AccessManager, access)
        self.app.instance("access", access)
        # Guards
        guard_manager = GuardManager()
        self.app.instance(GuardManager, guard_manager)
        self.app.instance("guards", guard_manager)
        # Tokens
        secret = os.getenv("APP_SECRET", os.getenv("JWT_SECRET", "change-me"))
        token_manager = TokenManager(
            secret=secret,
            access_ttl=int(os.getenv("JWT_ACCESS_TTL", "3600")),
            refresh_ttl=int(os.getenv("JWT_REFRESH_TTL", "604800")),
        )
        self.app.instance(TokenManager, token_manager)
        self.app.instance("tokens", token_manager)
        # PAT
        pat_manager = PersonalAccessTokenManager()
        self.app.instance(PersonalAccessTokenManager, pat_manager)
        # Password
        hasher = PasswordHasher(
            algorithm=os.getenv("PASSWORD_ALGORITHM", "bcrypt"), rounds=int(os.getenv("PASSWORD_ROUNDS", "12"))
        )
        self.app.instance(PasswordHasher, hasher)
        self.app.instance(PasswordValidator, PasswordValidator())
        self.app.instance(PasswordResetManager, PasswordResetManager())
        # MFA
        self.app.instance(MFAManager, MFAManager())
        # OAuth
        self.app.instance(OAuthManager, OAuthManager())
        # Sessions
        self.app.instance(SessionManager, SessionManager())
        # Throttle
        self.app.instance(
            LoginThrottle,
            LoginThrottle(
                max_attempts=int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")),
                lockout_seconds=int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300")),
            ),
        )
        # Events
        self.app.instance(AuthEventDispatcher, AuthEventDispatcher())

    async def boot(self) -> None:
        access: AccessManager = await self.app.make(AccessManager)

        # Casbin
        config = await self.app.make_or("config")
        if config is not None:
            casbin_config = config.get("auth.casbin", None)
            if casbin_config and isinstance(casbin_config, dict):
                guard = CasbinGuard()
                model_path = casbin_config.get("model")
                policy_path = casbin_config.get("policy")
                if model_path and policy_path:
                    await guard.init_from_file(model_path, policy_path)
                else:
                    await guard.init_rbac()
                self.app.instance(CasbinGuard, guard)
                self.app.instance("casbin", guard)
                access.set_casbin(guard)
