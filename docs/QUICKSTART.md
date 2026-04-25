# Glasswatch Quick Start

**Get up and running with Glasswatch in under 5 minutes.**

---

## Option A: Try the Demo (No Signup)

The fastest way to see Glasswatch:

**Live Demo:** https://frontend-production-ef3e.up.railway.app

Click **"Demo Login"** — no account needed. The demo tenant is pre-loaded with synthetic assets, vulnerabilities, and goals. All features work: create goals, approve bundles, run the AI assistant, check the audit log. Demo data resets periodically.

---

## Option B: Self-Hosted

Install Glasswatch on your own server (requires Docker 20.10+ and Docker Compose 2.0+):

```bash
curl -fsSL https://raw.githubusercontent.com/jmckinley/glasswatch/main/install.sh | bash
```

The script handles environment setup, pulls images, and starts all services.

Once running:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (interactive Swagger UI)

Click **"Demo Login"** on the login page to access a pre-configured demo account.

---

## 1. Connect Your Scanner

Glasswatch accepts vulnerability data from Tenable, Qualys, or Rapid7 via webhook, or from any scanner via CSV import.

### Webhook (Tenable / Qualys / Rapid7)

Configure your scanner to POST findings to:

```
POST https://<your-host>/api/v1/webhooks/scanner/tenable
POST https://<your-host>/api/v1/webhooks/scanner/qualys
POST https://<your-host>/api/v1/webhooks/scanner/rapid7
Authorization: Bearer <your-api-key>
```

See [SCANNING_INTEGRATIONS.md](SCANNING_INTEGRATIONS.md) and [SIMULATORS.md](SIMULATORS.md) for full setup details.

**Testing without real credentials?** Use the built-in API Simulators — they mimic real scanner payloads without any external accounts:

```bash
# Add to .env
SIMULATOR_MODE=true
```

With `SIMULATOR_MODE=true`, the simulators run on port 8099 and can push synthetic scan results directly into Glasswatch. See [SIMULATORS.md](SIMULATORS.md) for all supported systems.

### CSV Import

1. Navigate to **Vulnerabilities** → **Import**
2. Upload a CSV with your vulnerability and asset data
3. Map columns to Glasswatch fields (scanner column mappings are pre-configured for common formats)
4. Click **Import**

---

## 2. Create Your First Goal

Convert a business objective into an optimized patch schedule:

### Via UI:

1. Navigate to **Goals** → **Create Goal**
2. Fill in:
   - **Name:** "Eliminate Critical Production Vulnerabilities"
   - **Type:** Zero Critical
   - **Description:** "Zero critical vulnerabilities on production servers by end of quarter"
   - **Target Date:** (pick a date)
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
# Get demo access token
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/demo-login | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eliminate Critical Production Vulnerabilities",
    "type": "zero_critical",
    "description": "Zero critical vulnerabilities on production servers",
    "target_date": "2025-06-30T23:59:59Z",
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
    "start_date": "2025-05-01T00:00:00Z"
  }'
```

---

## 3. Review Generated Bundles

### Via UI:

1. Navigate to **Bundles**
2. See generated patch bundles:
   - Bundle 1 - Production Critical (Scheduled: next maintenance window)
   - Bundle 2 - Production High (Scheduled: following window)
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

## 4. Simulate Patch Impact

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

## 5. Approve and Execute

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
    \"description\": \"Critical vulnerabilities on production servers\",
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

## 6. Check the Audit Log

Every action in Glasswatch is recorded in the audit log — goal creation, bundle approvals, user changes, everything. This supports compliance reviews and forensic investigation.

### Via UI:

1. Navigate to **Audit Log** in the sidebar
2. Filter by action type, user, or date range
3. Verify the actions you just took are recorded (goal created, bundle approved, etc.)
4. Export to CSV for compliance reporting

### Via API:

```bash
curl -X GET "http://localhost:8000/api/v1/audit-log?limit=20" \
  -H "Authorization: Bearer $TOKEN"

# Export as CSV
curl -X GET "http://localhost:8000/api/v1/audit-log/export" \
  -H "Authorization: Bearer $TOKEN" \
  -o audit-log.csv
```

---

## What's Next?

### Explore Key Features:

- **🎯 Goals:** Create more complex goals (compliance deadlines, risk reduction targets)
- **📊 Dashboard:** View real-time vulnerability and asset health metrics
- **👥 Team Collaboration:** Add team members and use comments/@mentions
- **🤖 AI Assistant:** Ask "What needs my attention?" or "Create a rule blocking Friday deployments"
- **📋 Compliance Dashboard:** Track BOD 22-01, SLA status, and MTTP
- **⚙️ Settings:** Configure maintenance windows, approval policies, integrations

### Read Full Documentation:

- **User Guide:** `docs/USER_GUIDE.md`
- **Admin Guide:** `docs/ADMIN_GUIDE.md`
- **API Reference:** `docs/API.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Scanner Integrations:** `docs/SCANNING_INTEGRATIONS.md`
- **API Simulators:** `docs/SIMULATORS.md`

### Get Help:

- **API Docs:** http://localhost:8000/docs (interactive Swagger UI)
- **Support:** support@glasswatch.ai

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

# Reset database
docker-compose down -v
docker-compose up -d
```

### Demo login doesn't work

```bash
# Verify backend is running
curl http://localhost:8000/health

# If WORKOS_API_KEY is set, SSO mode is active — demo login requires it to be unset
# Comment out WORKOS_API_KEY in .env for demo mode
```

---

**Happy patching! 🚀**

For detailed guides, see the full documentation in the `docs/` directory.
