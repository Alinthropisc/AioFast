from .auth_exceptions import AuthorizationException, PermissionException, RoleException
from .base import AioFastException, ContainerException
from .configuration_exceptions import (
    ConfigError,
    ConfigKeyError,
    ConfigLoadError,
    ConfigurationError,
    ConfigValidationError,
    EnvironmentError,
    EnvironmentKeyError,
    FrozenConfigError,
)
from .console_exceptions import (
    CommandLockException,
    CommandNotFoundException,
    CommandTimeoutException,
    CommandValidationException,
    ConsoleException,
    EnvironmentGuardException,
    InvalidOptionException,
    MissingArgumentException,
    TooManyArgumentsException,
)
from .database_exceptions import ModelNotFoundError
from .foundation_exceptions import (
    BindingNotFoundError,
    BindingNotFoundException,
    BindingResolutionException,
    CircularDependencyError,
    CircularDependencyException,
    ContainerError,
    MissingContainerBindingNotFound,
    StrictContainerException,
)
from .http_exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    HTTPException,
    InternalServerException,
    MethodNotAllowedException,
    NotFoundException,
    ServiceUnavailableException,
    TooManyRequestsException,
    UnauthorizedException,
    ValidationException,
)
from .registry_exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

__all__ = [
    "AioFastException",
    # Auth Exceptions
    "AuthorizationException",
    "BadRequestException",
    "BindingNotFoundError",
    "BindingNotFoundException",
    "BindingResolutionException",
    "CircularDependencyError",
    "CircularDependencyException",
    "CommandLockException",
    "CommandNotFoundException",
    "CommandTimeoutException",
    "CommandValidationException",
    "ConfigError",
    "ConfigKeyError",
    "ConfigKeyError",
    "ConfigLoadError",
    "ConfigValidationError",
    "ConfigurationError",
    "ConflictException",
    # Console
    "ConsoleException",
    "ContainerError",
    "ContainerException",
    "EnvironmentError",
    "EnvironmentGuardException",
    "EnvironmentKeyError",
    "ForbiddenException",
    "FrozenConfigError",
    # HTTP
    "HTTPException",
    "InternalServerException",
    "InvalidOptionException",
    "MethodNotAllowedException",
    "MissingArgumentException",
    "MissingContainerBindingNotFound",
    # Database Exception
    "ModelNotFoundError",
    "NotFoundException",
    "PermissionException",
    "RoleException",
    "ServiceUnavailableException",
    "StrictContainerException",
    "TooManyArgumentsException",
    "TooManyRequestsException",
    "UnauthorizedException",
    "ValidationException",
    "generic_exception_handler",
    # Registry Exceptions
    "http_exception_handler",
    "validation_exception_handler",
]
