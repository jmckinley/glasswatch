# Load Testing for Glasswatch

This directory contains Locust-based load testing configurations for the Glasswatch API.

## Prerequisites

```bash
pip install locust
```

## Running Load Tests

### Basic Load Test

```bash
# Start Locust web UI
locust -f backend/tests/load/locustfile.py --host http://localhost:8000

# Open browser to http://localhost:8089
# Configure:
#   - Number of users: 100
#   - Spawn rate: 10 users/second
```

### Headless Load Test

```bash
# Run without web UI
locust -f backend/tests/load/locustfile.py \
  --host http://localhost:8000 \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 5m \
  --headless
```

### Distributed Load Test

```bash
# Start master
locust -f backend/tests/load/locustfile.py \
  --host http://localhost:8000 \
  --master

# Start workers (on same or different machines)
locust -f backend/tests/load/locustfile.py \
  --worker \
  --master-host localhost
```

## Performance Targets

- **Concurrent Users:** 1000
- **p95 Response Time:** < 500ms
- **p99 Response Time:** < 1000ms
- **Error Rate:** < 1%

## Test Scenarios

### GlasswatchUser (90% of traffic)
Simulates normal users performing common operations:

- **Dashboard (weight: 5)** - View vulnerabilities list
- **Assets (weight: 4)** - View assets list  
- **Details (weight: 3)** - View vulnerability details
- **Stats (weight: 3)** - View dashboard statistics
- **Filters (weight: 2)** - Filter by severity
- **Bundles (weight: 2)** - View patch bundles
- **Write Ops (weight: 1)** - Create vulnerabilities, trigger scans
- **Approvals (weight: 1)** - Submit approval requests

### AdminUser (10% of traffic)
Simulates admin users performing expensive operations:

- Report generation
- Bulk operations
- System configuration

## Monitoring During Load Tests

### Application Performance

```bash
# Watch performance endpoint
watch -n 1 'curl -s http://localhost:8000/performance | jq'
```

### Database Pool

```bash
# Monitor pool stats
curl http://localhost:8000/performance | jq '.database_pool'
```

### Cache Metrics

```bash
# Monitor cache hit rate
curl http://localhost:8000/performance | jq '.cache'
```

### Query Performance

```bash
# Check for slow queries and N+1 issues
curl http://localhost:8000/performance | jq '.queries'
```

## Analyzing Results

### Locust Stats

- **RPS (Requests/second)** - Throughput
- **Response Time (ms)** - Latency distribution
- **Failures** - Error rate
- **Users** - Concurrent load

### Performance Headers

All responses include:
- `X-Response-Time` - Request duration
- `X-DB-Queries` - Number of database queries

### Slow Request Logs

Check application logs for:
- Slow requests (>500ms)
- N+1 query detection
- Cache misses

## Optimization Workflow

1. **Baseline** - Run load test, record metrics
2. **Identify** - Find slow endpoints, N+1 queries
3. **Optimize** - Add indexes, caching, query optimization
4. **Verify** - Re-run load test, compare metrics
5. **Repeat** - Continue until targets met

## Common Issues

### High Response Times
- Check database pool exhaustion
- Look for N+1 queries
- Review slow query logs
- Verify cache hit rate

### Pool Exhaustion
- Increase `DATABASE_POOL_SIZE`
- Increase `DATABASE_MAX_OVERFLOW`
- Check for connection leaks

### Low Cache Hit Rate
- Increase TTL for stable data
- Review cache invalidation logic
- Check Redis connectivity

### N+1 Queries
- Review relationship loading (eager vs lazy)
- Use `joinedload()` or `selectinload()`
- Batch queries where possible

## Production Load Testing

### Safety Checklist

- [ ] Use dedicated test environment
- [ ] Verify no production data
- [ ] Set up monitoring/alerting
- [ ] Plan for rollback
- [ ] Test during off-hours
- [ ] Start with small load, ramp up gradually

### Realistic Load Profile

1. **Ramp-up** - Gradually increase users
2. **Sustained** - Hold peak load
3. **Spike** - Sudden traffic burst
4. **Cooldown** - Decrease users

```bash
# Example: Realistic ramp-up
locust -f backend/tests/load/locustfile.py \
  --host http://staging.glasswatch.example.com \
  --users 1000 \
  --spawn-rate 20 \
  --run-time 30m \
  --headless
```
