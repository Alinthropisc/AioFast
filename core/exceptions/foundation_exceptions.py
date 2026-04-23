from .base import ContainerException


class ContainerError(Exception):
    pass


class MissingContainerBindingNotFound(ContainerError):
    pass


class StrictContainerException(ContainerError):
    pass


class BindingNotFoundError(ContainerError):
    pass


class CircularDependencyError(ContainerError):
    pass


class BindingNotFoundException(ContainerException):
    def __init__(self, key):
        super().__init__(f"Binding '{key}' not found in the container")
        self.key = key


class BindingResolutionException(ContainerException):
    def __init__(self, key, reason: str = ""):
        msg = f"Cannot resolve binding '{key}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.key = key


class CircularDependencyException(ContainerException):
    def __init__(self, chain: list):
        path = " -> ".join(str(c) for c in chain)
        super().__init__(f"Circular dependency detected: {path}")
        self.chain = chain
