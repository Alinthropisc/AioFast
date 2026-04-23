from .access import AccessManager
from .auth_events import (
    AuthEvent,
    AuthEventDispatcher,
    FailedLoginEvent,
    LockoutEvent,
    LoginEvent,
    LogoutEvent,
    MFAEnabledEvent,
    MFAVerifiedEvent,
    PasswordResetEvent,
    TokenIssuedEvent,
    TokenRevokedEvent,
)
from .auth_service_provider import AuthorizationServiceProvider
from .casbin_guard import ABAC_MODEL, RBAC_MODEL, CasbinGuard
from .decorators import authorize, requires_permission, requires_role
from .gate import Gate, Response
from .guards import (
    ApiKeyGuard,
    CompositeGuard,
    Guard,
    GuardManager,
    JWTGuard,
    SessionGuard,
)
from .mfa import TOTP, BackupCodes, MFAManager
from .middleware import AuthorizationMiddleware
from .oauth import (
    DiscordProvider,
    GitHubProvider,
    GoogleProvider,
    OAuthConfig,
    OAuthManager,
    OAuthProvider,
    OAuthUser,
)
from .password import PasswordHasher, PasswordResetManager, PasswordValidator
from .policy import Policy, PolicyRegistry
from .session_manager import DeviceSession, SessionManager
from .throttle import LoginThrottle
from .tokens import PersonalAccessToken, PersonalAccessTokenManager, TokenManager, TokenPair
from .user_mixin import Authenticatable, HasApiTokens, HasMFA, HasRoles

__all__ = [
    "ABAC_MODEL",
    "RBAC_MODEL",
    # MFA
    "TOTP",
    # Core
    "AccessManager",
    "ApiKeyGuard",
    "AuthEvent",
    # Events
    "AuthEventDispatcher",
    # User Mixins
    "Authenticatable",
    # Exceptions
    "AuthorizationException",
    "AuthorizationMiddleware",
    # Provider
    "AuthorizationServiceProvider",
    "BackupCodes",
    # Casbin
    "CasbinGuard",
    "CompositeGuard",
    "DeviceSession",
    "DiscordProvider",
    "FailedLoginEvent",
    "Gate",
    "GitHubProvider",
    "GoogleProvider",
    # Guards
    "Guard",
    "GuardManager",
    "HasApiTokens",
    "HasMFA",
    "HasRoles",
    "JWTGuard",
    "LockoutEvent",
    "LoginEvent",
    # Throttle
    "LoginThrottle",
    "LogoutEvent",
    "MFAEnabledEvent",
    "MFAManager",
    "MFAVerifiedEvent",
    "OAuthConfig",
    # OAuth
    "OAuthManager",
    "OAuthProvider",
    "OAuthUser",
    # Password
    "PasswordHasher",
    "PasswordResetEvent",
    "PasswordResetManager",
    "PasswordValidator",
    "PermissionException",
    "PersonalAccessToken",
    "PersonalAccessTokenManager",
    "Policy",
    "PolicyRegistry",
    "Response",
    "RoleException",
    "SessionGuard",
    # Sessions
    "SessionManager",
    "TokenIssuedEvent",
    # Tokens
    "TokenManager",
    "TokenPair",
    "TokenRevokedEvent",
    # Decorators & Middleware
    "authorize",
    "requires_permission",
    "requires_role",
]
