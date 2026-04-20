"""
Prometheus-compatible metrics service for Glasswatch.

Tracks application performance, business metrics, and system health.
"""
import time
from typing import Dict, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)


class MetricsService:
    """
    Centralized metrics collection service.
    
    Provides Prometheus-compatible metrics for:
    - HTTP request tracking
    - Database performance
    - Cache efficiency
    - Business metrics (vulnerabilities, bundles, etc.)
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics collectors."""
        self.registry = registry or CollectorRegistry()
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'tenant_id'],
            registry=self.registry,
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency in seconds',
            ['method', 'endpoint', 'status_code'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Number of HTTP requests currently being processed',
            ['method', 'endpoint'],
            registry=self.registry,
        )
        
        self.http_errors_total = Counter(
            'http_errors_total',
            'Total HTTP errors',
            ['method', 'endpoint', 'error_type', 'status_code'],
            registry=self.registry,
        )
        
        # Database Metrics
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
            registry=self.registry,
        )
        
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Number of active database connections',
            registry=self.registry,
        )
        
        self.db_connections_total = Gauge(
            'db_connections_total',
            'Total database connection pool size',
            registry=self.registry,
        )
        
        self.db_errors_total = Counter(
            'db_errors_total',
            'Total database errors',
            ['operation', 'error_type'],
            registry=self.registry,
        )
        
        # Cache Metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_name', 'operation'],
            registry=self.registry,
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_name', 'operation'],
            registry=self.registry,
        )
        
        self.cache_errors_total = Counter(
            'cache_errors_total',
            'Total cache errors',
            ['cache_name', 'error_type'],
            registry=self.registry,
        )
        
        # Business Metrics
        self.vulnerabilities_scanned_total = Counter(
            'vulnerabilities_scanned_total',
            'Total vulnerabilities scanned',
            ['tenant_id', 'severity', 'source'],
            registry=self.registry,
        )
        
        self.bundles_created_total = Counter(
            'bundles_created_total',
            'Total patch bundles created',
            ['tenant_id', 'bundle_type'],
            registry=self.registry,
        )
        
        self.approvals_processed_total = Counter(
            'approvals_processed_total',
            'Total approvals processed',
            ['tenant_id', 'decision', 'approver_role'],
            registry=self.registry,
        )
        
        self.snapshots_created_total = Counter(
            'snapshots_created_total',
            'Total snapshots created',
            ['tenant_id', 'snapshot_type'],
            registry=self.registry,
        )
        
        self.discovery_runs_total = Counter(
            'discovery_runs_total',
            'Total discovery runs completed',
            ['tenant_id', 'source', 'status'],
            registry=self.registry,
        )
        
        self.patch_weather_queries_total = Counter(
            'patch_weather_queries_total',
            'Total patch weather queries',
            ['tenant_id', 'cache_hit'],
            registry=self.registry,
        )
        
        # System Health Metrics
        self.system_info = Gauge(
            'system_info',
            'System information',
            ['version', 'environment'],
            registry=self.registry,
        )
    
    def track_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        tenant_id: Optional[str] = None,
    ):
        """
        Track an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status_code: HTTP status code
            duration: Request duration in seconds
            tenant_id: Optional tenant identifier
        """
        tenant = tenant_id or "unknown"
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            tenant_id=tenant,
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).observe(duration)
    
    def track_error(
        self,
        method: str,
        endpoint: str,
        error_type: str,
        status_code: int,
    ):
        """Track an HTTP error."""
        self.http_errors_total.labels(
            method=method,
            endpoint=endpoint,
            error_type=error_type,
            status_code=status_code,
        ).inc()
    
    def track_db_query(self, operation: str, table: str, duration: float):
        """Track a database query."""
        self.db_query_duration_seconds.labels(
            operation=operation,
            table=table,
        ).observe(duration)
    
    def track_db_error(self, operation: str, error_type: str):
        """Track a database error."""
        self.db_errors_total.labels(
            operation=operation,
            error_type=error_type,
        ).inc()
    
    def update_db_connections(self, active: int, total: int):
        """Update database connection metrics."""
        self.db_connections_active.set(active)
        self.db_connections_total.set(total)
    
    def track_cache_hit(self, cache_name: str, operation: str = "get"):
        """Track a cache hit."""
        self.cache_hits_total.labels(
            cache_name=cache_name,
            operation=operation,
        ).inc()
    
    def track_cache_miss(self, cache_name: str, operation: str = "get"):
        """Track a cache miss."""
        self.cache_misses_total.labels(
            cache_name=cache_name,
            operation=operation,
        ).inc()
    
    def track_cache_error(self, cache_name: str, error_type: str):
        """Track a cache error."""
        self.cache_errors_total.labels(
            cache_name=cache_name,
            error_type=error_type,
        ).inc()
    
    def track_vulnerability_scan(
        self,
        tenant_id: str,
        severity: str,
        source: str = "nvd",
    ):
        """Track a vulnerability scan."""
        self.vulnerabilities_scanned_total.labels(
            tenant_id=tenant_id,
            severity=severity,
            source=source,
        ).inc()
    
    def track_bundle_creation(self, tenant_id: str, bundle_type: str = "standard"):
        """Track bundle creation."""
        self.bundles_created_total.labels(
            tenant_id=tenant_id,
            bundle_type=bundle_type,
        ).inc()
    
    def track_approval(self, tenant_id: str, decision: str, approver_role: str):
        """Track an approval decision."""
        self.approvals_processed_total.labels(
            tenant_id=tenant_id,
            decision=decision,
            approver_role=approver_role,
        ).inc()
    
    def track_snapshot(self, tenant_id: str, snapshot_type: str = "manual"):
        """Track snapshot creation."""
        self.snapshots_created_total.labels(
            tenant_id=tenant_id,
            snapshot_type=snapshot_type,
        ).inc()
    
    def track_discovery_run(self, tenant_id: str, source: str, status: str):
        """Track a discovery run."""
        self.discovery_runs_total.labels(
            tenant_id=tenant_id,
            source=source,
            status=status,
        ).inc()
    
    def track_patch_weather_query(self, tenant_id: str, cache_hit: bool):
        """Track a patch weather query."""
        self.patch_weather_queries_total.labels(
            tenant_id=tenant_id,
            cache_hit=str(cache_hit).lower(),
        ).inc()
    
    def set_system_info(self, version: str, environment: str):
        """Set system information metric."""
        self.system_info.labels(
            version=version,
            environment=environment,
        ).set(1)
    
    def generate_metrics(self) -> bytes:
        """
        Generate Prometheus metrics in text format.
        
        Returns:
            Prometheus metrics in text exposition format
        """
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get the global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def reset_metrics():
    """Reset metrics (useful for testing)."""
    global _metrics_service
    _metrics_service = MetricsService()
