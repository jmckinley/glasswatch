"""
Rate limiting middleware for API endpoints.

Uses in-memory storage for development/testing.
For production, should be replaced with Redis-backed rate limiter.
"""
import time
from typing import Dict, Tuple
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter.
    
    Tracks requests per IP address within a time window.
    Thread-safe using locks.
    
    Note: This is NOT suitable for production with multiple workers.
    Use Redis-backed rate limiter (e.g., slowapi, fastapi-limiter) in production.
    """
    
    def __init__(self):
        self._requests: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._lock = Lock()
    
    def is_allowed(self, key: str, endpoint: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Identifier (usually IP address)
            endpoint: Endpoint path
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds
        
        with self._lock:
            # Get request times for this key/endpoint
            request_times = self._requests[key][endpoint]
            
            # Remove old requests outside the window
            request_times[:] = [t for t in request_times if t > window_start]
            
            # Check if limit exceeded
            if len(request_times) >= max_requests:
                # Calculate retry-after
                oldest_request = min(request_times)
                retry_after = int(oldest_request + window_seconds - now) + 1
                return False, retry_after
            
            # Add current request
            request_times.append(now)
            return True, 0
    
    def clear(self):
        """Clear all rate limit data."""
        with self._lock:
            self._requests.clear()


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for specific endpoints.
    
    Applies different rate limits based on endpoint path.
    """
    
    # Rate limit configuration: endpoint_prefix -> (max_requests, window_seconds)
    RATE_LIMITS = {
        "/api/v1/auth/login": (10, 60),  # 10 login attempts per minute
        "/api/v1/auth/callback": (20, 60),  # 20 callbacks per minute
        "/api/v1/auth/demo-login": (5, 60),  # 5 demo logins per minute
        "/api/v1/auth/api-key": (5, 300),  # 5 API key generations per 5 minutes
    }
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to configured endpoints."""
        path = request.url.path
        
        # Check if this endpoint has rate limiting
        rate_config = None
        for endpoint_prefix, config in self.RATE_LIMITS.items():
            if path.startswith(endpoint_prefix):
                rate_config = config
                break
        
        if rate_config:
            max_requests, window_seconds = rate_config
            
            # Use IP address as key
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            allowed, retry_after = rate_limiter.is_allowed(
                key=client_ip,
                endpoint=path,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
        
        # Continue processing
        response = await call_next(request)
        return response


def require_rate_limit(max_requests: int, window_seconds: int):
    """
    Dependency for applying rate limiting to specific endpoints.
    
    Usage:
        @router.post("/login")
        async def login(
            _rate_limit: None = Depends(require_rate_limit(10, 60))
        ):
            ...
    
    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
    """
    async def rate_limit_checker(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        
        allowed, retry_after = rate_limiter.is_allowed(
            key=client_ip,
            endpoint=endpoint,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
    
    return rate_limit_checker
