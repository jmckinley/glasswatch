# Glasswatch Admin Guide

**Deployment, configuration, and operational guide for Glasswatch administrators.**

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration Reference](#configuration-reference)
3. [User Management](#user-management)
4. [Approval Policies](#approval-policies)
5. [Maintenance Windows](#maintenance-windows)
6. [Backup & Restore](#backup--restore)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tuning](#performance-tuning)
10. [Security Configuration](#security-configuration)
11. [Audit Log Review](#audit-log-review)
12. [Integration Setup](#integration-setup)

---

## Installation

### Prerequisites

**Hardware Requirements:**
- CPU: 4+ cores (8+ recommended for production)
- RAM: 8GB minimum (16GB+ recommended)
- Disk: 50GB+ SSD storage
- Network: 1Gbps network interface

**Software Requirements:**
- Docker 20.10+ and Docker Compose 2.0+
- PostgreSQL 14+ (or use Docker Compose)
- Redis 6.0+ (or use Docker Compose)
- Python 3.11+ (for backend development)
- Node.js 20+ (for frontend development)

### Quick Start with Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/glasswatch/glasswatch.git
   cd glasswatch
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   nano .env
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services:**
   ```bash
   docker-compose ps
   # All services should be "Up"
   ```

5. **Access Glasswatch:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Production Deployment

For production deployments, see detailed guides:
- **Kubernetes**: `docs/deployment/kubernetes.md`
- **AWS ECS**: `docs/deployment/aws-ecs.md`
- **Azure**: `docs/deployment/azure.md`
- **GCP**: `docs/deployment/gcp.md`

---

## Configuration Reference

### Environment Variables

#### Core Application

```bash
# Basic Configuration
PROJECT_NAME=PatchGuide
VERSION=1.0.0
API_V1_STR=/api/v1
ENV=production  # development, staging, production
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4  # Number of uvicorn workers
```

#### Database

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/glasswatch

# Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# SSL (production)
DB_SSL_MODE=require
DB_SSL_CERT=/path/to/cert.pem
```

#### Redis

```bash
# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Connection Pool
REDIS_POOL_SIZE=10
REDIS_POOL_TIMEOUT=5

# SSL (production)
REDIS_SSL=true
REDIS_SSL_CERT=/path/to/cert.pem
```

#### Security

```bash
# JWT Authentication
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=https://app.glasswatch.ai,https://glasswatch.ai

# Trusted Hosts
TRUSTED_HOSTS=app.glasswatch.ai,api.glasswatch.ai
ENABLE_TRUSTED_HOSTS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STANDARD=1000  # requests/hour
RATE_LIMIT_OPTIMIZATION=10  # requests/hour
RATE_LIMIT_SEARCH=500  # requests/hour
```

#### External Services

```bash
# WorkOS (SSO Authentication)
WORKOS_API_KEY=sk_live_...
WORKOS_CLIENT_ID=client_...
WORKOS_REDIRECT_URI=https://app.glasswatch.ai/auth/callback

# NVD (Vulnerability Data)
NVD_API_KEY=your-nvd-api-key
NVD_API_URL=https://services.nvd.nist.gov/rest/json/cves/2.0

# EPSS (Exploit Prediction)
EPSS_API_URL=https://api.first.org/data/v1/epss

# AWS (for KMS encryption)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=secret...
AWS_KMS_KEY_ID=arn:aws:kms:...

# Snapper Runtime Integration
SNAPPER_API_URL=https://snapper.internal/api
SNAPPER_API_KEY=snapper_key_...
SNAPPER_SYNC_INTERVAL_HOURS=6

# Patch Weather Service
PATCH_WEATHER_ENABLED=true
PATCH_WEATHER_API_URL=https://patchweather.ai/api
PATCH_WEATHER_MIN_REPORTS=5
```

#### Optimization

```bash
# Constraint Solver
OPTIMIZATION_MAX_TIME_SECONDS=30
OPTIMIZATION_DEFAULT_WINDOWS=12
OPTIMIZATION_THREAD_LIMIT=4

# Batch Processing
BATCH_SIZE=100
BATCH_TIMEOUT_SECONDS=300
```

#### Observability

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # text or json
LOG_FILE=/var/log/glasswatch/app.log

# Metrics (Prometheus)
METRICS_ENABLED=true
METRICS_PORT=9090

# Tracing (OpenTelemetry)
OTEL_ENABLED=true
OTEL_ENDPOINT=http://jaeger:4318
OTEL_SERVICE_NAME=glasswatch-backend

# Sentry (Error Tracking)
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

#### Email Notifications

```bash
# SMTP Configuration
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxx...
SMTP_FROM=noreply@glasswatch.ai
SMTP_FROM_NAME=Glasswatch

# Email Features
EMAIL_ENABLED=true
EMAIL_DIGEST_ENABLED=true
EMAIL_APPROVAL_NOTIFICATIONS=true
```

#### Feature Flags

```bash
# Features
FEATURE_PATCH_WEATHER=true
FEATURE_AI_ASSISTANT=true
FEATURE_WEBHOOKS=true
FEATURE_ADVANCED_REPORTING=true
FEATURE_SNAPPER_INTEGRATION=true
```

---

## User Management

### Roles and Permissions

| Role | Capabilities |
|------|--------------|
| **Viewer** | Read-only access to all resources |
| **Analyst** | Viewer + Create goals, bundles, comments |
| **Operator** | Analyst + Execute bundles, manage assets |
| **Admin** | Full access + User management, configuration |

### Creating Users

#### Via SSO (Production)

Users are automatically provisioned on first SSO login:
1. User authenticates via WorkOS SSO
2. System creates user account with default role (Analyst)
3. Admin can upgrade role as needed

#### Manual User Creation (Development)

```bash
# Connect to backend container
docker-compose exec backend bash

# Create user via CLI
python scripts/create_user.py \
  --email alice@acme.com \
  --name "Alice Smith" \
  --role admin \
  --tenant-id <tenant-uuid>
```

### User Invitation Flow

1. Admin navigates to **Users** > **Invite User**
2. Fill in:
   - Email address
   - Full name
   - Initial role
   - Optional: Custom permissions
3. Click **Send Invitation**
4. User receives email with:
   - Welcome message
   - Login instructions
   - Initial password reset link (if not SSO)
5. User completes setup on first login

### Modifying User Roles

1. Navigate to **Users**
2. Click user to modify
3. Select new role from dropdown
4. **Optional**: Add custom permissions
5. Click **Save**
6. User's access updates immediately

### Deactivating Users

**Soft Delete** (recommended):
1. Navigate to **Users**
2. Click user to deactivate
3. Click **Deactivate**
4. Confirm action
5. User can't log in but audit logs are preserved

**Hard Delete** (audit log impact):
1. Only for compliance/legal requirements
2. Contact support or use admin CLI
3. All user data is permanently removed

### Custom Permissions

Fine-grained permissions beyond roles:

```json
{
  "can_approve_bundles": true,
  "can_execute_production": true,
  "can_modify_goals": true,
  "can_delete_assets": false,
  "can_manage_users": false,
  "max_bundle_risk_score": 80
}
```

Set via user edit form or API.

---

## Approval Policies

### Default Policies

Glasswatch ships with sensible defaults:

**Production Critical:**
- Required Approvals: 2
- Timeout: 48 hours
- Conditions: Environment=production AND Risk≥80
- Approvers: Admin, Security Lead

**Production Standard:**
- Required Approvals: 1
- Timeout: 24 hours
- Conditions: Environment=production AND Risk<80
- Approvers: Admin, Operator

**Non-Production:**
- Auto-approve if Risk<40
- Manual approval if Risk≥40
- Timeout: 12 hours

### Creating Custom Policies

1. Navigate to **Settings** > **Approval Policies**
2. Click **New Policy**
3. Configure:
   - **Name**: Descriptive policy name
   - **Description**: When this policy applies
   - **Required Approvals**: Number (1-5)
   - **Auto-Approve Threshold**: Risk score for auto-approval (or null)
   - **Timeout**: Hours until expiration
   - **Conditions**:
     - Environment (production, staging, etc.)
     - Risk level (low, medium, high, critical)
     - Asset criticality
     - Vulnerability severity
     - Custom JSON conditions
   - **Approver Roles**: Which roles can approve
   - **Notification Settings**:
     - Email approvers immediately
     - Escalate if timeout approaching
4. Click **Create**

**Example: Emergency Patch Policy**
```json
{
  "name": "Emergency Critical Patch",
  "required_approvals": 1,
  "auto_approve_threshold": null,
  "timeout_hours": 4,
  "conditions": {
    "vulnerability_kev_listed": true,
    "exploit_available": true,
    "asset_exposure": "internet"
  },
  "approver_roles": ["admin"],
  "escalation_enabled": true,
  "escalation_after_hours": 2
}
```

### Policy Priority

When multiple policies match:
1. Most specific conditions win
2. Highest approval count wins
3. Shortest timeout wins

---

## Maintenance Windows

### Creating Maintenance Windows

1. Navigate to **Settings** > **Maintenance Windows**
2. Click **New Window**
3. Configure:
   - **Name**: "Production Saturday Maintenance"
   - **Type**: Scheduled, Emergency, or Blackout
   - **Schedule**:
     - Start time
     - End time
     - Timezone
     - Recurrence (weekly, monthly, custom)
   - **Scope**:
     - Environment (production, staging, etc.)
     - Asset groups
     - Criticality levels
   - **Constraints**:
     - Max duration (hours)
     - Max assets affected
     - Approved activities
   - **Approvals**:
     - Requires approval?
     - Approver roles
4. Click **Create**

### Recurring Windows

**Weekly Example:**
```
Every Saturday, 2:00 AM - 6:00 AM UTC
Environment: Production
Max Duration: 4 hours
Max Assets: 50
```

**Monthly Example:**
```
First Sunday of each month, 3:00 AM - 7:00 AM EST
Environment: All
Max Duration: 4 hours
Requires Approval: Yes
```

### Emergency Windows

Create ad-hoc windows for urgent patching:
1. Click **Create Emergency Window**
2. Set immediate or near-future start time
3. Shorter approval timeouts apply
4. Higher notification priority

### Change Freezes (Blackout Windows)

Prevent all patching during critical periods:
1. Create window with type "Blackout"
2. Set date range (e.g., holiday season, major launch)
3. All bundle execution blocked during freeze
4. Exceptions require admin override

**Example: Holiday Freeze**
```
December 20 - January 5
Type: Blackout
Reason: Holiday change freeze
Override: Admin only
```

---

## Backup & Restore

### Database Backups

#### Automated Backups (Recommended)

**PostgreSQL with pg_dump:**
```bash
# Daily backup cron job
0 2 * * * /usr/bin/docker-compose exec -T postgres \
  pg_dump -U glasswatch glasswatch | \
  gzip > /backups/glasswatch-$(date +\%Y\%m\%d).sql.gz

# Retention: Keep 30 days
find /backups -name "glasswatch-*.sql.gz" -mtime +30 -delete
```

**AWS RDS Automated Backups:**
- Enable automated backups (7-35 day retention)
- Daily backup window during low traffic
- Point-in-time recovery available

#### Manual Backup

```bash
# One-time backup
docker-compose exec postgres pg_dump -U glasswatch glasswatch \
  > glasswatch-backup-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# Stop application
docker-compose stop backend frontend

# Restore database
docker-compose exec -T postgres psql -U glasswatch glasswatch \
  < glasswatch-backup-20260420.sql

# Restart application
docker-compose start backend frontend

# Verify restoration
docker-compose exec backend python scripts/verify_db.py
```

### Configuration Backups

Backup critical configuration files:
```bash
# Environment configuration
cp .env .env.backup.$(date +%Y%m%d)

# Docker Compose
cp docker-compose.yml docker-compose.yml.backup

# Custom configs
tar -czf configs-$(date +%Y%m%d).tar.gz \
  backend/core/config.py \
  backend/core/security_config.py \
  .env
```

### Disaster Recovery

**Full Recovery Procedure:**
1. Provision new infrastructure
2. Restore latest database backup
3. Restore configuration files
4. Deploy application containers
5. Verify services are healthy
6. Test critical functionality
7. Update DNS if needed

**RTO/RPO:**
- Recovery Time Objective (RTO): <4 hours
- Recovery Point Objective (RPO): <24 hours (daily backups)

---

## Monitoring & Observability

### Health Checks

**Application Health:**
```bash
# API health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "PatchGuide",
  "version": "1.0.0",
  "checks": {
    "api": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

**Database Health:**
```bash
# Check active connections
docker-compose exec postgres psql -U glasswatch -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check database size
docker-compose exec postgres psql -U glasswatch -c \
  "SELECT pg_size_pretty(pg_database_size('glasswatch'));"
```

**Redis Health:**
```bash
docker-compose exec redis redis-cli ping
# Expected: PONG

docker-compose exec redis redis-cli info stats
```

### Prometheus Metrics

**Exposed Metrics** (port 9090):
- `http_requests_total` - Total HTTP requests by endpoint, method, status
- `http_request_duration_seconds` - Request latency histogram
- `db_connections_active` - Active database connections
- `db_query_duration_seconds` - Database query latency
- `optimization_runs_total` - Total optimization runs
- `optimization_duration_seconds` - Optimization execution time
- `bundle_executions_total` - Bundle executions by status
- `vulnerability_scans_total` - Discovery scans by status

**Grafana Dashboard:**
- Import dashboard from `monitoring/grafana/dashboard.json`
- Pre-configured panels for key metrics
- Alerts for critical thresholds

### Logging

**Log Levels:**
- DEBUG: Detailed diagnostic information
- INFO: General informational messages
- WARNING: Warning messages (potential issues)
- ERROR: Error messages (failures)
- CRITICAL: Critical failures requiring immediate attention

**Log Aggregation:**

**ELK Stack:**
```yaml
# docker-compose.yml
  elasticsearch:
    image: elasticsearch:8.11
    ...
  
  logstash:
    image: logstash:8.11
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ...
  
  kibana:
    image: kibana:8.11
    ...
```

**CloudWatch (AWS):**
```bash
# Install awslogs driver
docker-compose exec backend pip install awscli

# Configure log driver in docker-compose.yml
logging:
  driver: awslogs
  options:
    awslogs-region: us-east-1
    awslogs-group: /glasswatch/backend
    awslogs-stream: backend
```

### Alerting

**Critical Alerts:**
- Service down (frontend, backend, database, redis)
- Database connection pool exhausted
- High error rate (>5% of requests)
- Optimization failures
- Bundle execution failures
- Disk space <10%
- Memory usage >90%

**Warning Alerts:**
- High response times (p95 > 2s)
- Approaching rate limits
- Approaching database connection limits
- Low Patch Weather scores in bundles
- Approval request timeouts approaching

**Alert Channels:**
- Email
- PagerDuty
- Slack
- SMS (Twilio)

---

## Troubleshooting

### Common Issues

#### Database Connection Errors

**Symptom:** `FATAL: too many connections`

**Solution:**
```bash
# Check current connections
docker-compose exec postgres psql -U glasswatch -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Increase max_connections in postgresql.conf
docker-compose exec postgres bash -c \
  "echo 'max_connections = 200' >> /var/lib/postgresql/data/postgresql.conf"

# Restart PostgreSQL
docker-compose restart postgres

# Adjust application pool size
# In .env:
DB_POOL_SIZE=50  # Reduce from default
DB_MAX_OVERFLOW=20
```

#### Slow Optimization

**Symptom:** Goal optimization times out after 30 seconds

**Solution:**
```bash
# Increase timeout (in .env)
OPTIMIZATION_MAX_TIME_SECONDS=60

# Reduce problem size:
# - Fewer maintenance windows
# - Narrower asset scope
# - Fewer vulnerabilities

# Check thread limit
OPTIMIZATION_THREAD_LIMIT=8  # Increase if CPU available
```

#### Redis Connection Issues

**Symptom:** `Error connecting to Redis`

**Solution:**
```bash
# Verify Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
docker-compose exec backend python -c \
  "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Clear Redis if corrupted
docker-compose exec redis redis-cli FLUSHALL
```

#### SSO Login Failures

**Symptom:** "SSO callback failed" or infinite redirect

**Solution:**
```bash
# Verify WorkOS configuration
echo $WORKOS_API_KEY  # Should be sk_live_...
echo $WORKOS_CLIENT_ID  # Should be client_...
echo $WORKOS_REDIRECT_URI  # Must match WorkOS dashboard

# Check WorkOS connection
curl -H "Authorization: Bearer $WORKOS_API_KEY" \
  https://api.workos.com/organizations

# Test SSO flow manually:
# 1. Get authorization URL
# 2. Complete flow in browser
# 3. Check callback logs for errors
```

#### High Memory Usage

**Symptom:** Container using excessive memory, OOM kills

**Solution:**
```bash
# Check memory usage
docker stats

# Reduce worker count (in .env)
WORKERS=2  # Reduce from 4

# Set memory limits in docker-compose.yml
services:
  backend:
    mem_limit: 2g
    mem_reservation: 1g

# Optimize batch sizes
BATCH_SIZE=50  # Reduce from 100

# Check for memory leaks
docker-compose exec backend python scripts/memory_profiler.py
```

### Debug Mode

Enable detailed logging:
```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart backend

# Tail logs
docker-compose logs -f backend
```

### Support Diagnostics

Generate diagnostic bundle for support:
```bash
# Run diagnostic script
docker-compose exec backend python scripts/diagnostics.py \
  --output /tmp/diagnostics.json

# Includes:
# - System info
# - Configuration (sensitive values redacted)
# - Recent logs
# - Health checks
# - Resource usage
# - Database stats

# Send to support
curl -F "file=@/tmp/diagnostics.json" \
  https://support.glasswatch.ai/upload
```

---

## Performance Tuning

### Database Optimization

**Connection Pooling:**
```bash
# Tune based on workload
DB_POOL_SIZE=20  # Standard: 20-50
DB_MAX_OVERFLOW=10  # Burst capacity
DB_POOL_TIMEOUT=30  # Connection wait time
DB_POOL_RECYCLE=3600  # Recycle connections hourly
```

**Query Optimization:**
```sql
-- Create indexes for common queries
CREATE INDEX idx_assets_tenant_env ON assets(tenant_id, environment);
CREATE INDEX idx_vulns_severity ON vulnerabilities(severity, kev_listed);
CREATE INDEX idx_bundles_status_scheduled ON bundles(status, scheduled_for);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM assets WHERE tenant_id = '...' AND environment = 'production';
```

**Vacuum and Analyze:**
```bash
# Auto-vacuum configuration
ALTER TABLE assets SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE vulnerabilities SET (autovacuum_analyze_scale_factor = 0.05);

# Manual vacuum
docker-compose exec postgres vacuumdb -U glasswatch -d glasswatch --analyze --verbose
```

### Redis Optimization

```bash
# Increase max memory
docker-compose exec redis redis-cli CONFIG SET maxmemory 2gb

# Set eviction policy
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Persistence (if needed)
docker-compose exec redis redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Application Tuning

**Worker Configuration:**
```bash
# CPU-bound workload: workers = (2 × CPU cores) + 1
# I/O-bound workload: workers = more (experiment)

WORKERS=9  # For 4-core system (2×4 + 1)
```

**Caching Strategy:**
```python
# Aggressive caching (in backend/core/config.py)
CACHE_TTL_VULNERABILITIES = 3600  # 1 hour
CACHE_TTL_ASSETS = 1800  # 30 minutes
CACHE_TTL_STATS = 300  # 5 minutes
```

### Optimization Engine Tuning

```bash
# Limit time spent on optimization
OPTIMIZATION_MAX_TIME_SECONDS=30  # Balance quality vs speed

# Thread limit (match CPU cores)
OPTIMIZATION_THREAD_LIMIT=4

# Solution quality vs speed
OPTIMIZATION_SOLUTION_LIMIT=100  # More = better quality but slower
```

---

## Security Configuration

### TLS/SSL

**Application TLS:**
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name app.glasswatch.ai;
    
    ssl_certificate /etc/ssl/certs/glasswatch.crt;
    ssl_certificate_key /etc/ssl/private/glasswatch.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Database TLS:**
```bash
# In .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
DB_SSL_CERT=/path/to/client-cert.pem
DB_SSL_KEY=/path/to/client-key.pem
DB_SSL_ROOT_CERT=/path/to/root-cert.pem
```

### Secrets Management

**HashiCorp Vault Integration:**
```python
# backend/core/secrets.py
from hvac import Client

vault_client = Client(url='https://vault.internal:8200')
vault_client.auth.approle.login(
    role_id=os.getenv('VAULT_ROLE_ID'),
    secret_id=os.getenv('VAULT_SECRET_ID'),
)

# Fetch secrets
db_password = vault_client.secrets.kv.v2.read_secret_version(
    path='glasswatch/database'
)['data']['data']['password']
```

**AWS Secrets Manager:**
```python
import boto3

client = boto3.client('secretsmanager', region_name='us-east-1')
secret = client.get_secret_value(SecretId='glasswatch/database')
db_password = json.loads(secret['SecretString'])['password']
```

### Security Headers

Configured in `backend/middleware/security.py`:
```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

### Network Security

**Firewall Rules:**
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH (admin only)
ufw allow 443/tcp   # HTTPS
ufw deny 5432/tcp   # PostgreSQL (internal only)
ufw deny 6379/tcp   # Redis (internal only)
ufw enable
```

**Network Isolation:**
- Frontend → Backend: Internal network only
- Backend → Database: Internal network only
- Backend → Redis: Internal network only
- External APIs: Egress allowed via NAT

---

## Audit Log Review

### Accessing Audit Logs

1. Navigate to **Settings** > **Audit Logs**
2. Filter by:
   - User
   - Action type
   - Resource type
   - Date range
3. Export for compliance reporting

### Common Audit Queries

**Failed Login Attempts:**
```sql
SELECT * FROM audit_logs 
WHERE action = 'user.login_failed' 
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

**Privilege Escalations:**
```sql
SELECT * FROM audit_logs 
WHERE action = 'user.role_changed' 
  AND metadata->>'new_role' = 'admin'
ORDER BY timestamp DESC;
```

**Bundle Executions:**
```sql
SELECT * FROM audit_logs 
WHERE action IN ('bundle.approved', 'bundle.executed', 'bundle.completed')
  AND resource_id = '<bundle-uuid>'
ORDER BY timestamp ASC;
```

### Retention Policy

- **Hot Storage**: Last 90 days (PostgreSQL)
- **Warm Storage**: 90 days - 1 year (S3/GCS)
- **Cold Storage**: 1-7 years (Glacier/Coldline)
- **Legal Holds**: Indefinite retention as needed

---

## Integration Setup

### ITSM Integration

**ServiceNow:**
```bash
# In .env
SERVICENOW_INSTANCE=acme.service-now.com
SERVICENOW_USERNAME=glasswatch_integration
SERVICENOW_PASSWORD=secure_password

# Create change requests automatically
SERVICENOW_AUTO_CREATE_CHANGES=true
SERVICENOW_CHANGE_TYPE=Standard
SERVICENOW_ASSIGNMENT_GROUP=Patch Management
```

**Jira:**
```bash
JIRA_URL=https://acme.atlassian.net
JIRA_USERNAME=glasswatch@acme.com
JIRA_API_TOKEN=xxx...
JIRA_PROJECT_KEY=PATCH
JIRA_AUTO_CREATE_TICKETS=true
```

### Patch Deployment Tools

**Ansible:**
```yaml
# Configure in Settings → Integrations → Ansible
ansible:
  controller_url: https://ansible.internal
  username: glasswatch
  token: xxx...
  inventory: production
  playbook_path: /playbooks/patch.yml
```

**AWS Systems Manager:**
```bash
AWS_SSM_ENABLED=true
AWS_SSM_DOCUMENT_NAME=AWS-RunPatchBaseline
AWS_SSM_NOTIFICATION_ARN=arn:aws:sns:...
```

### Webhooks

Configure webhooks for external system integration:
```json
{
  "url": "https://external-system.com/webhook",
  "events": ["bundle.approved", "bundle.executed"],
  "secret": "webhook_secret_key",
  "headers": {
    "X-Custom-Header": "value"
  }
}
```

---

**For additional support, contact:** support@glasswatch.ai
