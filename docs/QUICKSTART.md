# Glasswatch Quick Start

**Get up and running with Glasswatch in 5 minutes.**

---

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB+ RAM
- 10GB+ free disk space

---

## 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/glasswatch/glasswatch.git
cd glasswatch

# Create environment file
cp .env.example .env

# (Optional) Edit configuration
nano .env
```

---

## 2. Start Services

```bash
# Start all services
docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected output:
# NAME                STATUS
# glasswatch-backend  Up
# glasswatch-frontend Up
# glasswatch-postgres Up
# glasswatch-redis    Up
```

---

## 3. Access Demo Mode

Open your browser and navigate to:

**Frontend:** http://localhost:3000

Click **"Demo Login"** to access with a pre-configured demo account.

**API Documentation:** http://localhost:8000/docs

---

## 4. Add Your First Vulnerability

### Via UI:

1. Navigate to **Vulnerabilities** → **Add Vulnerability**
2. Enter CVE identifier: `CVE-2024-1234`
3. Fill in details (or let it auto-populate from NVD):
   - Title: "Remote Code Execution in Apache Commons"
   - Severity: CRITICAL
   - CVSS Score: 9.8
4. Click **Save**

### Via API:

```bash
# Get demo access token
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/demo-login | jq -r '.access_token')

# Add vulnerability
curl -X POST http://localhost:8000/api/v1/vulnerabilities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "CVE-2024-1234",
    "source": "nvd",
    "title": "Remote Code Execution in Apache Commons",
    "severity": "CRITICAL",
    "cvss_score": 9.8
  }'
```

---

## 5. Add Your First Asset

### Via UI:

1. Navigate to **Assets** → **Add Asset**
2. Fill in:
   - **Identifier:** `prod-web-01`
   - **Name:** Production Web Server 01
   - **Type:** Server
   - **Platform:** Linux
   - **Environment:** Production
   - **Criticality:** 5 (Critical)
   - **Exposure:** Internet
3. Click **Save**

### Via API:

```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "prod-web-01",
    "name": "Production Web Server 01",
    "type": "server",
    "platform": "linux",
    "environment": "production",
    "criticality": 5,
    "exposure": "internet"
  }'
```

---

## 6. Run Discovery Scan

Automatically discover assets and vulnerabilities:

### Via UI:

1. Navigate to **Discovery** → **Scans**
2. Click **New Scan**
3. Configure:
   - **Name:** "Initial Network Scan"
   - **Type:** Network Scan
   - **Targets:** `192.168.1.0/24` (adjust to your network)
   - Enable: Port scan, Service detection, Vulnerability detection
4. Click **Run Scan**
5. Monitor progress
6. Review discovered assets and vulnerabilities

### Via API:

```bash
curl -X POST http://localhost:8000/api/v1/discovery/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Initial Network Scan",
    "scan_type": "network",
    "targets": ["192.168.1.0/24"],
    "scan_config": {
      "port_scan": true,
      "service_detection": true,
      "vulnerability_detection": true
    }
  }'
```

---

## 7. Create Your First Goal

Convert a business objective into an optimized patch schedule:

### Via UI:

1. Navigate to **Goals** → **Create Goal**
2. Fill in:
   - **Name:** "Eliminate Critical Production Vulnerabilities"
   - **Type:** Zero Critical
   - **Description:** "Zero critical vulnerabilities on production servers by end of quarter"
   - **Target Date:** 2024-06-30
   - **Risk Tolerance:** Balanced
   - **Max Vulnerabilities per Window:** 10
   - **Max Downtime:** 4 hours
3. Scope:
   - **Asset Filters:**
     - Environment: production
     - Exposure: internet
   - **Vulnerability Filters:**
     - Severity: CRITICAL
4. Click **Create & Optimize**
5. Wait 10-30 seconds for optimization
6. Review generated patch bundles

### Via API:

```bash
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eliminate Critical Production Vulnerabilities",
    "type": "zero_critical",
    "description": "Zero critical vulnerabilities on production servers",
    "target_date": "2024-06-30T23:59:59Z",
    "risk_tolerance": "balanced",
    "max_vulns_per_window": 10,
    "max_downtime_hours": 4.0,
    "asset_filters": {
      "environment": ["production"],
      "exposure": ["internet"]
    },
    "vulnerability_filters": {
      "severity": ["CRITICAL"]
    }
  }'

# Run optimization
GOAL_ID="<goal-id-from-response>"
curl -X POST "http://localhost:8000/api/v1/goals/$GOAL_ID/optimize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "maintenance_window_count": 12,
    "start_date": "2024-05-01T00:00:00Z"
  }'
```

---

## 8. View Optimization Results

### Via UI:

1. Navigate to **Bundles**
2. See generated patch bundles:
   - Bundle 1 - Production Critical (Scheduled: 2024-05-04 02:00)
   - Bundle 2 - Production High (Scheduled: 2024-05-11 02:00)
   - ...
3. Click a bundle to view:
   - Affected assets
   - Vulnerabilities to patch
   - Risk score
   - Estimated downtime
4. Review the optimized schedule

### Via API:

```bash
# List bundles
curl -X GET http://localhost:8000/api/v1/bundles \
  -H "Authorization: Bearer $TOKEN"

# Get bundle details
BUNDLE_ID="<bundle-id>"
curl -X GET "http://localhost:8000/api/v1/bundles/$BUNDLE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 9. Simulate Patch Impact

Before approving a bundle, simulate its impact:

### Via UI:

1. Open a bundle
2. Click **Simulate Impact**
3. Review results:
   - Risk score (0-100)
   - Assets affected
   - Services impacted
   - Estimated downtime
   - Is safe to proceed? ✓/✗
4. Click **Run Dry-Run** for full validation:
   - Package availability
   - Disk space
   - Network connectivity
   - Maintenance window verification

### Via API:

```bash
# Predict impact
curl -X POST http://localhost:8000/api/v1/simulator/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"bundle_id\": \"$BUNDLE_ID\"}"

# Run dry-run
curl -X POST http://localhost:8000/api/v1/simulator/dry-run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"bundle_id\": \"$BUNDLE_ID\"}"
```

---

## 10. Approve and Execute

### Via UI:

1. Open bundle
2. Click **Request Approval**
3. Fill in approval request
4. Approver reviews and clicks **Approve**
5. Once approved, click **Execute**
6. Monitor real-time execution progress
7. Verify completion

### Via API:

```bash
# Request approval
curl -X POST http://localhost:8000/api/v1/approvals/requests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"bundle_id\": \"$BUNDLE_ID\",
    \"title\": \"Approve Production Critical Patches\",
    \"description\": \"8 critical vulnerabilities on production servers\",
    \"risk_level\": \"high\"
  }"

# Approve request (as approver)
REQUEST_ID="<request-id>"
curl -X POST "http://localhost:8000/api/v1/approvals/requests/$REQUEST_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"comment\": \"Approved for Saturday maintenance\"}"

# Execute bundle
curl -X POST "http://localhost:8000/api/v1/bundles/$BUNDLE_ID/execute" \
  -H "Authorization: Bearer $TOKEN"
```

---

## What's Next?

### Explore Key Features:

- **🎯 Goals:** Create more complex goals (compliance deadlines, risk reduction targets)
- **📊 Dashboard:** View real-time vulnerability and asset health metrics
- **🔍 Discovery:** Set up scheduled scans for continuous monitoring
- **👥 Team Collaboration:** Add team members and use comments/@mentions
- **📝 Audit Logs:** Review complete audit trail for compliance
- **⚙️ Settings:** Configure maintenance windows, approval policies, integrations

### Read Full Documentation:

- **User Guide:** `docs/USER_GUIDE.md`
- **Admin Guide:** `docs/ADMIN_GUIDE.md`
- **API Reference:** `docs/API.md`
- **Architecture:** `docs/ARCHITECTURE.md`

### Get Help:

- **API Docs:** http://localhost:8000/docs (interactive Swagger UI)
- **Support:** support@glasswatch.ai
- **Documentation:** https://docs.glasswatch.ai

---

## Stopping Services

```bash
# Stop all services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build
```

### Can't connect to database

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec backend python -c \
  "from backend.db.session import engine; print(engine)"

# Reset database
docker-compose down -v
docker-compose up -d
```

### Demo login doesn't work

```bash
# Verify backend is running
curl http://localhost:8000/health

# Check environment variables
docker-compose exec backend env | grep WORKOS

# If WORKOS_API_KEY is set, demo mode is disabled
# Comment out WORKOS_API_KEY in .env for demo mode
```

---

**Happy patching! 🚀**

For detailed guides, see the full documentation in the `docs/` directory.
