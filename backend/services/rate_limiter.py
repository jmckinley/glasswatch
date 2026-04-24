"""
Redis-backed rate limiter using sliding window.

Implements rate limiting with Redis sorted sets for distributed systems.
Falls back to allowing all requests if Redis is unavailable.
"""
import os
import time
from typing import Tuple, Optional


class RateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets.
    
    Uses ZREMRANGEBYSCORE to remove old entries and ZCARD to count
    current window entries. Atomic operations ensure accuracy.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL (or use REDIS_URL env var)
        """
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self._client = None
        self._redis_available = False
        
        if self.redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis
                self._redis_available = True
            except ImportError:
                self._redis_available = False
    
    async def _get_client(self):
        """Get or create Redis client."""
        if not self._redis_available:
            return None
        
        if self._client is None:
            try:
                self._client = self._redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                # Test connection
                await self._client.ping()
            except Exception:
                self._client = None
                return None
        
        return self._client
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Uses sliding window algorithm:
        1. Remove entries older than window
        2. Count remaining entries
        3. If under limit, add current timestamp
        
        Args:
            key: Rate limit key (e.g., "api:user:123" or "api:ip:1.2.3.4")
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (allowed: bool, remaining: int)
            - allowed: True if request should be allowed
            - remaining: Number of requests remaining in window
        """
        client = await self._get_client()
        
        # Fallback: allow all requests if Redis unavailable
        if client is None:
            return True, limit
        
        try:
            now = time.time()
            window_start = now - window_seconds
            
            # Prefix key to namespace rate limits
            redis_key = f"ratelimit:{key}"
            
            # Use pipeline for atomic operations
            pipe = client.pipeline()
            
            # 1. Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # 2. Count current entries in window
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Result from ZCARD
            
            # Check if limit exceeded
            if current_count >= limit:
                remaining = 0
                allowed = False
            else:
                # 3. Add current request timestamp
                await client.zadd(redis_key, {str(now): now})
                
                # 4. Set expiration on the key (cleanup)
                await client.expire(redis_key, window_seconds + 60)
                
                remaining = limit - current_count - 1
                allowed = True
            
            return allowed, remaining
        
        except Exception:
            # On any error, fail open (allow request)
            # Log error in production
            return True, limit
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    
    return _rate_limiter
