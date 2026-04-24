# Glasswatch — Systems & Integration Reference

Technical reference for integrators, security engineers, and platform teams.

---

## Supported Integrations

Glasswatch integrates with the following external systems. Each category below links to the detailed configuration section.

### Vulnerability Scanners
| System | Protocol | Auth method | Section |
|---|---|---|---|
| **Tenable** (Nessus / Tenable.io) | Inbound webhook | X-Webhook-Secret | [Tenable](#tenable) |
| **Qualys** | Inbound webhook | X-Webhook-Secret | [Qualys](#qualys) |
| **Rapid7 InsightVM** | Inbound webhook | X-Webhook-Secret | [Rapid7](#rapid7) |
| **CSV Import** | File upload | Bearer JWT | `/api/v1/import/vulnerabilities/csv` |

### Ticketing & Change Management
| System | Protocol | Auth method |
|---|---|---|
| **Jira** | Bidirectional webhook | API token + basic auth |
| **ServiceNow** | Outbound webhook | Username + password |

### Notifications & Messaging
| System | Protocol | Config location |
|---|---|---|
| **Slack** | Outbound webhook | Settings → Notifications → Slack Webhook |
| **Microsoft Teams** | Outbound webhook | Settings → Notifications → Teams Webhook |
| **Email (Resend)** | HTTPS API | `RESEND_API_KEY` env var |
| **SMTP (fallback)** | SMTP | `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` env vars |

### Authentication & Identity
| System | Protocol | Env vars |
|---|---|---|
| **Google OAuth** | OAuth 2.0 | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| **GitHub OAuth** | OAuth 2.0 | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |
| **WorkOS SSO** | SAML/OIDC | `WORKOS_API_KEY`, `WORKOS_CLIENT_ID` |
| **Email/Password** | JWT + bcrypt | Built-in, no config |

### AI & Intelligence
| System | Protocol | Env vars |
|---|---|---|
| **Anthropic Claude** | HTTPS API | `ANTHROPIC_API_KEY` |
| **NVD (NIST)** | HTTPS API | Auto (no key required) |
| **CISA KEV** | HTTPS API | Auto (no key required) |
| **EPSS** | HTTPS API | Auto (no key required) |

### Data & Infrastructure
| System | Protocol | Env vars |
|---|---|---|
| **PostgreSQL** | asyncpg | `DATABASE_URL` |
| **Redis** | redis-py | `REDIS_URL` |
| **Sentry** | HTTPS SDK | `SENTRY_DSN` |

---

## Base URLs

| Environment | URL |
|---|---|
| Production backend | `https://glasswatch-production.up.railway.app` |
| Production frontend | `https://frontend-production-ef3e.up.railway.app` |
| API prefix | `/api/v1/` |
| Interactive docs | `https://glasswatch-production.up.railway.app/docs` |

---

## Authentication

### Bearer JWT (Standard)

```http
Authorization: Bearer <jwt_token>
```

Obtain a token:
```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "user@example.com", "password": "..."}
```

Response:
```json
{"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}
```

### API Key

```http
X-API-Key: <api_key>
```

Issued from the Settings → API Keys page. Useful for service-to-service calls and CI pipelines.

### Webhook Secret

```http
X-Webhook-Secret: <shared_secret>
```

Used for inbound scanner webhooks. Configure the secret in Settings → Connections per scanner.

### Demo Mode

No auth required in demo environments. Include `X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000` to target the demo tenant.

---

## Rate Limits

**Currently: none.** Glasswatch does not enforce API rate limits at the application layer. Railway's infrastructure provides basic DDoS protection.

Rate limiting is planned for v2 (per-tenant, per-endpoint buckets).

---

## Error Format

**Validation errors:**
```json
{
  "detail": [
    {"loc": ["body", "field_name"], "msg": "field required", "type": "missing"}
  ]
}
```

**Application errors:**
```json
{"detail": "Bundle not found"}
```

**HTTP status codes used:** `200`, `201`, `204`, `400`, `401`, `403`, `404`, `409`, `422`, `500`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | ✅ | JWT signing secret (min 32 chars, random) |
| `ANTHROPIC_API_KEY` | Optional | Enables AI agent + NLP rule parsing |
| `WORKOS_API_KEY` | Optional | Enables enterprise SSO |
| `WORKOS_CLIENT_ID` | Optional | WorkOS OAuth client ID |
| `SLACK_BOT_TOKEN` | Optional | Outbound Slack notifications |
| `SENTRY_DSN` | Optional | Error tracking |
| `ENV` | Optional | `development` / `staging` / `production` (default: `development`) |
| `BACKEND_CORS_ORIGINS` | Optional | Comma-separated allowed origins |

---

## Key API Endpoints by Domain

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Email/password login |
| POST | `/auth/demo` | Demo tenant token |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Current user info |
| POST | `/auth/logout` | Invalidate token |
| GET | `/auth/oauth/google` | Google OAuth redirect |
| GET | `/auth/oauth/github` | GitHub OAuth redirect |

### Vulnerabilities

| Method | Path | Description |
|---|---|---|
| GET | `/vulnerabilities` | List (filterable by severity, KEV, EPSS, etc.) |
| GET | `/vulnerabilities/{id}` | Single vulnerability detail |
| POST | `/vulnerabilities` | Create/import vulnerability |
| PATCH | `/vulnerabilities/{id}` | Update fields |
| GET | `/vulnerabilities/{id}/assets` | Assets affected by this CVE |
| POST | `/vulnerabilities/bulk-import` | Batch import from scanner output |

### Assets

| Method | Path | Description |
|---|---|---|
| GET | `/assets` | List assets (filter by exposure, type, tags) |
| POST | `/assets` | Register asset |
| GET | `/assets/{id}` | Asset detail with vulnerability summary |
| PATCH | `/assets/{id}` | Update asset metadata |
| DELETE | `/assets/{id}` | Remove asset |
| GET | `/assets/{id}/vulnerabilities` | Vulnerabilities for this asset |
| POST | `/assets/{id}/tags` | Apply tags |

### Goals

| Method | Path | Description |
|---|---|---|
| GET | `/goals` | List goals |
| POST | `/goals` | Create goal |
| GET | `/goals/{id}` | Goal detail with progress |
| PATCH | `/goals/{id}` | Update goal |
| POST | `/goals/{id}/optimize` | Run optimizer → generate bundles |
| GET | `/goals/{id}/progress` | Current progress metrics |

### Bundles

| Method | Path | Description |
|---|---|---|
| GET | `/bundles` | List bundles (filter by status) |
| POST | `/bundles` | Create bundle |
| GET | `/bundles/{id}` | Bundle detail with items |
| PATCH | `/bundles/{id}` | Update bundle |
| POST | `/bundles/{id}/approve` | Approve for deployment |
| POST | `/bundles/{id}/execute` | Trigger deployment |
| POST | `/bundles/{id}/rollback` | Rollback bundle |

### Rules

| Method | Path | Description |
|---|---|---|
| GET | `/rules` | List deployment rules |
| POST | `/rules` | Create rule |
| POST | `/rules/parse-nlp` | Parse plain English → structured rule |
| POST | `/rules/evaluate` | Dry-run: which rules fire for given assets/env |
| PATCH | `/rules/{id}` | Update rule |
| DELETE | `/rules/{id}` | Delete rule |

### Maintenance Windows

| Method | Path | Description |
|---|---|---|
| GET | `/maintenance-windows` | List windows |
| POST | `/maintenance-windows` | Create window |
| GET | `/maintenance-windows/{id}` | Window detail |
| PATCH | `/maintenance-windows/{id}` | Update window |
| DELETE | `/maintenance-windows/{id}` | Delete window |
| GET | `/maintenance-windows/environments` | Distinct environments |

### AI Agent

| Method | Path | Description |
|---|---|---|
| POST | `/agent/chat` | Send message, get response + actions |

Request:
```json
{"message": "What needs my attention right now?", "context": {}}
```

Response:
```json
{
  "response": "You have 3 critical KEV vulnerabilities on internet-facing assets...",
  "actions_taken": ["Queried vulnerability database", "Checked bundle status"],
  "suggested_actions": ["View critical KEV vulnerabilities", "Approve pending bundle"]
}
```

### Settings

| Method | Path | Description |
|---|---|---|
| GET | `/settings` | All tenant settings |
| PATCH | `/settings` | Update settings |
| POST | `/settings/test-connection` | Test integration connectivity |

---

## Webhook Endpoints

### Tenable

```
POST /api/v1/webhooks/scanner/tenable
X-Webhook-Secret: <secret>
Content-Type: application/json
```

Example payload:
```json
{
  "type": "SCAN_COMPLETED",
  "scan_id": "scan-abc123",
  "asset_ip": "10.0.0.50",
  "asset_hostname": "db-prod-01",
  "findings": [
    {
      "plugin_id": "97994",
      "cve": "CVE-2021-44228",
      "severity": "CRITICAL",
      "cvss_score": 10.0,
      "description": "Apache Log4Shell...",
      "solution": "Upgrade to Log4j 2.16.0+"
    }
  ]
}
```

### Qualys

```
POST /api/v1/webhooks/scanner/qualys
X-Webhook-Secret: <secret>
Content-Type: application/json
```

Example payload:
```json
{
  "ServiceRequest": {
    "data": {
      "HostAsset": {
        "id": "12345",
        "address": "10.0.0.51",
        "hostname": "web-prod-02",
        "vulnerabilities": {
          "list": [
            {
              "HostAssetVuln": {
                "qid": "91360",
                "cveId": "CVE-2022-0847",
                "severity": 5,
                "firstFound": "2022-03-15"
              }
            }
          ]
        }
      }
    }
  }
}
```

### Rapid7

```
POST /api/v1/webhooks/scanner/rapid7
X-Webhook-Secret: <secret>
Content-Type: application/json
```

Example payload:
```json
{
  "event_type": "ASSET_VULNERABILITY_FOUND",
  "asset": {
    "id": "r7-asset-789",
    "ip": "10.0.0.52",
    "hostname": "internal-api-01",
    "os": "Ubuntu 22.04"
  },
  "vulnerabilities": [
    {
      "id": "r7-vuln-456",
      "cve": "CVE-2023-23397",
      "cvss_score": 9.8,
      "title": "Microsoft Outlook NTLM Elevation of Privilege",
      "severity": "CRITICAL",
      "solution": "Apply MS23-023 patch"
    }
  ]
}
```

### Slack Events (inbound)

```
POST /api/v1/slack/events
X-Slack-Signature: v0=<hmac>
Content-Type: application/json
```

### Jira Webhooks (inbound)

```
POST /api/v1/connections/jira/webhook
X-Webhook-Secret: <secret>
Content-Type: application/json
```

Example — issue transitioned to Done (closes bundle step):
```json
{
  "webhookEvent": "jira:issue_updated",
  "issue": {
    "key": "SEC-451",
    "fields": {
      "status": {"name": "Done"},
      "summary": "Patch CVE-2021-44228 on db-prod-01"
    }
  }
}
```

---

## Pagination

List endpoints support `skip` (offset) and `limit` parameters:

```
GET /api/v1/vulnerabilities?skip=0&limit=50&severity=CRITICAL
```

Default `limit` is 50. Maximum is 500.

---

## Filtering

Common filter parameters across list endpoints:

| Parameter | Type | Notes |
|---|---|---|
| `severity` | string | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `kev_only` | bool | Filter to KEV-listed only |
| `status` | string | Bundle/goal status |
| `environment` | string | Asset/window environment |
| `tag` | string | Filter by tag (repeatable) |
| `search` | string | Full-text search |
| `skip` | int | Pagination offset |
| `limit` | int | Page size (max 500) |
