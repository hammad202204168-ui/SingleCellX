"""
Caching utilities for analysis results and preprocessed data.

Implements in-memory caching with TTL to avoid recomputation of expensive
operations like PCA, UMAP, and clustering when parameters haven't changed.
"""
import json
import hashlib
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import threading


class CacheEntry:
    """A single cached item with TTL support."""
    
    def __init__(self, value: Any, ttl_seconds: int = 3600):
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds
    
    def __repr__(self) -> str:
        return f"CacheEntry(expired={self.is_expired()}, age={self.age_seconds():.1f}s)"
    
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()


class AnalysisCache:
    """Thread-safe cache for analysis pipeline results."""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, prefix: str, **params) -> str:
        """Generate a cache key from prefix and parameters."""
        # Sort params for deterministic keys
        param_str = json.dumps(params, sort_keys=True, default=str)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
    
    def get(self, prefix: str, **params) -> Optional[Any]:
        """Retrieve a cached value if it exists and hasn't expired."""
        key = self._make_key(prefix, **params)
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    self.hits += 1
                    return entry.value
                else:
                    del self._cache[key]
            self.misses += 1
            return None
    
    def set(self, prefix: str, value: Any, ttl: Optional[int] = None, **params):
        """Cache a value with optional TTL override."""
        key = self._make_key(prefix, **params)
        ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
    
    def clear(self, prefix: Optional[str] = None):
        """Clear all cache entries or those matching a prefix."""
        with self._lock:
            if prefix is None:
                self._cache.clear()
                self.hits = 0
                self.misses = 0
            else:
                keys_to_delete = [k for k in self._cache if k.startswith(f"{prefix}:")]
                for k in keys_to_delete:
                    del self._cache[k]
    
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        with self._lock:
            expired = sum(1 for e in self._cache.values() if e.is_expired())
            return {
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": total,
                "hit_rate_pct": round(hit_rate, 2),
                "cached_items": len(self._cache),
                "expired_items": expired,
            }
    
    def cleanup(self):
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for k in expired_keys:
                del self._cache[k]
            return len(expired_keys)


# Global cache instance
_cache = AnalysisCache(default_ttl=3600)  # 1 hour default


def get_cache() -> AnalysisCache:
    """Get the global cache instance."""
    return _cache


def cached_computation(prefix: str, ttl: Optional[int] = None):
    """Decorator for caching function results.
    
    Usage:
        @cached_computation("pca", ttl=1800)
        def run_pca(data, n_components):
            ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cache = get_cache()
            cached_result = cache.get(prefix, args=args, kwargs=kwargs)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(prefix, result, ttl=ttl, args=args, kwargs=kwargs)
            return result
        return wrapper
    return decorator
