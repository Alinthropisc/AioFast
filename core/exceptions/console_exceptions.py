from .base import AioFastException


class ConsoleException(AioFastException):
    pass


class CommandNotFoundException(ConsoleException):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Command '{name}' not found")


class CommandValidationException(ConsoleException):
    def __init__(self, command: str, errors: list[str]) -> None:
        self.command = command
        self.errors = errors
        super().__init__(f"Validation failed for '{command}': {'; '.join(errors)}")


class TooManyArgumentsException(ConsoleException):
    def __init__(self, command: str) -> None:
        super().__init__(f"Too many arguments for command '{command}'")


class MissingArgumentException(ConsoleException):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Missing required argument: '{name}'")


class InvalidOptionException(ConsoleException):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Invalid option: '{name}'")


class CommandLockException(ConsoleException):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Command '{name}' is already running")


class CommandTimeoutException(ConsoleException):
    def __init__(self, name: str, seconds: int) -> None:
        self.name = name
        self.seconds = seconds
        super().__init__(f"Command '{name}' timed out after {seconds}s")


class EnvironmentGuardException(ConsoleException):
    def __init__(self, name: str, env: str, allowed: list[str]) -> None:
        self.name = name
        self.env = env
        self.allowed = allowed
        super().__init__(f"Command '{name}' cannot run in '{env}'. Allowed: {', '.join(allowed)}")
