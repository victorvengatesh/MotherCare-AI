"""
Rate Limiting Middleware for MotherCare AI

Implements per-endpoint and per-user rate limiting using token bucket algorithm.
Prevents abuse and protects against brute-force attacks.
"""

import time
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Configuration:
    - max_tokens: Maximum tokens in bucket (requests allowed)
    - refill_rate: Tokens refilled per second
    """
    
    def __init__(self, max_tokens: int = 100, refill_rate: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_tokens: Max requests allowed per window
            refill_rate: Tokens to add per second (refill_rate tokens per second)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = Lock()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        with self._lock:
            self._refill()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            return False
    
    def _refill(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_remaining(self) -> int:
        """Get remaining tokens."""
        with self._lock:
            self._refill()
            return int(self.tokens)


class PerUserRateLimiter:
    """
    Per-user rate limiter using token bucket algorithm.
    Tracks rate limits for different users independently.
    """
    
    def __init__(self, max_tokens: int = 100, refill_rate: float = 1.0, cleanup_interval: int = 300):
        """
        Initialize per-user rate limiter.
        
        Args:
            max_tokens: Max tokens per user
            refill_rate: Tokens to add per second
            cleanup_interval: Seconds between cleanup of inactive users
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.cleanup_interval = cleanup_interval
        self.limiters: Dict[str, RateLimiter] = {}
        self.last_cleanup = time.time()
        self._lock = Lock()
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is allowed to make a request."""
        with self._lock:
            self._cleanup_if_needed()
            
            if user_id not in self.limiters:
                self.limiters[user_id] = RateLimiter(self.max_tokens, self.refill_rate)
            
            return self.limiters[user_id].is_allowed()
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining tokens for user."""
        with self._lock:
            if user_id not in self.limiters:
                return self.max_tokens
            
            return self.limiters[user_id].get_remaining()
    
    def _cleanup_if_needed(self):
        """Remove inactive user limiters."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove limiters that haven't been used
        active_users = set()
        for user_id, limiter in list(self.limiters.items()):
            # Keep limiters that still have tokens or were recently used
            if limiter.tokens < limiter.max_tokens or (now - limiter.last_refill) < 60:
                active_users.add(user_id)
        
        self.limiters = {uid: self.limiters[uid] for uid in active_users}
        self.last_cleanup = now
        
        logger.info(f"Rate limiter cleanup: {len(active_users)} active users remaining")


# Global rate limiters
# Endpoint-level limits
auth_limiter = RateLimiter(max_tokens=10, refill_rate=1.0)  # 10 requests per 10 seconds
chat_limiter = PerUserRateLimiter(max_tokens=30, refill_rate=0.5)  # 30 requests per 60 seconds per user
upload_limiter = PerUserRateLimiter(max_tokens=5, refill_rate=0.1)  # 5 uploads per 50 seconds per user
twin_limiter = PerUserRateLimiter(max_tokens=50, refill_rate=1.0)  # 50 requests per 50 seconds per user

# Default limiter for other endpoints
default_limiter = RateLimiter(max_tokens=100, refill_rate=2.0)  # 100 requests per 50 seconds


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


# Rate limit configurations by endpoint
RATE_LIMIT_CONFIG = {
    # Authentication
    "POST /auth/register": {"limiter": auth_limiter, "per_user": False},
    "POST /auth/login": {"limiter": auth_limiter, "per_user": False},
    
    # Chat & AI
    "POST /ai/chat": {"limiter": chat_limiter, "per_user": True},
    "POST /ai/upload-report": {"limiter": upload_limiter, "per_user": True},
    
    # Digital Twin
    "GET /ai/twin": {"limiter": twin_limiter, "per_user": True},
    "PUT /ai/twin": {"limiter": twin_limiter, "per_user": True},
    "GET /ai/records": {"limiter": twin_limiter, "per_user": True},
}


def get_rate_limiter(endpoint: str, user_id: str = None) -> Tuple[RateLimiter | PerUserRateLimiter, bool]:
    """
    Get appropriate rate limiter for endpoint.
    
    Args:
        endpoint: API endpoint path
        user_id: User ID (for per-user limiters)
    
    Returns:
        Tuple of (limiter, is_per_user)
    """
    config = RATE_LIMIT_CONFIG.get(endpoint)
    
    if config:
        return config["limiter"], config["per_user"]
    
    return default_limiter, False


def check_rate_limit(endpoint: str, user_id: str = None) -> Tuple[bool, int]:
    """
    Check if request is allowed.
    
    Args:
        endpoint: API endpoint path
        user_id: User ID (for per-user limiters)
    
    Returns:
        Tuple of (allowed, remaining_tokens)
    """
    limiter, is_per_user = get_rate_limiter(endpoint, user_id)
    
    try:
        if is_per_user and user_id:
            allowed = limiter.is_allowed(user_id)
            remaining = limiter.get_remaining(user_id)
        else:
            allowed = limiter.is_allowed()
            remaining = limiter.get_remaining()
        
        return allowed, remaining
    except Exception as e:
        logger.error(f"Rate limiter error: {e}")
        # On error, allow the request
        return True, -1


def get_retry_after(endpoint: str) -> int:
    """
    Calculate retry-after time in seconds.
    
    Args:
        endpoint: API endpoint path
    
    Returns:
        Retry-after time in seconds
    """
    limiter, _ = get_rate_limiter(endpoint)
    
    # Calculate based on refill rate
    if isinstance(limiter, RateLimiter):
        if limiter.refill_rate > 0:
            return int(1 / limiter.refill_rate)
    elif isinstance(limiter, PerUserRateLimiter):
        if limiter.refill_rate > 0:
            return int(1 / limiter.refill_rate)
    
    return 60


# Logging configuration for rate limit events
def log_rate_limit_event(endpoint: str, user_id: str = None, ip_address: str = None):
    """Log when rate limit is exceeded."""
    logger.warning(
        f"Rate limit exceeded",
        extra={
            "endpoint": endpoint,
            "user_id": user_id,
            "ip_address": ip_address
        }
    )
