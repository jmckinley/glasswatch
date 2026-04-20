"""
Performance Monitoring Middleware

Tracks request timing, database queries, and request sizes.
"""
import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.db.optimization import QueryOptimizer

logger = logging.getLogger(__name__)

# Configuration
SLOW_REQUEST_THRESHOLD_MS = 500


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request performance metrics.
    
    Adds headers:
    - X-Response-Time: Request duration in milliseconds
    - X-DB-Queries: Number of database queries executed
    
    Logs slow requests (>500ms by default).
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add performance headers.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with performance headers
        """
        # Reset query stats for this request
        QueryOptimizer.reset_stats()
        
        # Record start time
        start_time = time.time()
        
        # Get request size
        request_size = 0
        if request.headers.get("content-length"):
            request_size = int(request.headers["content-length"])
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # Get query statistics
        query_stats = QueryOptimizer.get_query_stats()
        query_count = query_stats["total_queries"]
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        response.headers["X-DB-Queries"] = str(query_count)
        
        # Log slow requests
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"({duration_ms:.2f}ms, {query_count} queries)"
            )
            
            # Log N+1 detection
            if query_stats["n_plus_one_detected"]:
                logger.warning(
                    f"N+1 query detected in {request.method} {request.url.path}: "
                    f"{query_stats['n_plus_one_details']}"
                )
        
        # Log request metrics (debug level)
        logger.debug(
            f"{request.method} {request.url.path} - "
            f"{duration_ms:.2f}ms, {query_count} queries, "
            f"request: {request_size}b, response: {response.headers.get('content-length', 0)}b"
        )
        
        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and limit request sizes.
    
    Logs large requests and can enforce size limits.
    """
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            max_request_size: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check request size and process request.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or error if request too large
        """
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            
            # Log large requests
            if size > 1024 * 1024:  # > 1MB
                logger.info(
                    f"Large request: {request.method} {request.url.path} "
                    f"({size / 1024 / 1024:.2f}MB)"
                )
            
            # Enforce size limit
            if size > self.max_request_size:
                logger.warning(
                    f"Request too large: {request.method} {request.url.path} "
                    f"({size / 1024 / 1024:.2f}MB > {self.max_request_size / 1024 / 1024:.2f}MB)"
                )
                return Response(
                    content=f"Request entity too large (max: {self.max_request_size / 1024 / 1024:.0f}MB)",
                    status_code=413
                )
        
        return await call_next(request)


def get_performance_summary() -> dict:
    """
    Get performance summary for current request context.
    
    Returns:
        Performance metrics
    """
    query_stats = QueryOptimizer.get_query_stats()
    
    return {
        "database": {
            "queries": query_stats["total_queries"],
            "n_plus_one_detected": query_stats["n_plus_one_detected"],
            "slow_queries": len([
                q for q in query_stats["queries"]
                if q["duration_ms"] > 100
            ])
        }
    }
