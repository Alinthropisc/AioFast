from __future__ import annotations

from typing import Any

from .base import AioFastException


class HTTPException(AioFastException):
    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal Server Error",
        errors: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.errors = errors or {}
        self.headers = headers or {}
        super().__init__(detail)

    def to_dict(self) -> dict:
        result = {
            "message": self.detail,
            "status_code": self.status_code,
        }
        if self.errors:
            result["errors"] = self.errors
        return result


class BadRequestException(HTTPException):
    def __init__(self, detail: str = "Bad Request", **kwargs):
        super().__init__(400, detail, **kwargs)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Unauthorized", **kwargs):
        super().__init__(401, detail, **kwargs)


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Forbidden", **kwargs):
        super().__init__(403, detail, **kwargs)


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Not Found", **kwargs):
        super().__init__(404, detail, **kwargs)


class MethodNotAllowedException(HTTPException):
    def __init__(self, detail: str = "Method Not Allowed", **kwargs):
        super().__init__(405, detail, **kwargs)


class ConflictException(HTTPException):
    def __init__(self, detail: str = "Conflict", **kwargs):
        super().__init__(409, detail, **kwargs)


class ValidationException(HTTPException):
    def __init__(self, errors: dict[str, Any], detail: str = "Validation Error"):
        super().__init__(422, detail, errors=errors)


class TooManyRequestsException(HTTPException):
    def __init__(self, detail: str = "Too Many Requests", retry_after: int = 60):
        super().__init__(429, detail, headers={"Retry-After": str(retry_after)})
        self.retry_after = retry_after


class InternalServerException(HTTPException):
    def __init__(self, detail: str = "Internal Server Error", **kwargs):
        super().__init__(500, detail, **kwargs)


class ServiceUnavailableException(HTTPException):
    def __init__(self, detail: str = "Service Unavailable", **kwargs):
        super().__init__(503, detail, **kwargs)
