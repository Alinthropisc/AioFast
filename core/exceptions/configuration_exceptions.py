from .base import AioFastException


class ConfigurationError(AioFastException):
    pass


class ConfigLoadError(ConfigurationError):
    pass


class ConfigValidationError(ConfigurationError):
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class EnvironmentError(AioFastException):
    pass


class EnvironmentKeyError(EnvironmentError):
    pass


class ConfigError(Exception):
    pass


class ConfigKeyError(ConfigError, KeyError):
    pass


class FrozenConfigError(ConfigError):
    pass
