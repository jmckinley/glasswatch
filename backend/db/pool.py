"""
Database Connection Pool Configuration

Optimized connection pooling for PostgreSQL with health checks and monitoring.
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event, text

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Pool configuration
DEFAULT_POOL_SIZE = 20
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600  # 1 hour


def create_optimized_engine(
    database_url: str = None,
    pool_size: int = None,
    max_overflow: int = None,
    pool_timeout: int = None,
    pool_recycle: int = None,
    echo: bool = False
) -> AsyncEngine:
    """
    Create an optimized async database engine with connection pooling.
    
    Args:
        database_url: Database connection URL (defaults to settings.DATABASE_URL)
        pool_size: Number of connections to maintain (default: 20)
        max_overflow: Max connections beyond pool_size (default: 10)
        pool_timeout: Seconds to wait for connection (default: 30)
        pool_recycle: Seconds before recycling connection (default: 3600)
        echo: Enable SQL query logging
        
    Returns:
        Configured AsyncEngine
    """
    database_url = database_url or settings.DATABASE_URL
    pool_size = pool_size or getattr(settings, 'DATABASE_POOL_SIZE', DEFAULT_POOL_SIZE)
    max_overflow = max_overflow or getattr(settings, 'DATABASE_MAX_OVERFLOW', DEFAULT_MAX_OVERFLOW)
    pool_timeout = pool_timeout or getattr(settings, 'DATABASE_POOL_TIMEOUT', DEFAULT_POOL_TIMEOUT)
    pool_recycle = pool_recycle or getattr(settings, 'DATABASE_POOL_RECYCLE', DEFAULT_POOL_RECYCLE)
    
    # Determine pool class based on environment
    if settings.ENV == "test":
        # Use NullPool for testing to avoid connection issues
        poolclass = NullPool
        logger.info("Using NullPool for testing environment")
    else:
        poolclass = QueuePool
        logger.info(
            f"Configuring connection pool: "
            f"size={pool_size}, max_overflow={max_overflow}, "
            f"timeout={pool_timeout}s, recycle={pool_recycle}s"
        )
    
    engine = create_async_engine(
        database_url,
        echo=echo,
        future=True,
        poolclass=poolclass,
        pool_size=pool_size if poolclass == QueuePool else None,
        max_overflow=max_overflow if poolclass == QueuePool else None,
        pool_timeout=pool_timeout if poolclass == QueuePool else None,
        pool_recycle=pool_recycle if poolclass == QueuePool else None,
        pool_pre_ping=True,  # Verify connections before using
        pool_use_lifo=True,  # Use LIFO to reduce connection churn
    )
    
    # Add connection pool event listeners
    setup_pool_events(engine)
    
    return engine


def setup_pool_events(engine: AsyncEngine):
    """
    Set up event listeners for connection pool monitoring.
    
    Args:
        engine: SQLAlchemy AsyncEngine
    """
    
    @event.listens_for(engine.sync_engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new connections."""
        logger.debug(f"Database connection established: {id(dbapi_conn)}")
    
    @event.listens_for(engine.sync_engine, "close")
    def receive_close(dbapi_conn, connection_record):
        """Log closed connections."""
        logger.debug(f"Database connection closed: {id(dbapi_conn)}")
    
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout from pool."""
        logger.debug(f"Connection checked out from pool: {id(dbapi_conn)}")
    
    @event.listens_for(engine.sync_engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection checkin to pool."""
        logger.debug(f"Connection returned to pool: {id(dbapi_conn)}")


async def check_pool_health(engine: AsyncEngine) -> Dict[str, Any]:
    """
    Check connection pool health and return statistics.
    
    Args:
        engine: SQLAlchemy AsyncEngine
        
    Returns:
        Pool health statistics
    """
    try:
        pool = engine.pool
        
        # Get pool statistics
        stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
            "healthy": True
        }
        
        # Test a connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            stats["connection_test"] = "passed"
            
        return stats
        
    except Exception as e:
        logger.error(f"Pool health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e)
        }


async def get_pool_stats(engine: AsyncEngine) -> Dict[str, Any]:
    """
    Get detailed connection pool statistics.
    
    Args:
        engine: SQLAlchemy AsyncEngine
        
    Returns:
        Detailed pool statistics
    """
    try:
        pool = engine.pool
        
        return {
            "pool": {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "max_overflow": getattr(pool, '_max_overflow', None),
                "timeout": getattr(pool, '_timeout', None),
            },
            "connections": {
                "total": pool.size() + pool.overflow(),
                "available": pool.checkedin(),
                "in_use": pool.checkedout(),
                "waiting": pool.overflow(),
            },
            "configuration": {
                "pool_size": getattr(pool, '_pool_size', None),
                "max_overflow": getattr(pool, '_max_overflow', None),
                "timeout": getattr(pool, '_timeout', None),
                "recycle": getattr(pool, '_recycle', None),
            }
        }
    except Exception as e:
        logger.error(f"Failed to get pool stats: {e}")
        return {"error": str(e)}


def get_pool_recommendations(stats: Dict[str, Any]) -> list[str]:
    """
    Analyze pool statistics and provide optimization recommendations.
    
    Args:
        stats: Pool statistics from get_pool_stats()
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    if stats.get("error"):
        return ["Unable to analyze pool - check connection"]
    
    pool_info = stats.get("pool", {})
    connections = stats.get("connections", {})
    
    # Check for pool exhaustion
    if pool_info.get("overflow", 0) > 0:
        recommendations.append(
            f"⚠️  Pool overflow active ({pool_info['overflow']} connections). "
            "Consider increasing pool_size."
        )
    
    # Check for high utilization
    total = connections.get("total", 0)
    in_use = connections.get("in_use", 0)
    if total > 0 and (in_use / total) > 0.8:
        recommendations.append(
            f"⚠️  High pool utilization ({in_use}/{total} = {in_use/total:.1%}). "
            "Consider increasing pool size or max_overflow."
        )
    
    # Check for low utilization
    if total > 0 and (in_use / total) < 0.2:
        recommendations.append(
            f"ℹ️  Low pool utilization ({in_use}/{total} = {in_use/total:.1%}). "
            "Pool size may be larger than necessary."
        )
    
    if not recommendations:
        recommendations.append("✅ Pool configuration looks healthy")
    
    return recommendations
