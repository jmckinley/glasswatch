# Performance Optimization Guide

Sprint 11: Launch Prep - Performance tuning implementation.

## Overview

This document describes the performance optimization infrastructure added to Glasswatch for production launch readiness.

## Components

### 1. Database Query Optimization (`backend/db/optimization.py`)

**Features:**
- Slow query logging (>100ms threshold)
- Automatic EXPLAIN ANALYZE for very slow queries (>200ms)
- N+1 query detection
- Query result caching decorator
- Query statistics tracking

**Usage:**

```python
from backend.db.optimization import track_queries, cache_query_result

# Track queries in a request
with track_queries() as stats:
    result = await db.execute(query)
    # Automatically detects N+1 patterns

# Cache query results
@cache_query_result(ttl_seconds=600, key_prefix="vulnerabilities")
async def get_vulnerabilities(tenant_id: str, severity: str):
    # Expensive query
    return results
```

**Monitoring:**
- Check application logs for slow query warnings
- Use `/performance` endpoint to see query statistics
- N+1 patterns are automatically logged

### 2. Connection Pooling (`backend/db/pool.py`)

**Configuration:**
- Pool size: 20 connections (configurable via `DATABASE_POOL_SIZE`)
- Max overflow: 10 (configurable via `DATABASE_MAX_OVERFLOW`)
- Pool timeout: 30 seconds
- Connection recycle: 3600 seconds (1 hour)
- LIFO pool strategy to reduce connection churn
- Pre-ping enabled for connection health checks

**Features:**
- Optimized pool configuration for production
- Connection lifecycle event logging
- Pool health checks
- Pool statistics and recommendations

**Monitoring:**

```bash
# Check pool health
curl http://localhost:8000/health | jq '.metrics.database_pool'

# Get detailed pool stats and recommendations
curl http://localhost:8000/performance | jq '.database_pool'
```

**Environment Variables:**

```bash
DATABASE_POOL_SIZE=20           # Number of persistent connections
DATABASE_MAX_OVERFLOW=10        # Additional connections allowed
DATABASE_POOL_TIMEOUT=30        # Seconds to wait for connection
DATABASE_POOL_RECYCLE=3600      # Seconds before recycling connection
```

### 3. Redis Caching (`backend/services/cache_service.py`)

**Features:**
- Redis-backed caching with graceful degradation
- Automatic cache key generation (tenant-aware)
- Cache hit/miss metrics
- TTL-based expiration
- Pattern-based invalidation
- Decorators for easy integration

**Configuration:**

```bash
REDIS_URL=redis://localhost:6379/0
```

**Usage:**

```python
from backend.services.cache_service import cached, cache_invalidate_on_write

# Cache read operations
@cached(entity_type="vulnerability", ttl=600)
async def get_vulnerabilities(tenant_id: str, severity: str):
    # This result will be cached for 10 minutes
    return await db.query(...)

# Invalidate cache on writes
@cache_invalidate_on_write(entity_type="vulnerability")
async def update_vulnerability(tenant_id: str, vuln_id: str, data: dict):
    # Cache will be invalidated after update
    return await db.update(...)
```

**Monitoring:**

```bash
# Check cache metrics
curl http://localhost:8000/performance | jq '.cache'

# Output:
# {
#   "available": true,
#   "hits": 1523,
#   "misses": 234,
#   "hit_rate_percent": 86.69
# }
```

**Graceful Degradation:**
If Redis is unavailable, caching is automatically disabled and the application continues functioning normally (cache misses are logged but don't cause errors).

### 4. Performance Middleware (`backend/middleware/performance.py`)

**Features:**
- Request timing (added as `X-Response-Time` header)
- Database query counting (added as `X-DB-Queries` header)
- Slow request logging (>500ms)
- Request size tracking and limiting
- Automatic N+1 detection per request

**Headers Added:**
- `X-Response-Time: 127.45ms` - Total request duration
- `X-DB-Queries: 12` - Number of database queries executed

**Configuration:**

```python
# In main.py
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestSizeMiddleware, max_request_size=10 * 1024 * 1024)  # 10MB
```

**Monitoring:**
Check application logs for slow request warnings and N+1 detection.

### 5. Database Indexes (`backend/alembic/versions/007_add_performance_indexes.py`)

**Indexes Added:**

**Vulnerabilities:**
- `(tenant_id, severity)` - Filter by severity per tenant
- `(tenant_id, kev_status)` - KEV vulnerability queries
- `(cve_id)` - CVE lookup
- `(tenant_id, created_at)` - Recent vulnerabilities

**Assets:**
- `(tenant_id, criticality)` - Filter by criticality
- `(tenant_id, internet_facing)` - Internet-facing assets
- `(tenant_id, asset_type)` - Filter by type

**PatchBundles & Bundles:**
- `(tenant_id, status)` - Filter by status
- `(created_at)` - Recent bundles
- `(tenant_id, created_at)` - Tenant timeline

**ApprovalRequests:**
- `(tenant_id, status)` - Pending approvals
- `(requester_id)` - My requests
- `(entity_type, entity_id)` - Entity lookups

**Comments & Activities:**
- `(entity_type, entity_id)` - Comments on entities
- `(tenant_id, created_at)` - Activity timeline
- `(author_id)` / `(user_id)` - User activity

**Apply Migration:**

```bash
# Apply performance indexes
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Verification:**

```sql
-- Check indexes
\di+ idx_vulnerabilities_*

-- Analyze index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### 6. Load Testing (`backend/tests/load/locustfile.py`)

**Features:**
- Realistic user simulation (90% normal users, 10% admin)
- Weighted task distribution
- Multiple test scenarios
- Performance target validation

**Running Tests:**

```bash
# Install Locust
pip install locust

# Run with web UI
locust -f backend/tests/load/locustfile.py --host http://localhost:8000

# Headless test (1000 users)
locust -f backend/tests/load/locustfile.py \
  --host http://localhost:8000 \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 5m \
  --headless
```

**Performance Targets:**
- 1000 concurrent users
- p95 response time < 500ms
- p99 response time < 1000ms
- Error rate < 1%

See `backend/tests/load/README.md` for detailed documentation.

## Monitoring Endpoints

### `/health` - Health Check

```bash
curl http://localhost:8000/health | jq
```

Returns:
- Overall health status
- Database pool health
- Redis availability
- Detailed metrics

### `/performance` - Performance Metrics

```bash
curl http://localhost:8000/performance | jq
```

Returns:
- Database pool statistics
- Pool recommendations
- Cache metrics (hit rate, etc.)
- Query statistics (N+1 detection)

## Configuration

### Environment Variables

```bash
# Database Connection Pool
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/glasswatch
DATABASE_POOL_SIZE=20           # Persistent connections
DATABASE_MAX_OVERFLOW=10        # Additional connections
DATABASE_POOL_TIMEOUT=30        # Connection wait timeout (seconds)
DATABASE_POOL_RECYCLE=3600      # Connection recycle time (seconds)

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Application
ENV=production
DEBUG=false
```

### Tuning Guidelines

**Small Deployments (< 100 concurrent users):**
```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5
```

**Medium Deployments (100-500 users):**
```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

**Large Deployments (> 500 users):**
```bash
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=25
```

**Rule of Thumb:**
`pool_size + max_overflow` should be less than PostgreSQL's `max_connections` setting (default: 100).

## Optimization Workflow

1. **Baseline Measurement**
   ```bash
   # Run load test
   locust -f backend/tests/load/locustfile.py --users 100 --run-time 2m
   
   # Check metrics
   curl http://localhost:8000/performance
   ```

2. **Identify Bottlenecks**
   - Check slow query logs
   - Review N+1 detection
   - Monitor pool utilization
   - Check cache hit rate

3. **Apply Optimizations**
   - Add database indexes
   - Enable caching for hot paths
   - Optimize queries (eager loading)
   - Adjust pool size

4. **Verify Improvements**
   - Re-run load tests
   - Compare metrics
   - Check response times

5. **Monitor Production**
   - Set up alerts for slow requests
   - Track cache hit rates
   - Monitor pool exhaustion
   - Review query patterns

## Common Performance Issues

### High Response Times

**Symptoms:**
- p95 > 500ms
- Slow request warnings in logs

**Solutions:**
1. Check for N+1 queries (use `joinedload()`)
2. Add database indexes for common queries
3. Enable caching for expensive operations
4. Review query complexity

### Pool Exhaustion

**Symptoms:**
- "QueuePool limit exceeded" errors
- High pool overflow count
- Timeout errors

**Solutions:**
1. Increase `DATABASE_POOL_SIZE`
2. Increase `DATABASE_MAX_OVERFLOW`
3. Check for connection leaks
4. Reduce connection hold time

### Low Cache Hit Rate

**Symptoms:**
- Cache hit rate < 70%
- High database load

**Solutions:**
1. Increase cache TTL for stable data
2. Review cache invalidation logic
3. Add caching to more endpoints
4. Check Redis connectivity

### N+1 Queries

**Symptoms:**
- High query count per request
- N+1 detection warnings

**Solutions:**
1. Use eager loading: `selectinload()` or `joinedload()`
2. Batch queries with `select()`
3. Use relationship loading strategies
4. Consider caching related entities

## Production Checklist

- [ ] Database indexes applied (`alembic upgrade head`)
- [ ] Redis configured and running
- [ ] Connection pool sized appropriately
- [ ] Performance middleware enabled
- [ ] Monitoring endpoints accessible
- [ ] Load testing completed with targets met
- [ ] Slow query alerts configured
- [ ] Cache monitoring in place
- [ ] Pool exhaustion alerts configured
- [ ] Documentation reviewed by team

## Performance Budget

**Target Metrics (p95):**
- Dashboard load: < 300ms
- Detail views: < 200ms
- List endpoints: < 400ms
- Write operations: < 500ms
- Search queries: < 600ms

**Database:**
- Query time: < 100ms (p95)
- Connection pool utilization: < 80%
- Cache hit rate: > 80%

**Application:**
- Requests/second: > 100 (at 1000 concurrent users)
- Error rate: < 0.1%
- Memory usage: < 2GB per worker

## Further Optimization

If performance targets are not met:

1. **Application-level caching** - Cache computed results (scoring, risk calculations)
2. **Query optimization** - Rewrite complex queries, use CTEs
3. **Read replicas** - Distribute read load across replicas
4. **CDN** - Cache static assets and API responses
5. **Database partitioning** - Partition large tables by tenant
6. **Async workers** - Move heavy operations to background jobs
7. **Materialized views** - Pre-compute dashboard statistics

## Resources

- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Locust Documentation](https://docs.locust.io/)
