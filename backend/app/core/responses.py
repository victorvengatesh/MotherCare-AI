"""
Standardized Response Format

All API responses follow a consistent structure to prevent frontend breakage
and ensure predictable error handling.
"""
from typing import Any, Optional
from fastapi.responses import JSONResponse


def standard_response(
    status_code: int,
    data: Any = None,
    message: str = "",
    success: Optional[bool] = None,
) -> JSONResponse:
    """
    Create a standardized API response.

    Args:
        status_code: HTTP status code
        data: Response payload
        message: Human-readable message
        success: Override success determination (default: status_code < 400)

    Returns:
        JSONResponse with consistent structure
    """
    if success is None:
        success = 400 > status_code

    return JSONResponse(
        status_code=status_code,
        content={
            "success": success,
            "data": data,
            "message": message,
            "status_code": status_code,
        },
    )


def success_response(data: Any = None, message: str = "Success") -> JSONResponse:
    """Create a 200 success response."""
    return standard_response(200, data=data, message=message, success=True)


def created_response(data: Any = None, message: str = "Created") -> JSONResponse:
    """Create a 201 created response."""
    return standard_response(201, data=data, message=message, success=True)


def bad_request_response(message: str = "Bad Request") -> JSONResponse:
    """Create a 400 bad request response."""
    return standard_response(400, message=message, success=False)


def unauthorized_response(message: str = "Unauthorized") -> JSONResponse:
    """Create a 401 unauthorized response."""
    return standard_response(401, message=message, success=False)


def server_error_response(
    message: str = "An unexpected server error occurred",
    detail: str = "",
) -> JSONResponse:
    """Create a 500 error response."""
    return standard_response(
        500,
        data={"detail": detail} if detail else None,
        message=message,
        success=False,
    )


def service_unavailable_response(
    message: str = "Service temporarily unavailable. Please try again shortly."
) -> JSONResponse:
    """Create a 503 service unavailable response."""
    return standard_response(503, message=message, success=False)
