"""
Custom FastAPI Middleware for MotherCare AI

Includes:
- Rate limiting middleware
- Request logging middleware
- CORS configuration
- Security headers
"""

import time
import logging
import jwt
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limiter import check_rate_limit, get_retry_after, log_rate_limit_event

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limiting on API endpoints."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract endpoint path
        endpoint = f"{request.method} {request.url.path}"
        
        # Get user ID from token if available
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            try:
                # Extract token
                token = auth_header[7:]  # Remove "Bearer " prefix
                # Try to decode without verification (just to get the sub claim)
                # In production, you'd verify the signature
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get("sub")  # "sub" is the username/user_id claim
            except Exception as e:
                # If token parsing fails, fall back to IP-based limiting
                logger.debug(f"Could not extract user_id from token: {e}")
                user_id = None
        
        # Fall back to IP address if no user_id extracted
        if not user_id:
            user_id = request.client.host if request.client else "unknown"
        
        # Check rate limit
        allowed, remaining = check_rate_limit(endpoint, user_id)
        
        if not allowed:
            retry_after = get_retry_after(endpoint)
            log_rate_limit_event(endpoint, user_id, request.client.host if request.client else None)
            
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "message": "Rate limit exceeded. Please slow down.",
                    "detail": f"Too many requests. Try again in {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and status information."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Incoming request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent", "Unknown")
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                f"Request error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": f"{duration_ms:.1f}",
                "client_ip": request.client.host if request.client else None
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


def get_cors_middleware() -> Middleware:
    """Configure CORS middleware."""
    return CORSMiddleware(
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Remaining", "Retry-After"],
    )


def setup_middleware(app):
    """Setup all middleware for the application."""
    
    # Add security headers middleware (innermost)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Add CORS middleware (outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Remaining", "Retry-After"],
    )
    
    return app
