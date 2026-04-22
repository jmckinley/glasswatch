"""
Health check endpoints for monitoring and load balancers.

Provides multiple levels of health checks:
- /health - Simple alive check
- /health/ready - Readiness check (dependencies ready)
- /health/detailed - Comprehensive system status
"""
import time
import psutil
import shutil
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db, engine
from backend.core.config import settings


router = APIRouter()

# Track startup time
_startup_time = time.time()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Simple health check for load balancers.
    
    Returns 200 if the service is alive.
    This endpoint is very lightweight and should always respond quickly.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check - verify service can handle requests.
    
    Checks:
    - Database connection
    - Database query execution
    
    Returns 200 if ready, 503 if not ready.
    """
    status = "ready"
    checks = {}
    
    # Check database connection
    try:
        # Simple query to verify DB is responsive
        result = await db.execute(text("SELECT 1"))
        db_connected = result.scalar() == 1
        checks["database"] = "ok" if db_connected else "failed"
        
        if not db_connected:
            status = "not_ready"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        status = "not_ready"
    
    # Check database migrations (optional - checks if tables exist)
    try:
        # Try to query a core table
        result = await db.execute(text("SELECT COUNT(*) FROM tenants"))
        checks["database_schema"] = "ok"
    except Exception as e:
        checks["database_schema"] = f"error: {str(e)}"
        # Don't mark as not_ready - might be first startup
    
    if status != "ready":
        raise HTTPException(status_code=503, detail={"status": status, "checks": checks})
    
    return {
        "status": status,
        "checks": checks,
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with comprehensive system status.
    
    Returns detailed information about:
    - Database connection and pool
    - System resources (CPU, memory, disk)
    - Uptime
    - Active connections
    - Recent activity metrics
    
    This endpoint is more expensive and should be called less frequently.
    """
    checks = {}
    
    # Database health
    db_health = await _check_database_health(db)
    checks["database"] = db_health
    
    # Redis health (if configured)
    # redis_health = await _check_redis_health()
    # checks["redis"] = redis_health
    
    # System resources
    system_health = _check_system_resources()
    checks["system"] = system_health
    
    # Uptime
    uptime_seconds = time.time() - _startup_time
    checks["uptime"] = {
        "seconds": int(uptime_seconds),
        "human_readable": _format_uptime(uptime_seconds),
        "started_at": datetime.fromtimestamp(_startup_time).isoformat(),
    }
    
    # Overall status
    overall_status = "healthy"
    
    # Check for critical issues
    if db_health.get("status") != "ok":
        overall_status = "degraded"
    
    if system_health["disk"]["usage_percent"] > 90:
        overall_status = "degraded"
    
    if system_health["memory"]["usage_percent"] > 90:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _check_database_health(db: AsyncSession) -> Dict[str, Any]:
    """
    Check database health and connection pool.
    
    Returns:
        Database health metrics
    """
    health = {}
    
    try:
        # Test query with timing
        start = time.perf_counter()
        result = await db.execute(text("SELECT 1"))
        query_time = time.perf_counter() - start
        
        health["status"] = "ok" if result.scalar() == 1 else "failed"
        health["query_time_ms"] = round(query_time * 1000, 2)
        
        # Connection pool status
        pool = engine.pool
        health["connection_pool"] = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
        }
        
        # Calculate pool utilization
        total_connections = pool.size() + pool.overflow()
        if total_connections > 0:
            utilization = (pool.checkedout() / total_connections) * 100
            health["connection_pool"]["utilization_percent"] = round(utilization, 2)
        
        # Check for recent activity (example - count tenants)
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM tenants"))
            tenant_count = result.scalar()
            health["tenant_count"] = tenant_count
        except Exception:
            pass  # Table might not exist yet
        
    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)
    
    return health


async def _check_redis_health() -> Dict[str, Any]:
    """
    Check Redis health (if configured).
    
    Returns:
        Redis health metrics
    """
    health = {}
    
    # TODO: Implement when Redis is integrated
    # try:
    #     redis_client = get_redis_client()
    #     await redis_client.ping()
    #     health["status"] = "ok"
    # except Exception as e:
    #     health["status"] = "error"
    #     health["error"] = str(e)
    
    health["status"] = "not_configured"
    
    return health


def _check_system_resources() -> Dict[str, Any]:
    """
    Check system resource usage.
    
    Returns:
        System resource metrics
    """
    resources = {}
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    resources["cpu"] = {
        "usage_percent": cpu_percent,
        "count": psutil.cpu_count(),
    }
    
    # Memory usage
    memory = psutil.virtual_memory()
    resources["memory"] = {
        "total_mb": round(memory.total / 1024 / 1024, 2),
        "available_mb": round(memory.available / 1024 / 1024, 2),
        "used_mb": round(memory.used / 1024 / 1024, 2),
        "usage_percent": memory.percent,
    }
    
    # Disk usage
    disk = shutil.disk_usage("/")
    resources["disk"] = {
        "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
        "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
        "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
        "usage_percent": round((disk.used / disk.total) * 100, 2),
    }
    
    # Network connections (current process)
    try:
        process = psutil.Process()
        connections = process.connections()
        resources["connections"] = {
            "total": len(connections),
            "established": len([c for c in connections if c.status == "ESTABLISHED"]),
        }
    except Exception:
        resources["connections"] = {"error": "Unable to get connection info"}
    
    return resources


def _format_uptime(seconds: float) -> str:
    """
    Format uptime in human-readable format.
    
    Args:
        seconds: Uptime in seconds
    
    Returns:
        Human-readable uptime string
    """
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)
