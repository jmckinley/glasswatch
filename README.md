# PatchGuide.ai - Intelligent Patch Optimization Platform

**Transform business objectives into optimized patch schedules.**

PatchGuide.ai is the first AI-powered patch management platform that understands your business goals. Instead of just prioritizing vulnerabilities by severity, PatchGuide uses constraint solving to create optimal patching schedules that balance risk reduction with operational reality.

## 🎯 The Problem

Security teams are drowning in vulnerabilities:
- 20,000+ CVEs published yearly
- Average enterprise: 2,000+ vulnerabilities
- 75% never get patched
- No clear prioritization beyond CVSS scores
- Business impact disconnected from technical decisions

## 💡 Our Solution

**AI-driven optimization**: Tell PatchGuide your business objective, and it creates the optimal patch schedule.

Examples:
- "Make us audit-ready by July 1st"
- "Reduce internet-facing critical vulnerabilities by 80%"
- "Achieve SOC 2 compliance for Q3 audit"

## 🚀 Key Features

### 1. **Intelligent Scoring** (Our Differentiator)
- 8-factor algorithm beyond just CVSS
- **Snapper runtime integration**: ±25 points based on actual code execution
- EPSS probability scoring
- KEV catalog priority boost
- Asset criticality and exposure weighting

### 2. **Constraint Solver Optimization**
- OR-Tools powered scheduling engine
- Balances risk, downtime, and deadlines
- Groups related patches for efficiency
- Respects maintenance windows
- No competitor has true goal-based optimization

### 3. **Patch Weather™** (Network Effect Moat)
- Community-driven patch success metrics
- "Is this patch safe to deploy?"
- Rollback rates and vendor acknowledgments
- Only Glasswatch has this aggregated data

### 4. **AI Assistant Integration**
- Natural language goal creation
- "What should I patch this week?" insights
- Anomaly detection and alerts
- Predictive risk analysis

### 5. **Business Context Integration**
- Risk profiles: Conservative, Balanced, Aggressive
- Compliance deadline tracking
- Cost modeling for downtime
- Executive-friendly dashboards

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js 15    │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   Frontend      │     │   Backend       │     │   Database      │
│   (Dark Theme)  │     │   (Async)       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   OR-Tools      │     │     Redis       │
                        │   Optimizer     │     │     Cache       │
                        └─────────────────┘     └─────────────────┘
```

## 🚦 Current Status (Sprint 0 - 60% Complete)

### ✅ Completed
- **Database Models**: All 8 core models with relationships
- **Scoring Engine**: Complete with Snapper integration
- **APIs**: Vulnerabilities, Assets, Goals (with optimization)
- **Goal Optimization**: Constraint solver implementation
- **Frontend Scaffold**: Next.js 15 with dark theme dashboard

### 🔄 In Progress
- Docker Compose setup
- Authentication (WorkOS integration)
- Webhook system
- AI Assistant

### 📋 TODO
- ITSM integrations (ServiceNow, Jira)
- Patch Weather data collection
- Notification system
- Multi-tenant deployment

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, OR-Tools
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS 4
- **Database**: PostgreSQL (primary), Redis (cache)
- **Infrastructure**: Docker, Kubernetes-ready
- **AI**: OpenAI GPT-4 for natural language goals

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker

```bash
# Clone the repository
git clone https://github.com/jmckinley/patchai.git
cd patchai

# Start all services
docker-compose up

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### Local Development

#### Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

## 📊 API Examples

### Create a Goal
```bash
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -d '{
    "name": "Glasswing Readiness",
    "type": "compliance_deadline",
    "target_date": "2024-07-01T00:00:00Z",
    "risk_tolerance": "balanced",
    "max_vulns_per_window": 20
  }'
```

### Optimize the Schedule
```bash
curl -X POST http://localhost:8000/api/v1/goals/{goal_id}/optimize \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -d '{
    "max_future_windows": 12
  }'
```

## 🔐 Security

- Multi-tenant isolation at every layer
- Encryption at rest (AWS KMS)
- Row-level security in PostgreSQL
- SOC 2 compliant architecture from day one
- API authentication via WorkOS (production)

## 🤝 Contributing

We're in early development. For now:
1. Fork the repo
2. Create a feature branch
3. Submit a PR with clear description

## 📄 License

Proprietary - © 2024 PatchGuide, Inc.

---

**Built with ❤️ by the PatchGuide team**

*"Stop patching blind. Start patching smart."*