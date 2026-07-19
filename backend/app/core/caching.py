"""
Caching Layer for MotherCare AI

Implements:
- In-memory caching with TTL
- Query result caching
- RAG embedding caching
- Cache invalidation strategies
"""

import time
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached value with TTL."""
    
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return (time.time() - self.created_at) > self.ttl
    
    def get(self) -> Optional[Any]:
        """Get value if not expired."""
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
        """Get value from cache."""
        with self._lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if entry.is_expired():
                del self.cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL."""
        with self._lock:
            # Evict oldest entry if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k].created_at)
                del self.cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")
            
            self.cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str):
        """Delete entry from cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self.cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [
                k for k, v in self.cache.items() 
                if v.is_expired()
            ]
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            self.cleanup_expired()
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "usage_percent": (len(self.cache) / self.max_size) * 100
            }


# Global cache instances
query_cache = SimpleCache(max_size=500)  # For SQL queries
rag_cache = SimpleCache(max_size=1000)   # For RAG embeddings
twin_cache = SimpleCache(max_size=2000)  # For digital twin data
api_cache = SimpleCache(max_size=300)    # For external API responses


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    return "|".join(key_parts)


def cached(cache_instance: SimpleCache, ttl: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        cache_instance: Cache to use
        ttl: Time to live in seconds
    
    Usage:
        @cached(query_cache, ttl=600)
        def get_user(user_id):
            return db.query(User).get(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_value = cache_instance.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(key, result, ttl)
            logger.debug(f"Cache miss: {key}")
            
            return result
        
        return wrapper
    
    return decorator


def cache_clear(*cache_instances):
    """
    Decorator to clear cache after function execution.
    
    Usage:
        @cache_clear(query_cache, twin_cache)
        def update_user(user_id, data):
            db.update(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            for cache_instance in cache_instances:
                cache_instance.clear()
                logger.debug(f"Cleared cache after {func.__name__}")
            
            return result
        
        return wrapper
    
    return decorator


class QueryOptimizer:
    """Optimize SQLAlchemy queries with eager loading and indexing hints."""
    
    @staticmethod
    def optimize_user_query(query):
        """Optimize user query with eager loading."""
        return query.options(
            # Lazy load related health records
        )
    
    @staticmethod
    def optimize_twin_query(query):
        """Optimize digital twin query."""
        return query.options(
            # Include biomarkers and risk scores
        )
    
    @staticmethod
    def optimize_record_query(query):
        """Optimize health record query."""
        return query.options(
            # Eager load user and metadata
        )


def batch_cache_get(cache_instance: SimpleCache, keys: list) -> Dict[str, Any]:
    """Get multiple values from cache in batch."""
    results = {}
    for key in keys:
        value = cache_instance.get(key)
        if value is not None:
            results[key] = value
    return results


def batch_cache_set(cache_instance: SimpleCache, data: Dict[str, Any], ttl: int = 300):
    """Set multiple values in cache in batch."""
    for key, value in data.items():
        cache_instance.set(key, value, ttl)


# Background cache maintenance
def cache_maintenance_task():
    """
    Periodic task to maintain cache health.
    Run this in a background thread or scheduler (APScheduler, Celery, etc.)
    """
    logger.info("Running cache maintenance...")
    
    for cache_name, cache_instance in [
        ("query_cache", query_cache),
        ("rag_cache", rag_cache),
        ("twin_cache", twin_cache),
        ("api_cache", api_cache),
    ]:
        cache_instance.cleanup_expired()
        stats = cache_instance.get_stats()
        logger.info(f"{cache_name} stats: {stats}")


# Example usage in endpoints:
"""
from app.core.caching import cached, query_cache, twin_cache

@app.get("/ai/twin")
@cached(twin_cache, ttl=300)
async def get_twin(user_id: str, db: Session = Depends(get_db)):
    # This result will be cached for 5 minutes
    return db.query(DigitalTwin).filter_by(user_id=user_id).first()

@app.put("/ai/twin")
@cache_clear(twin_cache)  # Clear cache when twin is updated
async def update_twin(user_id: str, data: dict, db: Session = Depends(get_db)):
    # Update logic here
    pass
"""
