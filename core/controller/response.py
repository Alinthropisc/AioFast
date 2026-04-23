from __future__ import annotations

from typing import Any


class ApiResponse:
    """
    Standardized API response builder.

    Usage:
        return ApiResponse.success(data=users)
        return ApiResponse.created(data=user)
        return ApiResponse.error("Not found", status=404)
        return ApiResponse.paginated(items, total=100, page=1, per_page=20)
        return ApiResponse.no_content()
    """

    @staticmethod
    def success(
        data: Any = None, message: str = "Success", *, meta: dict[str, Any] | None = None, status: int = 200
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": True,
            "message": message,
            "status": status,
        }
        if data is not None:
            result["data"] = data
        if meta:
            result["meta"] = meta
        return result

    @staticmethod
    def created(data: Any = None, message: str = "Created") -> dict[str, Any]:
        return ApiResponse.success(data=data, message=message, status=201)

    @staticmethod
    def no_content() -> dict[str, Any]:
        return {"success": True, "status": 204}

    @staticmethod
    def error(
        message: str = "Error", *, status: int = 400, errors: Any | None = None, code: str | None = None
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False,
            "message": message,
            "status": status,
        }
        if errors is not None:
            result["errors"] = errors
        if code:
            result["code"] = code
        return result

    @staticmethod
    def not_found(message: str = "Not Found", *, resource: str | None = None) -> dict[str, Any]:
        msg = f"{resource} not found" if resource else message
        return ApiResponse.error(msg, status=404, code="NOT_FOUND")

    @staticmethod
    def validation_error(errors: Any, message: str = "Validation Error") -> dict[str, Any]:
        return ApiResponse.error(message, status=422, errors=errors, code="VALIDATION_ERROR")

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> dict[str, Any]:
        return ApiResponse.error(message, status=401, code="UNAUTHORIZED")

    @staticmethod
    def forbidden(message: str = "Forbidden") -> dict[str, Any]:
        return ApiResponse.error(message, status=403, code="FORBIDDEN")

    @staticmethod
    def server_error(message: str = "Internal Server Error") -> dict[str, Any]:
        return ApiResponse.error(message, status=500, code="SERVER_ERROR")

    @staticmethod
    def paginated(data: list[Any], *, total: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        total_pages = (total + per_page - 1) // per_page
        return ApiResponse.success(
            data=data,
            meta={
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
        )

    @staticmethod
    def collection(data: list[Any], *, message: str = "Success", meta: dict[str, Any] | None = None) -> dict[str, Any]:
        result_meta = {"count": len(data)}
        if meta:
            result_meta.update(meta)
        return ApiResponse.success(data=data, message=message, meta=result_meta)
