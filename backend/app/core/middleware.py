"""Custom middleware for MotherCare AI.

CORS is intentionally configured once in ``app.main`` from ``ALLOWED_ORIGINS``.
This module owns rate limiting, request logging, and security headers only.
"""

import logging
import os
import time
from typing import Callable

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limiter import check_rate_limit, get_retry_after, log_rate_limit_event

logger = logging.getLogger(__name__)


def _request_path(request: Request) -> str:
    """Return the router-facing ASGI path, independent of the Host header.

    Older Starlette versions can reconstruct ``request.url.path`` from an
    attacker-controlled malformed Host header. Security decisions such as
    rate-limit bucket selection must therefore use the raw ASGI scope path.
    """
    return request.scope.get("path") or "/"


def _get_rate_limit_identity(request: Request) -> str:
    """Return a trusted rate-limit identity.

    A JWT subject is used only after signature and access-token verification.
    Invalid, forged, or refresh tokens fall back to the client IP so callers
    cannot rotate arbitrary ``sub`` claims to bypass per-user rate limits.
    """
    auth_header = request.headers.get("Authorization", "")
    secret_key = os.getenv("MC_SECRET_KEY")

    if secret_key and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            if payload.get("type", "access") == "access" and payload.get("sub"):
                return f"user:{payload['sub']}"
        except jwt.PyJWTError:
            logger.debug("Invalid bearer token supplied to rate limiter")

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limiting on API endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        endpoint = f"{request.method} {_request_path(request)}"
        identity = _get_rate_limit_identity(request)

        allowed, remaining = check_rate_limit(endpoint, identity)

        if not allowed:
            retry_after = get_retry_after(endpoint)
            log_rate_limit_event(
                endpoint,
                identity,
                request.client.host if request.client else None,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "message": "Rate limit exceeded. Please slow down.",
                    "detail": f"Too many requests. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log requests with timing and status information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        path = _request_path(request)

        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "path": path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent", "Unknown"),
            },
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "Request error",
                extra={
                    "method": request.method,
                    "path": path,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": f"{duration_ms:.1f}",
                "client_ip": request.client.host if request.client else None,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add baseline security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


def setup_middleware(app):
    """Install non-CORS middleware.

    CORS is installed in ``app.main`` so deployment-specific origins are not
    overwritten by a second hard-coded middleware layer.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    return app
