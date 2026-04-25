# Glasswatch — Architecture

## Overview

Glasswatch is a three-tier web application: a Next.js frontend, a FastAPI backend, and a PostgreSQL database, all hosted on Railway. External scanner integrations push vulnerability data via webhook endpoints.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT SIDE                             │
│                                                                 │
│   [Browser]                                                     │
│       │  HTTPS                                                  │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND (Railway)                  │
│                                                                 │
│   Next.js 15 · TypeScript · Tailwind CSS                        │
│   App Router · Server + Client Components                       │
│   https://frontend-production-ef3e.up.railway.app               │
│       │                                                         │
│       │  REST API calls  /api/v1/*                              │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (Railway)                   │
│                                                                 │
│   FastAPI · Python 3.11 · async SQLAlchemy · Pydantic v2        │
│   https://glasswatch-production.up.railway.app                  │
│                                                                 │
│   153 endpoints across 25 routers                               │
│   Services: scoring · deployment · rule_engine · simulator      │
│             notification · approval · reporting · backup        │
│       │                                                         │
│       │  async SQLAlchemy                                       │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (Railway managed)                  │
│                                                                 │
│   Primary data store. Alembic migrations.                       │
│   Connection pooling via asyncpg.                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              EXTERNAL SCANNER INTEGRATIONS                      │
│                                                                 │
│   [Tenable]                                                     │
│   [Qualys]    ──── HTTPS webhooks ──→  /api/v1/webhooks/        │
│   [Rapid7]                             scanner/*                │
│                                            │                   │
│                                            ▼                   │
│                                    [FastAPI Backend]            │
│                                            │                   │
│                                            ▼                   │
│                                       [PostgreSQL]              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend

| Item | Detail |
|---|---|
| Framework | Next.js 15 with App Router |
| Language | TypeScript |
| Styling | Tailwind CSS (dark theme, `bg-gray-900` base) |
| State | React hooks + local fetch via `/src/lib/api.ts` |
| Auth | JWT stored in `localStorage` (`glasswatch_token`) |
| Hosting | Railway (Dockerfile.frontend) |

Key pages under `src/app/(dashboard)/`:
- `/` — Dashboard (risk summary, activity feed)
- `/vulnerabilities` — Searchable CVE list with scoring breakdown
- `/assets` — Asset inventory with exposure and criticality
- `/goals` — Goal creation and progress tracking
- `/bundles` — Bundle list with approval workflows
- `/schedule` — Maintenance window calendar
- `/rules` — NLP-powered deployment rules
- `/settings` — Integrations, notifications, team
- `/help` — In-app help center and FAQ

---

## Backend

| Item | Detail |
|---|---|
| Framework | FastAPI (async) |
| Language | Python 3.11 |
| ORM | SQLAlchemy 2.x async (`select()` pattern) |
| Validation | Pydantic v2 |
| Auth | JWT (HS256) + demo tenant fallback |
| Migrations | Alembic |
| Hosting | Railway (Dockerfile.prod) |

### Key Services (`backend/services/`)

| Service | Purpose |
|---|---|
| `scoring.py` | 8-factor vulnerability risk scoring |
| `deployment_service.py` | Bundle execution state machine |
| `rule_engine.py` | Deployment rule evaluation (allow/warn/block) |
| `simulator_service.py` | What-if scenario simulation |
| `notification_service.py` | Slack/Teams/email alert dispatch |
| `approval_service.py` | Multi-stage approval workflows |
| `reporting.py` | Snapshot generation and export |

### Router Map (`backend/api/v1/`)

| Router | Prefix |
|---|---|
| auth | `/api/v1/auth` |
| vulnerabilities | `/api/v1/vulnerabilities` |
| assets | `/api/v1/assets` |
| goals | `/api/v1/goals` |
| bundles | `/api/v1/bundles` |
| maintenance_windows | `/api/v1/maintenance-windows` |
| rules | `/api/v1/rules` |
| agent | `/api/v1/agent` |
| simulator | `/api/v1/simulator` |
| dashboard | `/api/v1/dashboard` |
| connections | `/api/v1/connections` |
| settings | `/api/v1/settings` |
| tags | `/api/v1/tags` |
| notifications | (various `/api/v1/notifications/*`) |
| webhooks | `/api/v1/webhooks/scanner/*` |

---

## Data Model

```
Tenant
  ├── Users (role: admin/analyst/viewer)
  ├── Assets (exposure: INTERNET/INTRANET/ISOLATED)
  │     └── AssetVulnerability (many-to-many join)
  ├── Vulnerabilities (CVE/GHSA/OSV identifiers)
  ├── Goals
  │     └── Bundles
  │           └── BundleItems (vulnerability + asset pairs)
  ├── MaintenanceWindows
  ├── DeploymentRules
  ├── Connections (Tenable, Qualys, Slack, Jira, etc.)
  ├── Tags (namespace:value)
  ├── Notifications
  └── AuditLogs
```

---

## Authentication

| Method | Use Case |
|---|---|
| JWT Bearer token | Standard user sessions |
| Demo tenant fallback | No-auth development / demo mode |
| Google/GitHub OAuth | Individual sign-in |
| WorkOS SSO | Enterprise SAML/OIDC |
| API Key (`X-API-Key`) | Service-to-service, webhooks |

Tokens are issued at `/api/v1/auth/login` and `/api/v1/auth/demo`.

---

## External Integrations

| Integration | Type | Direction |
|---|---|---|
| Tenable | Scanner | Inbound webhook |
| Qualys | Scanner | Inbound webhook |
| Rapid7 | Scanner | Inbound webhook |
| Slack | Notifications | Outbound |
| Microsoft Teams | Notifications | Outbound |
| Jira | Ticketing | Outbound |
| ServiceNow | ITSM | Outbound |
| VulnCheck | Threat intel | Outbound (enrichment) |
| Snapper | Runtime analysis | Outbound (scoring input) |
| Anthropic Claude | AI agent | Outbound (optional) |

---

## External API Simulators (Dev/Testing)

For development and integration testing without real scanner credentials, Glasswatch includes a set of mock servers that replicate the APIs of external systems.

| Detail | Value |
|---|---|
| Enabled by | `SIMULATOR_MODE=true` (env var) |
| Port | 8099 |
| Systems simulated | Tenable, Qualys, Rapid7, and 8 additional systems (11 total) |
| Purpose | Push synthetic scan payloads into Glasswatch without external accounts |

The simulators are **not** part of the production API surface. They start alongside the backend when `SIMULATOR_MODE=true` and are intended for local development and CI environments only. See [docs/SIMULATORS.md](SIMULATORS.md) for the full list of supported systems and usage.

---

## Testing

| Suite | Count | Runner |
|---|---|---|
| Backend unit + integration tests | 479 | pytest |
| Frontend component tests | 37 | React Testing Library |
| **Total** | **516** | |

Key test files:
- `backend/tests/unit/test_scoring.py` — 8-factor scoring algorithm
- `backend/tests/unit/test_audit_service.py` — audit log service
- `backend/tests/unit/test_external_api_simulators.py` — simulator endpoints (89 tests)
- `backend/tests/integration/test_audit_log_api.py` — audit log API endpoints
- `backend/tests/integration/test_audit_hooks.py` — audit hook integration

See [docs/TEST_PLAN.md](TEST_PLAN.md) for full coverage details.

---

## Not Yet Implemented (Planned)

- Message queue (Celery + Redis or similar) — currently synchronous
- Worker pool for long-running scoring jobs
- Multi-region deployment
- Read replicas for heavy analytics queries
