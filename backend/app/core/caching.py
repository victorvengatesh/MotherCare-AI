"""
Caching Layer for MotherCare AI — Phase 4 Upgrade

Implements:
- In-memory caching with TTL (SimpleCache — dev / Redis-unavailable fallback)
- Redis-backed distributed caching (RedisCache — production)
- CacheFactory auto-selects based on REDIS_URL environment variable
- Transparent decorator API (@cached, @cache_clear) — call-sites unchanged
"""

import os
import time
import json
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache (fallback / dev)
# ---------------------------------------------------------------------------

class CacheEntry:
    """Represents a cached value with TTL."""

    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    def get(self) -> Optional[Any]:
        if self.is_expired():
            return None
        return self.value


class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.cache:
                return None
            entry = self.cache[key]
            if entry.is_expired():
                del self.cache[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300):
        with self._lock:
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
                del self.cache[oldest_key]
            self.cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str):
        with self._lock:
            self.cache.pop(key, None)

    def clear(self):
        with self._lock:
            self.cache.clear()

    def cleanup_expired(self):
        with self._lock:
            expired = [k for k, v in self.cache.items() if v.is_expired()]
            for k in expired:
                del self.cache[k]
            if expired:
                logger.debug(f"Cleaned {len(expired)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self.cleanup_expired()
            return {
                "backend": "memory",
                "size": len(self.cache),
                "max_size": self.max_size,
                "usage_percent": round((len(self.cache) / self.max_size) * 100, 1),
            }


# ---------------------------------------------------------------------------
# Redis-backed cache (production)
# ---------------------------------------------------------------------------

class RedisCache:
    """
    Redis-backed distributed cache with transparent JSON serialization.
    Falls back gracefully if Redis is unavailable, with a circuit breaker
    to avoid connection latency spikes if Redis goes down.
    """

    def __init__(self, redis_url: str, key_prefix: str = "mc"):
        self._url = redis_url
        self._prefix = key_prefix
        self._client = None
        self._available = False
        self._failed_attempts = 0
        self._last_failure_time = 0.0
        self._cooloff_period = 30.0
        self._max_failures = 3
        self._connect()

    def _connect(self):
        try:
            import redis
            self._client = redis.Redis.from_url(
                self._url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._client.ping()
            self._available = True
            self._failed_attempts = 0
            logger.info("Redis cache connected: %s", self._url)
        except Exception as e:
            self._available = False
            self._failed_attempts = self._max_failures
            self._last_failure_time = time.time()
            logger.warning("Redis unavailable (%s) — falling back to in-memory cache", e)

    def _check_redis_availability(self) -> bool:
        """
        Check if Redis is available. If unavailable, verifies if the cool-off
        period has passed and attempts a single reconnect ping.
        """
        if self._available:
            return True

        now = time.time()
        if now - self._last_failure_time < self._cooloff_period:
            return False

        # Attempt reconnect ping
        try:
            logger.debug("Redis cool-off expired — attempting reconnect ping...")
            self._client.ping()
            self._available = True
            self._failed_attempts = 0
            logger.info("Redis cache reconnected successfully.")
            return True
        except Exception as e:
            self._last_failure_time = now
            logger.warning("Redis reconnect ping failed: %s. Cool-off extended.", e)
            return False

    def _handle_failure(self, error: Exception):
        """Track failures and trip circuit breaker if threshold is hit."""
        self._failed_attempts += 1
        logger.warning("Redis cache error #%d: %s", self._failed_attempts, error)
        if self._failed_attempts >= self._max_failures:
            self._available = False
            self._last_failure_time = time.time()
            logger.error("Redis cache circuit tripped! Offline cool-off active for %s seconds.", self._cooloff_period)

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        if not self._check_redis_availability():
            return None
        try:
            raw = self._client.get(self._key(key))
            self._failed_attempts = 0
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            self._handle_failure(e)
            return None

    def set(self, key: str, value: Any, ttl: int = 300):
        if not self._check_redis_availability():
            return
        try:
            self._client.setex(self._key(key), ttl, json.dumps(value, default=str))
            self._failed_attempts = 0
        except Exception as e:
            self._handle_failure(e)

    def delete(self, key: str):
        if not self._check_redis_availability():
            return
        try:
            self._client.delete(self._key(key))
            self._failed_attempts = 0
        except Exception as e:
            self._handle_failure(e)

    def clear(self):
        """Clear all keys with our prefix (use sparingly)."""
        if not self._check_redis_availability():
            return
        try:
            pattern = f"{self._prefix}:*"
            keys = self._client.keys(pattern)
            if keys:
                self._client.delete(*keys)
            self._failed_attempts = 0
        except Exception as e:
            self._handle_failure(e)

    def get_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {"backend": "redis", "available": self._available}
        if self._available:
            try:
                info = self._client.info("memory")
                stats["used_memory_human"] = info.get("used_memory_human")
                stats["connected_clients"] = self._client.info("clients").get("connected_clients")
            except Exception:
                pass
        return stats


# ---------------------------------------------------------------------------
# Cache factory — auto-select Redis or SimpleCache
# ---------------------------------------------------------------------------

class CacheFactory:
    """Returns the appropriate cache backend based on environment."""

    _instances: Dict[str, Any] = {}

    @classmethod
    def get_cache(cls, name: str, max_size: int = 1000) -> "SimpleCache | RedisCache":
        if name in cls._instances:
            return cls._instances[name]

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            cache = RedisCache(redis_url, key_prefix=f"mc:{name}")
            # If Redis isn't available, fall back to SimpleCache
            if not cache._available:
                cache = SimpleCache(max_size=max_size)
        else:
            cache = SimpleCache(max_size=max_size)

        cls._instances[name] = cache
        return cache


# ---------------------------------------------------------------------------
# Global cache instances (same names as before — call-sites unchanged)
# ---------------------------------------------------------------------------

query_cache = CacheFactory.get_cache("query", max_size=500)   # SQL query results
rag_cache   = CacheFactory.get_cache("rag",   max_size=1000)  # RAG embedding results
twin_cache  = CacheFactory.get_cache("twin",  max_size=2000)  # Digital twin state (TTL 300s)
api_cache   = CacheFactory.get_cache("api",   max_size=300)   # External API responses


# ---------------------------------------------------------------------------
# Decorator helpers — unchanged public interface
# ---------------------------------------------------------------------------

def cache_key(*args, **kwargs) -> str:
    """Generate a stable cache key from function arguments."""
    parts = [str(a) for a in args]
    parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return "|".join(parts)


def cached(cache_instance, ttl: int = 300):
    """
    Decorator — caches the return value of a function.

    Usage:
        @cached(twin_cache, ttl=300)
        def get_twin(user_id: str, db): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            cached_value = cache_instance.get(key)
            if cached_value is not None:
                logger.debug("Cache HIT: %s", key)
                return cached_value
            result = func(*args, **kwargs)
            cache_instance.set(key, result, ttl)
            logger.debug("Cache MISS: %s", key)
            return result
        return wrapper
    return decorator


def cache_clear(*cache_instances):
    """
    Decorator — clears specified caches after function execution.

    Usage:
        @cache_clear(twin_cache, query_cache)
        def update_twin(user_id, data, db): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for c in cache_instances:
                c.clear()
                logger.debug("Cleared cache after %s", func.__name__)
            return result
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

def batch_cache_get(cache_instance, keys: list) -> Dict[str, Any]:
    """Get multiple values from cache in one pass."""
    return {k: v for k in keys if (v := cache_instance.get(k)) is not None}


def batch_cache_set(cache_instance, data: Dict[str, Any], ttl: int = 300):
    """Set multiple key-value pairs in cache."""
    for key, value in data.items():
        cache_instance.set(key, value, ttl)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def cache_maintenance_task():
    """
    Periodic maintenance — clean expired entries from in-memory caches.
    Call from a background scheduler (APScheduler, Celery beat, etc.)
    """
    logger.info("Running cache maintenance...")
    for name, cache in [("query", query_cache), ("rag", rag_cache),
                         ("twin", twin_cache), ("api", api_cache)]:
        if hasattr(cache, "cleanup_expired"):
            cache.cleanup_expired()
        stats = cache.get_stats()
        logger.info("%s cache stats: %s", name, stats)
