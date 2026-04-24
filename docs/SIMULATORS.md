# External API Simulators

## Overview

Glasswatch ships with a full simulator server for all external integrations. The simulator
lets developers test the complete integration flow — auth, data formatting, error handling,
pagination — without needing real credentials or touching production systems.

The simulator is a standalone FastAPI app that:

- Validates auth headers exactly as the real services do (returns **401** on wrong format)
- Returns realistic data with real CVE IDs, CVSS scores, and EPSS values
- Matches the real response format exactly (same field names, nesting, data types)
- Supports error simulation via `?simulate_error=true`
- Logs all requests to stdout with timestamp, method, path, and auth presence

---

## Starting the Simulator

```bash
# From the backend/ directory:
uvicorn backend.simulators.external_apis:app --port 8099

# Or from the repo root:
cd ~/glasswatch
uvicorn backend.simulators.external_apis:app --port 8099
```

The simulator listens on `http://localhost:8099` by default.

Check it's running:
```bash
curl http://localhost:8099/simulator/status
```

---

## Endpoints Simulated

| Service             | Simulator Base URL                     | Auth Method                              | Response Format |
|---------------------|----------------------------------------|------------------------------------------|-----------------|
| Tenable.io          | `http://localhost:8099/tenable`        | `X-ApiKeys: accessKey=...;secretKey=...` | JSON            |
| Qualys VMPC         | `http://localhost:8099/qualys`         | `Authorization: Basic <base64>`          | XML             |
| Rapid7 InsightVM    | `http://localhost:8099/rapid7`         | `Authorization: Basic <base64>`          | JSON (HAL)      |
| Slack               | `http://localhost:8099/slack`          | `Authorization: Bearer xoxb-...`         | JSON            |
| Microsoft Teams     | `http://localhost:8099/teams`          | None (webhook URL is the secret)         | Plain text      |
| Jira                | `http://localhost:8099/jira`           | `Authorization: Basic <base64(email:token)>` | JSON        |
| ServiceNow          | `http://localhost:8099/servicenow`     | `Authorization: Basic <base64>`          | JSON            |
| CISA KEV            | `http://localhost:8099/cisa/kev`       | None                                     | JSON            |
| NVD (NIST)          | `http://localhost:8099/nvd`            | None (optional `apiKey` header)          | JSON            |
| EPSS                | `http://localhost:8099/epss`           | None                                     | JSON            |
| Resend (email)      | `http://localhost:8099/resend`         | `Authorization: Bearer re_...`           | JSON            |

---

## Key Endpoints

### Tenable.io
```
GET  /tenable/workbenches/vulnerabilities  — List vulnerabilities
GET  /tenable/workbenches/assets           — List assets
GET  /tenable/scans                        — List scans
POST /tenable/vulns/export                 — Start export (returns export_uuid)
GET  /tenable/vulns/export/{uuid}/status   — Poll export (PROCESSING → FINISHED)
GET  /tenable/vulns/export/{uuid}/chunks/1 — Download chunk (list of vulns)
```

### Qualys VMPC
```
GET  /qualys/api/2.0/fo/scan/      — List scans (XML)
POST /qualys/api/2.0/fo/report/    — Download vuln report (XML, VULN_LIST format)
GET  /qualys/msp/about.php         — Health check (XML)
```

### Rapid7 InsightVM
```
GET  /rapid7/api/3/health           — Health check
GET  /rapid7/api/3/vulnerabilities  — Paginated vulns (HAL JSON, ?page=0&size=10)
GET  /rapid7/api/3/assets           — Asset list (HAL JSON)
POST /rapid7/api/3/reports          — Create report
```

### Slack
```
POST /slack/api/chat.postMessage    — Post message
POST /slack/api/auth.test           — Auth test
```

### Microsoft Teams
```
POST /teams/webhook                 — Incoming webhook (MessageCard or Adaptive Card)
```

### Jira
```
POST /jira/rest/api/3/issue         — Create issue
GET  /jira/rest/api/3/project       — List projects
GET  /jira/rest/api/3/myself        — Get current user (health check)
```

### ServiceNow
```
POST /servicenow/api/now/table/incident          — Create incident
GET  /servicenow/api/now/table/cmdb_ci_server    — Query CMDB servers
GET  /servicenow/api/now/health                  — Health check
```

### CISA KEV / NVD / EPSS
```
GET /cisa/kev                              — Full KEV catalog
GET /nvd/rest/json/cves/2.0?cveId=CVE-...  — CVE lookup
GET /epss/data/v1/epss?cve=CVE-...         — EPSS score lookup
```

### Resend
```
POST /resend/emails         — Send email
GET  /resend/emails/{id}    — Get email status
```

---

## Testing with the Simulator

### Method 1: Environment variable (recommended)

Set `SIMULATOR_MODE=true` to route all Tenable/Qualys/Rapid7/Slack/etc. calls to the
local simulator. The `get_endpoint()` helper in `backend/simulators/config.py` performs
the URL swap automatically.

```bash
# Start the simulator in one terminal:
uvicorn backend.simulators.external_apis:app --port 8099

# Run tests with simulator in another:
SIMULATOR_MODE=true python3 -m pytest backend/tests/ -q
```

### Method 2: Standalone test script

```bash
# Start the simulator first, then:
python3 backend/simulators/test_simulators.py
```

This runs a comprehensive test of every endpoint and prints PASS/FAIL for each check.

### Method 3: Direct curl

```bash
# Tenable vulns
curl -H "X-ApiKeys: accessKey=test;secretKey=test" \
  http://localhost:8099/tenable/workbenches/vulnerabilities | jq .

# Qualys report (XML)
curl -u user:pass http://localhost:8099/qualys/api/2.0/fo/report/ -X POST

# Rapid7 vulns
curl -u user:pass http://localhost:8099/rapid7/api/3/vulnerabilities | jq .

# Slack message
curl -H "Authorization: Bearer xoxb-test" \
  -d '{"channel":"#test","text":"hi"}' -H "Content-Type: application/json" \
  http://localhost:8099/slack/api/chat.postMessage | jq .

# CISA KEV (no auth)
curl http://localhost:8099/cisa/kev | jq .keys
```

---

## Error Simulation

Any endpoint accepts `?simulate_error=true` to return a random 429, 500, or 503 error.
Use this to test your error-handling and retry logic:

```bash
curl "http://localhost:8099/tenable/workbenches/vulnerabilities?simulate_error=true" \
  -H "X-ApiKeys: accessKey=test;secretKey=test"
# Returns 429, 500, or 503
```

---

## Sample Data

All simulators share a consistent set of 10 CVEs spread across 5 assets:

| CVE ID            | Vendor         | CVSS | KEV | Asset           |
|-------------------|----------------|------|-----|-----------------|
| CVE-2024-21887    | Ivanti         | 9.8  | ✅  | vpn-gateway-01  |
| CVE-2024-1709     | ConnectWise    | 9.8  | ✅  | app-server-01   |
| CVE-2024-3400     | Palo Alto      | 10.0 | ✅  | vpn-gateway-01  |
| CVE-2024-23897    | Jenkins        | 9.1  | ❌  | app-server-01   |
| CVE-2023-44487    | IETF (HTTP/2)  | 7.5  | ✅  | web-server-01   |
| CVE-2024-4040     | CrushFTP       | 9.8  | ✅  | web-server-01   |
| CVE-2024-27198    | JetBrains      | 9.8  | ❌  | k8s-node-01     |
| CVE-2024-6387     | OpenSSH        | 8.1  | ✅  | db-server-01    |
| CVE-2024-38094    | Microsoft      | 7.2  | ✅  | app-server-01   |
| CVE-2024-49138    | Microsoft      | 7.8  | ✅  | k8s-node-01     |

---

## Adding New Simulators

Follow this pattern for each new service:

1. **Add auth validator** — mirror the real service's auth mechanism exactly.
   Return 401 if headers are missing or malformed.

2. **Add routes** under a `/servicename/` prefix matching the real API path structure.

3. **Return realistic data** — use real field names and types from the official API docs.

4. **Add `simulate_error` support** — call `_maybe_error(simulate_error)` early in each handler.

5. **Log the request** — call `_log(request, bool(auth_header))`.

6. **Add to `SIMULATOR_ENDPOINTS`** in `backend/simulators/config.py`.

7. **Write unit tests** in `backend/tests/unit/test_external_api_simulators.py` — at minimum:
   - Missing auth → 401
   - Wrong auth format → 401
   - Happy path → 200 with correct structure
   - Error simulation → ≥400

Example skeleton:
```python
def _require_myservice_auth(authorization: Optional[str]) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing auth")
    if not authorization.startswith("Bearer myprefix-"):
        raise HTTPException(status_code=401, detail="Invalid auth scheme")

@app.get("/myservice/api/resource")
async def myservice_list_resources(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    _log(request, bool(authorization))
    _require_myservice_auth(authorization)
    _maybe_error(simulate_error)
    return {"resources": [...], "total": N}
```
