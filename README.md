# Glasswatch

**AI-driven patch management for enterprise security teams.**

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://glasswatch-production.up.railway.app)
[![Deployed on Railway](https://img.shields.io/badge/deployed-Railway-blueviolet)](https://glasswatch-production.up.railway.app)

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
- **SSO & RBAC** — WorkOS-backed SSO, multi-tenant, role-based access

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), async SQLAlchemy |
| Database | PostgreSQL (Railway managed) |
| Auth | JWT + Google/GitHub OAuth + WorkOS SSO |
| Hosting | Railway (backend + frontend + DB) |

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

## Links

- **Live demo:** https://frontend-production-ef3e.up.railway.app
- **API docs (Swagger):** https://glasswatch-production.up.railway.app/docs
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
