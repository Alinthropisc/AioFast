from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from litestar import Request, Response

if TYPE_CHECKING:
    from .http_exceptions import HTTPException, ValidationException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    logger.warning("HTTP %d: %s [%s %s]", exc.status_code, exc.detail, request.method, request.url.path)
    return Response(content=exc.to_dict(), status_code=exc.status_code, headers=exc.headers or None)


async def validation_exception_handler(request: Request, exc: ValidationException) -> Response:
    logger.warning("Validation error: %s [%s %s]", exc.errors, request.method, request.url.path)
    return Response(content=exc.to_dict(), status_code=422)


async def generic_exception_handler(request: Request, exc: Exception) -> Response:
    logger.exception("Unhandled exception: %s [%s %s]", exc, request.method, request.url.path)
    return Response(
        content={
            "success": False,
            "message": "Internal Server Error",
        },
        status_code=500,
    )
