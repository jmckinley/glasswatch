# Glasswatch

**AI-driven patch management for enterprise security teams.**

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://glasswatch-production.up.railway.app)
[![Deployed on Railway](https://img.shields.io/badge/deployed-Railway-blueviolet)](https://glasswatch-production.up.railway.app)

**[Live Demo](https://frontend-production-ef3e.up.railway.app)** · **[API Docs](https://glasswatch-production.up.railway.app/docs)** · **[User Guide](docs/USER_GUIDE.md)** · **[Implementation Guide](docs/IMPLEMENTATION_GUIDE.md)**

---

## Quick Install (Self-Hosted)

```bash
curl -fsSL https://raw.githubusercontent.com/jmckinley/glasswatch/main/install.sh | bash
```

That's it. Requires [Docker](https://docs.docker.com/get-docker/). Up and running in under 5 minutes.

**Full installation guide:** [INSTALL.md](INSTALL.md) · **Advanced setup:** [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)

---

## What It Is

Glasswatch converts vulnerability chaos into organized, evidence-backed patch operations. Instead of drowning in CVE queues, teams define business objectives — "be Glasswing-ready by July 1" — and Glasswatch builds the optimal patching plan to get there.

**Live demo:** https://frontend-production-ef3e.up.railway.app
**API docs:** https://glasswatch-production.up.railway.app/docs

---

## Key Features

- **AI Scoring** — 8-factor vulnerability scoring (CVSS, EPSS, KEV, asset exposure, runtime data, patch age, exploit availability, business criticality)
- **Goal-Based Optimization** — Express outcomes, not tasks. Glasswatch generates maintenance bundles to hit your target date and risk threshold
- **Bundle Execution** — Group patches into scheduled maintenance windows with approval workflows, rollback support, and audit trails
- **NLP Rules** — Write deployment rules in plain English: "Block deployments on Fridays after 3pm in production"
- **AI Agent** — Ask questions and take actions in plain language from the in-app assistant
- **Scanner Webhooks** — Ingest findings from Tenable, Qualys, and Rapid7 in real time
- **Asset Intelligence** — Asset groups, patch coverage matrix, stale asset detection, per-asset risk breakdown
- **Compliance Dashboard** — BOD 22-01, SOC 2, and PCI DSS posture cards with MTTP metrics and SLA tracking
- **Notifications** — Real-time alerts via Slack, Teams, and email; configurable alert rules by event type
- **CSV Import** — Bulk import vulnerabilities and assets from any scanner via CSV
- **SIEM/CMDB API** — Export vulnerabilities and assets in JSON or CSV for downstream integration
- **SSO & RBAC** — WorkOS-backed SSO, multi-tenant, role-based access

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), async SQLAlchemy |
| Database | PostgreSQL + Redis |
| Auth | JWT + Google/GitHub OAuth + WorkOS SSO |
| Hosting | Railway (backend + frontend + DB) or self-hosted Docker |

---

## Integrations

### Vulnerability Scanners
| Scanner | Integration type |
|---|---|
| **Tenable** (Nessus / Tenable.io) | Inbound webhook + API key auth |
| **Qualys** | Inbound webhook + credential auth |
| **Rapid7 InsightVM** | Inbound webhook + API key auth |
| **CSV Import** | Manual upload at `/import` (any scanner export) |

### Ticketing & ITSM
| System | Integration type |
|---|---|
| **Jira** | Bidirectional webhook — bundle → issue, issue closed → bundle patched |
| **ServiceNow** | Webhook integration for change management |

### Notifications & Messaging
| System | Integration type |
|---|---|
| **Slack** | Incoming webhook for patch alerts, SLA warnings, bundle events |
| **Microsoft Teams** | Incoming webhook connector |
| **Email (Resend)** | Transactional email — invite links, weekly digest, alert notifications |
| **SMTP** | Fallback email delivery |

### Authentication & Identity
| System | Integration type |
|---|---|
| **Google OAuth** | Login with Google (OAuth 2.0) |
| **GitHub OAuth** | Login with GitHub |
| **WorkOS SSO** | Enterprise SAML/OIDC (Okta, Azure AD, Google Workspace) |
| **Email/Password** | Native auth with bcrypt hashing |

### AI & Intelligence
| System | Integration type |
|---|---|
| **Anthropic Claude** | AI assistant, NLP rule creation, risk analysis |
| **NVD (NIST)** | CVE enrichment — CVSS scores, description, references |
| **CISA KEV** | Known Exploited Vulnerabilities feed |
| **EPSS** | Exploit Prediction Scoring System for prioritization |

### Operations
| System | Integration type |
|---|---|
| **Sentry** | Error tracking and alerting |
| **PostgreSQL** | Primary data store |
| **Redis** | Caching, rate limiting, session management |

---

## Getting Started (Demo)

1. Open https://frontend-production-ef3e.up.railway.app
2. Click **"Try Demo"** — no signup required
3. Explore the dashboard, create a goal, or ask the AI assistant a question

---

## Architecture Overview

The frontend (Next.js) calls the backend REST API (`/api/v1/`, 153 endpoints). The backend handles scoring, rule evaluation, bundle scheduling, and AI agent logic against a PostgreSQL database. External scanners push findings via webhook endpoints in real time.

```
[Browser]
    → [Next.js Frontend (Railway)]
    → [FastAPI Backend (Railway)]
    → [PostgreSQL (Railway)]

[Tenable / Qualys / Rapid7]
    → [Webhook Endpoints /api/v1/webhooks/scanner/*]
    → [FastAPI Backend]
    → [PostgreSQL]
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

---

## Roadmap — Next Phase

Glasswatch is functional end-to-end today. Here's what's on deck for the next major phases:

### Phase 2 — Enterprise Readiness (Q3 2026)
- **WorkOS SSO** — SAML/OIDC single sign-on for enterprise identity providers (Okta, Azure AD, Google Workspace)
- **RBAC enforcement** — Hard role gates (Viewer/Analyst/Operator/Admin) enforced at the API layer, not just the UI
- **Audit log** — Immutable, exportable record of every user action (who approved what, when, from which IP) for SOC 2 evidence
- **Evidence packages** — One-click export of patch records, approval trails, and compliance snapshots formatted for auditors
- **Multi-region deployment** — EU and APAC hosting for data residency requirements

### Phase 3 — Deeper Intelligence (Q4 2026)
- **Live NVD/EPSS sync** — Automatic enrichment of new CVEs as they're published, without manual import
- **Threat intel feeds** — Direct integrations with VulnCheck, GreyNoise, and Shodan for real-time exploit signal
- **Asset auto-discovery** — Passive network scanning to find assets not in any scanner (rogue hosts, shadow IT)
- **Patch impact prediction** — ML model trained on historical data to predict which patches are likely to cause issues
- **Business context mapping** — Tie assets to revenue-generating services for true business-risk scoring

### Phase 4 — Workflow Automation (2027)
- **Jira/ServiceNow native sync** — Two-way ticket sync: Glasswatch bundle → ticket, ticket closed → bundle item marked patched
- **Auto-remediation playbooks** — For low-risk patches on non-production assets, trigger automated patch + verify cycles
- **Slack/Teams bot** — Full approval and status workflow without leaving chat
- **API-first integrations** — Webhooks out for every event (new KEV, bundle completed, SLA breached) for customer automation
- **Mobile app** — Approval workflows and alert triage on iOS and Android

### Always-on improvements
- Performance at scale (100k+ vulnerabilities, 10k+ assets)
- Deeper AI agent capabilities (natural language queries over all your data)
- More compliance frameworks (FedRAMP, HIPAA, ISO 27001, NIST CSF)
- Community-contributed scanner integrations

---

## For Alpha Customers

Glasswatch is in active alpha development. All sprints through Sprint 23 are complete. The live demo at [https://frontend-production-ef3e.up.railway.app](https://frontend-production-ef3e.up.railway.app) reflects the current state — click **Try Demo** to explore without signing up.

**What to expect during alpha:**
- Core functionality (scoring, goals, bundles, rules, compliance, notifications) is fully operational
- Some UI rough edges and in-progress features — we ship iteratively
- Demo data resets periodically
- Performance on large datasets (10k+ vulnerabilities) is functional but not yet optimized

**How to give feedback:**
Email [support@glasswatch.io](mailto:support@glasswatch.io) with what you found, what you expected, and what environment you're on. Screenshots are helpful. Bug reports and feature requests both welcome.

---

## Links

- **Live demo:** https://frontend-production-ef3e.up.railway.app
- **API docs (Swagger):** https://glasswatch-production.up.railway.app/docs
- **User Guide:** [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Implementation Guide:** [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Systems & integrations:** [docs/SYSTEMS.md](docs/SYSTEMS.md)
- **FAQ:** [docs/FAQ.md](docs/FAQ.md)

---

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and fill in `DATABASE_URL` and `SECRET_KEY`.

Required env vars: `DATABASE_URL`, `SECRET_KEY`
Optional: `ANTHROPIC_API_KEY` (AI features), `WORKOS_API_KEY` (SSO)
