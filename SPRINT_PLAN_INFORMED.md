# Glasswatch Informed Sprint Plan

**Based on**: Implementation history from April 17-18, 2026  
**Timeline**: 10 weeks remaining to July 2026 launch  
**Advantage**: We know exactly what works - no exploration needed

## Executive Summary

We're not starting from zero. We have:
- Proven architecture (5 layers)
- Tested scoring algorithm (8 factors with Snapper ±25pts)
- Validated goal engine design (constraint solver)
- Working code patterns from 33k lines
- 95% test coverage approach

This plan leverages everything we learned to deliver faster.

## Sprint Overview (2-week sprints)

| Sprint | Focus | Deliverables | Risk |
|--------|-------|--------------|------|
| 0 | Foundation & Models | Core API, all models, migrations | Low - we know the schema |
| 1 | Scoring & Ingestion | Working scorer, 3+ collectors | Low - algorithm proven |
| 2 | Goal Engine | Constraint solver, bundling | Medium - core differentiator |
| 3 | ITSM & Dashboard | ServiceNow, basic UI | Low - patterns established |
| 4 | Production Features | Patch Weather, webhooks | Medium - needs real data |
| 5 | Launch & Polish | K8s deploy, monitoring | High - time pressure |

## Sprint 0: Foundation (Week 1-2) ✅ ACCELERATED

**We skip exploration and build what we know works:**

### Week 1 - Core Platform
```python
# Day 1-2: Project structure (exactly as before)
backend/
  ├── alembic/
  ├── api/v1/
  ├── core/
  ├── db/
  ├── models/
  ├── services/
  └── tests/

# Day 3-4: All models at once (we know the schema)
- Tenant (with encryption_key_id)
- Vulnerability (with all scoring fields)
- Asset (with criticality + exposure)
- AssetVulnerability (junction)
- Goal + EnhancedGoal
- PatchBundle + BundlePatches

# Day 5: Core services
- Scoring service (copy the algorithm exactly)
- Base collector abstract class
- Authentication middleware
```

### Week 2 - APIs & Testing
```python
# Day 6-7: All CRUD APIs
/api/v1/vulnerabilities
/api/v1/assets  
/api/v1/goals
/api/v1/bundles

# Day 8-9: Test harness
- pytest fixtures (copy from Sprint 10)
- Scoring tests (20+ cases)
- API tests

# Day 10: Docker & Dev Environment
- docker-compose.yml (Postgres, Redis, Memgraph)
- Makefile with all commands
- Development seeds
```

**Acceleration**: We implement ALL models upfront since we know they work. No iterative discovery.

## Sprint 1: Ingestion & Intelligence (Week 3-4)

### Week 3 - Collectors
```python
# Parallel implementation (we have the patterns)
- OSV collector (proven simplest)
- KEV collector (high-value signal)
- GHSA collector (GitHub integration)
- EPSS collector (scoring enhancement)

# NEW: VulnCheck integration (commercial feed)
- Worth building early for differentiation
```

### Week 4 - Scoring Enhancement
```python
# Port the exact algorithm
- 8-factor scoring
- Snapper integration stub
- Redis caching layer
- Bulk scoring operations

# Add CVE matcher (we know the regex patterns)
```

**Acceleration**: Build all collectors in parallel since patterns are proven.

## Sprint 2: Goal Engine (Week 5-6) 🎯 CRITICAL PATH

### Week 5 - Core Optimizer
```python
class GoalOptimizer:
    def create_patch_plan(self, goal):
        # 1. Parse constraints (maintenance windows, risk tolerance)
        # 2. Get relevant vulnerabilities (filtered by goal criteria)
        # 3. Apply risk profile rules (conservative/balanced/aggressive)
        # 4. Run constraint solver (OR-Tools)
        # 5. Generate bundles respecting dependencies
        
# Copy the proven constraint solver approach
# This is THE differentiator
```

### Week 6 - Bundle Generation
```python
# Bundle creation with:
- Maintenance window assignment
- Dependency ordering
- Risk assessment
- Rollback plans
- Implementation steps

# API: POST /api/v1/goals/{id}/generate-plan
```

**Focus**: This is the secret sauce. Don't add features - nail the core algorithm.

## Sprint 3: Integration & UI (Week 7-8)

### Week 7 - ITSM Integration
```python
# ServiceNow first (most common)
- Change request creation
- Bundle → CR transformation  
- Status synchronization

# Jira Service Management second
# Webhook framework for others
```

### Week 8 - Dashboard MVP
```tsx
// Next.js 15 with proven patterns
- Dashboard home (metrics grid)
- Goal creation wizard
- Bundle timeline (Gantt)
- Vulnerability list
- Dark theme (required for ops)
```

**Acceleration**: Use component library (Radix) + Tailwind. No custom design.

## Sprint 4: Production Features (Week 9-10)

### Week 9 - Advanced Features
- **Patch Weather**: Community scoring system
- **Enhanced Goals**: Business impact modeling
- **Attestation Reports**: PDF generation
- **AI Planner**: Opus reasoning for complex goals

### Week 10 - Kubernetes & DevOps
- K8s operator with CRDs
- Multi-cloud deployment (Kustomize)
- Terraform modules
- Monitoring (Grafana)

## Sprint 5: Launch Sprint (Week 11-12)

### Week 11 - Testing & Hardening
- Load testing (Locust)
- Security audit
- Documentation
- Beta onboarding flow

### Week 12 - Launch
- Production deployment
- Launch announcement
- Glasswing Readiness Report (marketing)

## Key Accelerations vs Original

1. **Skip exploration**: We know what works
2. **Parallel development**: Multiple collectors at once
3. **Copy proven patterns**: Scoring, auth, APIs
4. **Focus on differentiators**: Goal engine, Patch Weather
5. **Defer nice-to-haves**: GraphQL, mobile app

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Time pressure | Proven patterns only, no experiments |
| Integration complexity | Start with ServiceNow only |
| Data quality | Use high-quality feeds (KEV, EPSS) |
| Testing time | Reuse Sprint 10 test infrastructure |

## Success Metrics

### Sprint 0
- [ ] All 6 models created with migrations
- [ ] 4 API endpoints working
- [ ] 20+ scoring tests passing

### Sprint 1  
- [ ] 4+ collectors operational
- [ ] 1000+ vulnerabilities ingested
- [ ] Scoring <50ms per vuln

### Sprint 2
- [ ] Goal → Bundle generation working
- [ ] Constraint solver tested
- [ ] 5+ test goals created

### Sprint 3
- [ ] ServiceNow integration live
- [ ] Dashboard showing real data
- [ ] <2s page load time

### Sprint 4
- [ ] Patch Weather calculating
- [ ] K8s operator deploying
- [ ] 3+ beta customers onboarded

### Sprint 5
- [ ] 99.9% uptime
- [ ] Load test passing (10k vulns)
- [ ] Public launch completed

## Daily Execution

### Morning (2 hours)
- Review yesterday's code
- Plan today's focus
- Unblock any issues

### Core Work (4-6 hours)
- Implement features
- Write tests
- Commit frequently

### End of Day (1 hour)
- Update STATUS.md
- Push all code
- Document decisions

## The Fast Path

Since we know:
1. The schema → Build all models Day 1
2. The scoring → Implement complete algorithm Day 5
3. The patterns → No exploration, just execution
4. The integrations → ServiceNow first, others later
5. The UI needs → Dashboard + goal wizard minimum

**We can build in 10 weeks what originally took 11 because we skip all dead ends.**

## Next Action

Start Sprint 0 immediately:
```bash
cd ~/glasswatch
# Create all models in models/
# Run: alembic init
# Create migration with all tables
# Implement scoring service
```

The code patterns are in GLASSWATCH_IMPLEMENTATION_HISTORY.md. The architecture is proven. Let's build.