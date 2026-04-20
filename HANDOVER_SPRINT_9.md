# Sprint 9 → Sprint 10 Handover

**Date:** 2026-04-20  
**Sprint 9 Complete:** Asset Discovery (10 scanners)  
**Sprint 10 Starting:** Production Hardening  
**Progress:** 82% (9/11 sprints complete)  
**Deadline:** July 2026 (Glasswing disclosure)

---

## Sprint 9 Completion Summary

### What We Built

**Asset Discovery System** - Production-ready v1.0 with:
- 10 scanners (AWS, Azure, GCP, CloudQuery, Trivy, Kubescape, Nmap, ServiceNow, Jira, Device42)
- Auto-sync scheduler (APScheduler with interval + cron support)
- Full-featured React dashboard
- Pluggable scanner architecture
- Asset deduplication logic
- Database persistence (create/update)
- Comprehensive documentation (4 guides, ~50KB)

**Delivered Code:**
- Backend: 13 files (~10,000 lines)
  - `backend/api/v1/discovery.py` - API endpoints
  - `backend/services/discovery/` - 10 scanner implementations
  - `backend/services/discovery_orchestrator.py` - Scan orchestration
  - `backend/services/discovery_scheduler.py` - Auto-sync scheduler
- Frontend: 4 files (~2,000 lines)
  - `frontend/src/app/dashboard/discovery/page.tsx` - Main dashboard
  - `frontend/src/components/discovery/` - Scanner cards, results table, scheduler
- Documentation: 3 guides
  - `ASSET_DISCOVERY_QUICKSTART.md`
  - `DISCOVERY_IMPLEMENTATION_SUMMARY.md`
  - `DISCOVERY_COMPLETE_SUMMARY.md`

**GitHub Status:**
- Branch: `main`
- Last commit: `887a73f` (Sprint 9 handover + TODO update)
- All code pushed and committed
- No uncommitted changes

### Key Achievements

1. **Full scanner coverage** - Cloud (AWS/Azure/GCP), containers (Trivy), K8s (Kubescape), network (Nmap), CMDB (3 integrations)
2. **Auto-sync scheduler** - Keep inventory fresh with configurable intervals or cron expressions
3. **Production-ready architecture** - Pluggable scanners, parallel execution, deduplication, error handling
4. **Clean documentation** - 4 comprehensive guides for users, operators, and developers

### Technical Highlights

**Scanner Architecture:**
```python
class BaseScanner:
    async def scan(self, config: Dict[str, Any]) -> List[AssetData]
    def is_available(self) -> bool
    def get_metadata() -> ScannerMetadata
```

**Deduplication Logic:**
- Asset identification: hostname/instance ID/IP/MAC
- Merge logic: latest data wins, combine IPs/tags
- Provider precedence: CMDB > Cloud > Network

**Auto-Sync:**
- Interval-based (every N seconds)
- Cron-based (e.g., "0 2 * * *")
- Per-scanner scheduling
- Timezone support

---

## Sprint 10: Production Hardening

### Goals

1. **Authentication & SSO** - WorkOS integration with RBAC
2. **Approval workflows** - Multi-level approvals for patch bundles
3. **Rollback tracking** - Pre-patch snapshots + automated rollback
4. **Patch simulator** - Impact prediction + dry-run mode
5. **Team collaboration** - Comments, @mentions, activity feed
6. **Testing & QA** - Unit tests (70%+ coverage), integration tests, security audit

### Priority Order

**Week 1 (HIGH PRIORITY):**
1. Authentication & SSO (WorkOS)
2. Approval workflows
3. Testing infrastructure (unit + integration tests)

**Week 2 (MEDIUM PRIORITY):**
4. Rollback tracking
5. Patch simulator
6. Team collaboration features
7. Security audit

### Success Criteria

- [ ] SSO login working (Google, Microsoft, Okta)
- [ ] Multi-tenant authentication enforced
- [ ] RBAC protecting API endpoints
- [ ] Approval workflow functional (submit → approve → execute)
- [ ] 70%+ test coverage on backend services
- [ ] Integration tests for critical paths
- [ ] Security scan passing (OWASP Top 10)
- [ ] Pre-patch snapshots + rollback working
- [ ] Patch simulator generating impact reports
- [ ] Comments + @mentions functional

---

## Current State

### What's Working

- **Core platform** - FastAPI backend, Next.js frontend, PostgreSQL database
- **Scoring algorithm** - 8-factor prioritization with Snapper runtime integration
- **Goal-based optimization** - OR-Tools constraint solver
- **Asset discovery** - 10 scanners with auto-sync
- **APIs** - Vulnerabilities, Assets, Goals, Bundles, Maintenance Windows, Discovery
- **Frontend** - Dashboard, Goals, Vulnerabilities, Schedule, Discovery pages
- **Notifications** - Slack, Teams, Email
- **AI Assistant** - Chat interface with natural language commands
- **Executive reporting** - PDF/PowerPoint generation

### What's Not Working (Yet)

- **Authentication** - Placeholder only, no real SSO
- **Approvals** - No workflow system
- **Rollback** - No pre-patch snapshots or automated rollback
- **Simulator** - No impact prediction tool
- **Collaboration** - No comments or @mentions
- **Tests** - Minimal test coverage (~10%)
- **Security** - No audit or penetration testing

### Technical Stack

**Backend:**
- FastAPI + Uvicorn
- SQLAlchemy (async) + Alembic
- PostgreSQL 15 + asyncpg
- Redis 7 (caching)
- OR-Tools (optimization)
- APScheduler (background jobs)
- WorkOS SDK (SSO - ready to integrate)

**Frontend:**
- Next.js 15 + React
- TypeScript
- Tailwind CSS 4
- MUI Components
- Axios (API client)

**Infrastructure:**
- Docker Compose
- PostgreSQL 15
- Redis 7
- Health checks
- Multi-tenant architecture

---

## Sprint 10 Implementation Plan

### Phase 1: Authentication & SSO (Days 1-3)

**WorkOS Integration:**
1. Create WorkOS account + organization
2. Configure SSO providers (Google, Microsoft, Okta)
3. Add WorkOS SDK to backend (`pip install workos`)
4. Implement OAuth callback handler
5. Session management (JWT tokens)
6. User provisioning (auto-create users on first login)

**RBAC System:**
1. Define roles: Admin, Manager, Analyst, Viewer
2. Create `Role` and `Permission` models
3. Add role assignments to `User` model
4. Implement permission decorators for API endpoints
5. Frontend role checks (show/hide features)

**Audit Logging:**
1. Create `AuditLog` model (user, action, timestamp, metadata)
2. Add logging decorators to API endpoints
3. Audit log API (GET /api/v1/audit-logs)
4. Frontend audit log viewer

### Phase 2: Approval Workflows (Days 4-5)

**Models:**
```python
class ApprovalRequest:
    id: UUID
    bundle_id: UUID
    requester_id: UUID
    status: Enum[pending, approved, rejected]
    risk_level: Enum[low, medium, high, critical]
    approvers: List[UUID]
    approval_chain: List[ApprovalStep]
    created_at: datetime
    approved_at: Optional[datetime]
    
class ApprovalStep:
    id: UUID
    request_id: UUID
    approver_id: UUID
    status: Enum[pending, approved, rejected]
    comments: str
    approved_at: Optional[datetime]
```

**API Endpoints:**
- POST /api/v1/approvals (create approval request)
- GET /api/v1/approvals (list pending approvals)
- POST /api/v1/approvals/{id}/approve (approve)
- POST /api/v1/approvals/{id}/reject (reject)

**Frontend:**
- Approval inbox page
- Approval request creation modal
- Quick approve/reject buttons
- Approval history view

**Notifications:**
- Email/Slack/Teams on approval request
- Reminder emails (after 24h, 48h)
- Status updates (approved, rejected)

### Phase 3: Testing Infrastructure (Days 6-7)

**Unit Tests:**
```
backend/tests/
├── unit/
│   ├── test_scoring.py
│   ├── test_optimization.py
│   ├── test_discovery.py
│   ├── test_approval_workflows.py
│   └── test_authentication.py
├── integration/
│   ├── test_api_vulnerabilities.py
│   ├── test_api_assets.py
│   ├── test_api_goals.py
│   ├── test_api_approvals.py
│   └── test_discovery_workflow.py
└── conftest.py (shared fixtures)
```

**Coverage Goals:**
- Scoring service: 80%+
- Optimization service: 80%+
- Discovery orchestrator: 70%+
- API endpoints: 70%+
- Overall: 70%+

**Tools:**
- pytest (test runner)
- pytest-cov (coverage)
- pytest-asyncio (async tests)
- httpx (API testing)
- pytest-mock (mocking)

### Phase 4: Rollback Tracking (Days 8-9)

**Models:**
```python
class PatchSnapshot:
    id: UUID
    bundle_id: UUID
    asset_id: UUID
    snapshot_type: Enum[pre_patch, post_patch]
    system_state: JSON  # packages, configs, services
    created_at: datetime
    
class RollbackProcedure:
    id: UUID
    bundle_id: UUID
    asset_id: UUID
    trigger: Enum[manual, automated, health_check_failed]
    status: Enum[pending, in_progress, completed, failed]
    executed_at: datetime
```

**Workflow:**
1. Pre-patch: Capture system state (packages, configs, services)
2. Execute patch
3. Post-patch: Health checks (service status, connectivity, metrics)
4. If health check fails → Automated rollback
5. If manual trigger → Rollback to pre-patch snapshot

### Phase 5: Patch Simulator (Day 10)

**Features:**
- Dependency analysis (what else uses this package?)
- Service impact (which services will restart?)
- Downtime estimation (based on historical data)
- Risk assessment (failure probability, blast radius)
- Dry-run mode (simulated execution with validation)

**API:**
- POST /api/v1/simulator/predict (impact prediction)
- POST /api/v1/simulator/dry-run (simulated execution)

### Phase 6: Team Collaboration (Days 11-12)

**Comments System:**
```python
class Comment:
    id: UUID
    entity_type: Enum[asset, vulnerability, bundle]
    entity_id: UUID
    user_id: UUID
    content: str
    mentions: List[UUID]  # @mentioned users
    created_at: datetime
```

**Activity Feed:**
- Recent actions (last 50 events)
- User-specific activity
- Team activity
- Real-time updates (WebSocket or polling)

### Phase 7: Security Audit (Days 13-14)

**Checklist:**
- [ ] Dependency scanning (`pip-audit`, `safety`)
- [ ] OWASP Top 10 verification
- [ ] SQL injection prevention (SQLAlchemy parameterization)
- [ ] XSS prevention (React auto-escaping + CSP headers)
- [ ] Authentication bypass attempts
- [ ] Authorization bypass attempts
- [ ] Rate limiting on auth endpoints
- [ ] CSRF protection
- [ ] Secrets management (no hardcoded keys)
- [ ] HTTPS enforcement
- [ ] Security headers (HSTS, X-Frame-Options, etc.)

---

## Key Files to Modify

### Backend Files
- `backend/main.py` - Add WorkOS routes, authentication middleware
- `backend/models/` - Add ApprovalRequest, ApprovalStep, AuditLog, PatchSnapshot, Comment models
- `backend/api/v1/approvals.py` - NEW: Approval workflow endpoints
- `backend/api/v1/auth.py` - NEW: Authentication endpoints
- `backend/api/v1/audit.py` - NEW: Audit log endpoints
- `backend/api/v1/simulator.py` - NEW: Patch simulator endpoints
- `backend/api/v1/comments.py` - NEW: Comments endpoints
- `backend/services/approval_service.py` - NEW: Approval workflow logic
- `backend/services/snapshot_service.py` - NEW: Pre-patch snapshot + rollback
- `backend/services/simulator_service.py` - NEW: Impact prediction
- `backend/middleware/auth.py` - NEW: JWT authentication middleware
- `backend/middleware/rbac.py` - NEW: Permission decorators

### Frontend Files
- `frontend/src/app/auth/login/page.tsx` - NEW: Login page
- `frontend/src/app/dashboard/approvals/page.tsx` - NEW: Approval inbox
- `frontend/src/app/dashboard/audit/page.tsx` - NEW: Audit log viewer
- `frontend/src/components/approvals/` - NEW: Approval request cards
- `frontend/src/components/comments/` - NEW: Comment threads
- `frontend/src/components/simulator/` - NEW: Impact prediction UI

### Test Files
- `backend/tests/unit/test_scoring.py`
- `backend/tests/unit/test_optimization.py`
- `backend/tests/unit/test_approval_workflows.py`
- `backend/tests/integration/test_api_approvals.py`
- `backend/tests/integration/test_api_auth.py`

---

## Open Questions

1. **WorkOS setup** - Do we have a WorkOS account? Need API keys.
2. **Approval chains** - Should approval chains be configurable per tenant?
3. **Rollback automation** - What health checks trigger automated rollback?
4. **Patch simulator** - Where do we get historical patch data for predictions?
5. **Comments persistence** - Should comments use PostgreSQL or a separate system?

---

## Next Steps

1. Set up WorkOS account and get API keys
2. Implement authentication + SSO (WorkOS OAuth)
3. Build approval workflow models + API
4. Write unit tests for scoring, optimization, discovery services
5. Add integration tests for critical API paths
6. Implement rollback tracking (pre-patch snapshots)
7. Build patch simulator (impact prediction)
8. Add team collaboration features (comments, @mentions)
9. Run security audit (dependency scan, OWASP checks)
10. Performance testing (load tests, large-scale scans)

---

## Repository Structure

```
glasswatch/
├── backend/
│   ├── alembic/           # Database migrations
│   ├── api/v1/            # API endpoints
│   ├── middleware/        # Auth, RBAC, logging
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Business logic
│   │   └── discovery/     # 10 scanner implementations
│   ├── tests/             # Test suite
│   │   ├── unit/
│   │   └── integration/
│   └── main.py            # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   │   ├── dashboard/
│   │   │   │   ├── discovery/
│   │   │   │   ├── approvals/     # NEW
│   │   │   │   └── audit/         # NEW
│   │   │   └── auth/              # NEW
│   │   └── components/
│   │       ├── discovery/
│   │       ├── approvals/         # NEW
│   │       └── comments/          # NEW
│   └── tests/e2e/
├── docs/
│   ├── ASSET_DISCOVERY_QUICKSTART.md
│   ├── DISCOVERY_IMPLEMENTATION_SUMMARY.md
│   └── DISCOVERY_COMPLETE_SUMMARY.md
├── docker-compose.yml
├── STATUS.md
├── TODO.md
├── DECISIONS.md
└── HANDOVER_SPRINT_9.md  # This file
```

---

## Contact

**Project:** PatchGuide (formerly Glasswatch)  
**GitHub:** https://github.com/jmckinley/glasswatch  
**Timeline:** July 2026 Glasswing disclosure deadline  
**Current Sprint:** Sprint 10 (Production Hardening)  
**Progress:** 82% complete (9/11 sprints)

---

**Handover complete. Ready to start Sprint 10.**
