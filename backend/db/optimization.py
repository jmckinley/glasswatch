"""
Database Query Optimization

Provides query analysis, slow query logging, N+1 detection, and caching.
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Configuration
SLOW_QUERY_THRESHOLD_MS = 100
EXPLAIN_ANALYZE_THRESHOLD_MS = 200
N_PLUS_ONE_THRESHOLD = 10


class QueryStats:
    """Track query statistics for N+1 detection."""
    
    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.query_count = 0
        self.start_time = None
        
    def reset(self):
        """Reset statistics."""
        self.queries = []
        self.query_count = 0
        self.start_time = time.time()
        
    def add_query(self, statement: str, duration_ms: float):
        """Add a query to statistics."""
        self.queries.append({
            "statement": statement,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        })
        self.query_count += 1
        
    def detect_n_plus_one(self) -> Optional[Dict[str, Any]]:
        """Detect potential N+1 query patterns."""
        if self.query_count < N_PLUS_ONE_THRESHOLD:
            return None
            
        # Group similar queries
        query_groups: Dict[str, int] = {}
        for query in self.queries:
            # Normalize query by removing specific IDs
            normalized = query["statement"][:100]  # Use first 100 chars as pattern
            query_groups[normalized] = query_groups.get(normalized, 0) + 1
            
        # Find repeated patterns
        for pattern, count in query_groups.items():
            if count >= N_PLUS_ONE_THRESHOLD:
                return {
                    "pattern": pattern,
                    "count": count,
                    "total_queries": self.query_count,
                    "warning": "Potential N+1 query detected"
                }
                
        return None


# Global query stats tracker
_query_stats = QueryStats()


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time."""
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries and track statistics."""
    if not hasattr(context, '_query_start_time'):
        return
        
    duration = time.time() - context._query_start_time
    duration_ms = duration * 1000
    
    # Track in statistics
    _query_stats.add_query(statement, duration_ms)
    
    # Log slow queries
    if duration_ms > SLOW_QUERY_THRESHOLD_MS:
        logger.warning(
            f"Slow query detected ({duration_ms:.2f}ms): {statement[:200]}"
        )
        
        # Run EXPLAIN ANALYZE for very slow queries
        if duration_ms > EXPLAIN_ANALYZE_THRESHOLD_MS:
            try:
                explain_result = conn.execute(f"EXPLAIN ANALYZE {statement}", parameters)
                logger.info(f"EXPLAIN ANALYZE:\n{explain_result.fetchall()}")
            except Exception as e:
                logger.debug(f"Could not run EXPLAIN ANALYZE: {e}")


@contextmanager
def track_queries():
    """
    Context manager to track queries and detect N+1 patterns.
    
    Usage:
        with track_queries() as stats:
            # Execute queries
            result = await db.execute(query)
        
        if stats.detect_n_plus_one():
            logger.warning("N+1 query pattern detected!")
    """
    _query_stats.reset()
    try:
        yield _query_stats
    finally:
        n_plus_one = _query_stats.detect_n_plus_one()
        if n_plus_one:
            logger.warning(
                f"N+1 Query Detected: {n_plus_one['count']} similar queries. "
                f"Pattern: {n_plus_one['pattern']}"
            )


def cache_query_result(ttl_seconds: int = 300, key_prefix: str = "query"):
    """
    Decorator to cache query results.
    
    Args:
        ttl_seconds: Time to live for cached result
        key_prefix: Prefix for cache key
        
    Usage:
        @cache_query_result(ttl_seconds=600, key_prefix="vulnerabilities")
        async def get_vulnerabilities(tenant_id: str, severity: str):
            # Query database
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Import here to avoid circular dependency
            from backend.services.cache_service import cache_service
            
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = await cache_service.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
                
            # Execute query
            logger.debug(f"Cache miss for {cache_key}, executing query")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_service.set(cache_key, result, ttl=ttl_seconds)
            
            return result
            
        return wrapper
    return decorator


class QueryOptimizer:
    """
    Query optimization utilities.
    """
    
    @staticmethod
    async def analyze_query(db: AsyncSession, statement: str) -> Dict[str, Any]:
        """
        Analyze a query using EXPLAIN.
        
        Args:
            db: Database session
            statement: SQL statement to analyze
            
        Returns:
            Query plan and analysis
        """
        try:
            result = await db.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}")
            plan = result.fetchone()[0]
            return {
                "query": statement,
                "plan": plan,
                "analyzed": True
            }
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {
                "query": statement,
                "error": str(e),
                "analyzed": False
            }
    
    @staticmethod
    def get_query_stats() -> Dict[str, Any]:
        """Get current query statistics."""
        n_plus_one = _query_stats.detect_n_plus_one()
        
        return {
            "total_queries": _query_stats.query_count,
            "queries": _query_stats.queries[-20:],  # Last 20 queries
            "n_plus_one_detected": n_plus_one is not None,
            "n_plus_one_details": n_plus_one,
            "elapsed_time": time.time() - _query_stats.start_time if _query_stats.start_time else 0
        }
    
    @staticmethod
    def reset_stats():
        """Reset query statistics."""
        _query_stats.reset()
