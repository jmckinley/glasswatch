"""
Redis Caching Service

Provides Redis-backed caching with graceful fallback and metrics.
"""
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps

import redis.asyncio as redis
from redis.exceptions import RedisError

from backend.core.config import settings

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Track cache hit/miss metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.sets = 0
        self.deletes = 0
        
    def record_hit(self):
        """Record cache hit."""
        self.hits += 1
        
    def record_miss(self):
        """Record cache miss."""
        self.misses += 1
        
    def record_error(self):
        """Record cache error."""
        self.errors += 1
        
    def record_set(self):
        """Record cache set."""
        self.sets += 1
        
    def record_delete(self):
        """Record cache delete."""
        self.deletes += 1
        
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "sets": self.sets,
            "deletes": self.deletes,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def reset(self):
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.sets = 0
        self.deletes = 0


class CacheService:
    """
    Redis-backed caching service with graceful degradation.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize cache service.
        
        Args:
            redis_url: Redis connection URL (defaults to settings.REDIS_URL)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._available = False
        self.metrics = CacheMetrics()
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self._client.ping()
            self._available = True
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except Exception as e:
            self._available = False
            logger.warning(f"⚠️  Redis unavailable: {e}. Caching disabled.")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._available = False
            logger.info("Redis disconnected")
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available
    
    def _make_key(self, entity_type: str, entity_id: str, tenant_id: str = None) -> str:
        """
        Generate cache key.
        
        Args:
            entity_type: Type of entity (e.g., "vulnerability", "asset")
            entity_id: Entity identifier
            tenant_id: Optional tenant ID for multi-tenancy
            
        Returns:
            Cache key string
        """
        if tenant_id:
            return f"glasswatch:{tenant_id}:{entity_type}:{entity_id}"
        return f"glasswatch:{entity_type}:{entity_id}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self._available:
            self.metrics.record_miss()
            return None
            
        try:
            value = await self._client.get(key)
            if value is None:
                self.metrics.record_miss()
                return None
                
            self.metrics.record_hit()
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            self.metrics.record_error()
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 300)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            return False
            
        try:
            # Serialize value as JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
                
            await self._client.set(key, value, ex=ttl)
            self.metrics.record_set()
            return True
            
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            self.metrics.record_error()
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            return False
            
        try:
            await self._client.delete(key)
            self.metrics.record_delete()
            return True
            
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            self.metrics.record_error()
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "glasswatch:tenant123:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._available:
            return 0
            
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
                
            if keys:
                deleted = await self._client.delete(*keys)
                self.metrics.record_delete()
                return deleted
            return 0
            
        except RedisError as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
            self.metrics.record_error()
            return 0
    
    async def invalidate_entity(self, entity_type: str, tenant_id: str = None):
        """
        Invalidate all cached entries for an entity type.
        
        Args:
            entity_type: Type of entity (e.g., "vulnerability")
            tenant_id: Optional tenant ID
        """
        pattern = self._make_key(entity_type, "*", tenant_id)
        deleted = await self.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cache entries for {entity_type}")
    
    def get_metrics(self) -> dict:
        """Get cache metrics."""
        return {
            "available": self._available,
            "redis_url": self.redis_url.split("@")[-1] if "@" in self.redis_url else self.redis_url,
            **self.metrics.get_stats()
        }
    
    def reset_metrics(self):
        """Reset cache metrics."""
        self.metrics.reset()


# Global cache service instance
cache_service = CacheService()


def cached(
    entity_type: str,
    ttl: int = 300,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching service method results.
    
    Args:
        entity_type: Type of entity being cached
        ttl: Time to live in seconds
        key_builder: Optional function to build custom cache key
        
    Usage:
        @cached(entity_type="vulnerability", ttl=600)
        async def get_vulnerabilities(tenant_id: str, severity: str):
            # Query database
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key: entity_type:function_name:args:kwargs
                tenant_id = kwargs.get('tenant_id') or (args[0] if args else None)
                cache_key = cache_service._make_key(
                    entity_type,
                    f"{func.__name__}:{hash(str(args[1:]) + str(kwargs))}",
                    tenant_id
                )
            
            # Try cache first
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate_on_write(entity_type: str):
    """
    Decorator to invalidate cache on write operations.
    
    Args:
        entity_type: Type of entity being modified
        
    Usage:
        @cache_invalidate_on_write(entity_type="vulnerability")
        async def update_vulnerability(tenant_id: str, vuln_id: str, data: dict):
            # Update database
            return updated_vuln
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)
            
            # Invalidate cache
            tenant_id = kwargs.get('tenant_id') or (args[0] if args else None)
            await cache_service.invalidate_entity(entity_type, tenant_id)
            logger.debug(f"Cache invalidated for {entity_type}, tenant: {tenant_id}")
            
            return result
        
        return wrapper
    return decorator
