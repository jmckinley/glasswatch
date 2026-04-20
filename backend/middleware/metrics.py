"""
Metrics middleware for automatic request tracking.

Instruments all HTTP requests with Prometheus metrics.
"""
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.services.metrics_service import get_metrics_service


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically tracks metrics for all HTTP requests.
    
    Tracks:
    - Request count by method, endpoint, status, and tenant
    - Request duration histogram
    - Active requests gauge
    - Error counts
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
    ):
        """
        Initialize metrics middleware.
        
        Args:
            app: ASGI application
            exclude_paths: List of paths to exclude from metrics (e.g., /health)
        """
        super().__init__(app)
        self.metrics = get_metrics_service()
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track metrics for the request."""
        # Skip metrics for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract request info
        method = request.method
        endpoint = self._normalize_endpoint(request.url.path)
        tenant_id = self._extract_tenant_id(request)
        
        # Track active requests
        self.metrics.http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint,
        ).inc()
        
        # Time the request
        start_time = time.perf_counter()
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Track metrics
            duration = time.perf_counter() - start_time
            self.metrics.track_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
                tenant_id=tenant_id,
            )
            
            # Track errors (4xx and 5xx)
            if status_code >= 400:
                error_type = self._classify_error(status_code)
                self.metrics.track_error(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type,
                    status_code=status_code,
                )
            
            return response
        
        except Exception as exc:
            # Track exception
            duration = time.perf_counter() - start_time
            self.metrics.track_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration,
                tenant_id=tenant_id,
            )
            self.metrics.track_error(
                method=method,
                endpoint=endpoint,
                error_type=type(exc).__name__,
                status_code=500,
            )
            raise
        
        finally:
            # Decrement active requests
            self.metrics.http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint,
            ).dec()
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for metrics.
        
        Replaces UUIDs and IDs with placeholders to avoid high cardinality.
        
        Example:
            /api/v1/bundles/123e4567-e89b-12d3-a456-426614174000 -> /api/v1/bundles/{id}
        """
        parts = path.split('/')
        normalized = []
        
        for part in parts:
            # Check if part looks like a UUID
            if len(part) == 36 and part.count('-') == 4:
                normalized.append('{id}')
            # Check if part looks like an integer ID
            elif part.isdigit():
                normalized.append('{id}')
            else:
                normalized.append(part)
        
        return '/'.join(normalized)
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        Extract tenant ID from request.
        
        Checks in order:
        1. Request state (set by auth middleware)
        2. Headers (X-Tenant-ID)
        3. Query parameters
        
        Returns:
            Tenant ID or None
        """
        # Check request state (set by auth middleware)
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id
        
        # Check headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Check query parameters
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        return None
    
    def _classify_error(self, status_code: int) -> str:
        """
        Classify error by status code.
        
        Args:
            status_code: HTTP status code
        
        Returns:
            Error classification (client_error, server_error, etc.)
        """
        if status_code == 400:
            return "bad_request"
        elif status_code == 401:
            return "unauthorized"
        elif status_code == 403:
            return "forbidden"
        elif status_code == 404:
            return "not_found"
        elif status_code == 422:
            return "validation_error"
        elif status_code == 429:
            return "rate_limit"
        elif 400 <= status_code < 500:
            return "client_error"
        elif status_code == 500:
            return "internal_error"
        elif status_code == 502:
            return "bad_gateway"
        elif status_code == 503:
            return "service_unavailable"
        elif status_code == 504:
            return "gateway_timeout"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"
