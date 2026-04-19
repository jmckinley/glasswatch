# Glasswatch

> The patch decision platform for the post-Mythos vulnerability management era

**We don't find vulnerabilities — we decide what to do about them.**

## Overview

Glasswatch is an AI-powered patch decision platform that transforms the chaos of vulnerability management into strategic, optimized patch operations. Built for the Glasswing disclosure era (July 2026), where thousands of critical vulnerabilities will be released simultaneously.

### Core Features

- **Goal-Based Optimization**: Define objectives ("patch critical CVEs in 3 weeks"), get optimized plans
- **Business Impact Modeling**: Prioritize based on revenue/hour, SLA penalties, and regulatory risk
- **Runtime Intelligence**: Know if vulnerable code actually executes (via Snapper integration)
- **Patch Weather**: Community deployment health scores (our network effect moat)
- **Multi-Cloud Native**: AWS, GCP, Azure support from day one
- **Kubernetes Operator**: Declarative patch management with CRDs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: PLATFORM (Multi-Tenant Infrastructure)           │
│  Event Bus · Per-Tenant DB · Audit Log                     │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: ORCHESTRATION & SURFACES                          │
│  Web App · ITSM Push · Patch Weather API · Attestation     │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: GRAPH & SCORING                                   │
│  Vuln × Asset Graph · Prioritization · Bundling · Goals    │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: NORMALIZATION & ENRICHMENT                        │
│  Dedupe · SBOE Builder · LLM Extractors                    │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: INGESTION                                         │
│  CVE/KEV/EPSS/GHSA · Cloud APIs · Snapper · Agents        │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- Docker & Kubernetes (for production)

### Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Database
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:16
docker run -d -p 7687:7687 memgraph/memgraph-platform
```

### Run Tests

```bash
# All tests
./scripts/run_all_tests.sh

# Unit tests only
cd backend && pytest tests/unit/

# Integration tests
cd backend && pytest tests/integration/

# E2E tests
cd frontend && npm run test:e2e
```

## API Documentation

Once running, visit:
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 16 (OLTP), Memgraph (graph)
- **Event Bus**: Redpanda (Kafka-compatible)
- **Cache**: Redis/Dragonfly
- **ML/AI**: Claude Opus 4.7 via Anthropic API
- **Infrastructure**: Kubernetes, Terraform, AWS/GCP/Azure

## Project Status

Building towards July 2026 Glasswing disclosure launch. Currently in Sprint 10 of 11.

### Completed
- ✅ Core prioritization engine
- ✅ Goal-based optimization
- ✅ Asset discovery (cloud + CMDB)
- ✅ Enhanced goals with business impact
- ✅ Kubernetes operator
- ✅ Multi-cloud deployment
- ✅ Testing infrastructure

### In Progress
- 🔄 Production hardening
- 🔄 Beta customer onboarding
- 🔄 Glasswing readiness dashboard

## Contributing

This is currently a private repository. For access, contact john@greatfallsventures.com.

## Security

For security issues, please email security@mckinleylabs.com. Do not open public issues.

## License

Proprietary - McKinley Labs LLC © 2026

---

**Built for the Mythos era. Ready for Glasswing.**