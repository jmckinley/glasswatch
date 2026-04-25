# Glasswatch Test Plan — April 2026

## Overview
- **Total tests:** 516 (479 backend + 37 frontend)
- **Backend:** 479 passing (includes 4 xfailed, 2 xpassed)
- **Frontend:** 37 passing (React Testing Library)
- **Last run:** 2026-04-25
- **CI:** GitHub Actions docker-build.yml on push to main

---

## Backend Test Coverage

### Unit Tests (`tests/unit/`)

- `test_approval_service.py` — approval request creation, approval/rejection, risk assessment, policy matching, expiration handling
- `test_audit_service.py` — audit log entry creation, filtering, export, hook triggering, tenant isolation
- `test_auth_rate_limiting.py` — Redis-backed sliding-window rate limiter (mocked Redis, pure logic)
- `test_bundle_state_machine.py` — VALID_TRANSITIONS map, status change guards via PATCH/POST
- `test_collaboration_service.py` — comments, @mentions, threading, reactions, activity feed
- `test_digest.py` — weekly digest HTML content builder, template rendering logic
- `test_external_api_simulators.py` — 89 tests covering all 11 simulated external API systems (Tenable, Qualys, Rapid7, and more)
- `test_import.py` — CSV parse helpers, row validation logic (no DB required)
- `test_invites.py` — invite token uniqueness, expiry, acceptance, revocation
- `test_maintenance_windows_enhanced.py` — MaintenanceWindow model: datacenter/geography fields, enhanced schedule logic
- `test_model_indexes.py` — structural checks that performance-critical SQLAlchemy indexes are defined (no live DB)
- `test_reporting.py` — BOD 22-01 compliance calculation, SLA deadlines/status, MTTP calculation
- `test_scoring.py` — 8-factor scoring algorithm: severity, EPSS, KEV, runtime, compensating controls, internet-facing, clamping
- `test_simulator_service.py` — impact prediction, risk scoring, blast radius, dependency detection, downtime estimation, dry-run validation
- `test_snapshot_service.py` — snapshot capture (pre/post patch), comparison diffs, rollback initiation, integrity validation

### Integration Tests (`tests/integration/`)

- `test_api_approvals.py` — approvals endpoints: creation, listing, approval/rejection flow, policy management
- `test_api_assets.py` — assets endpoints: list, get, create, update, delete (identifier/name fields)
- `test_api_auth.py` — auth endpoints: demo login, /me profile, API key generation, JWT tokens, tenant isolation
- `test_api_vulnerabilities.py` — vulnerabilities endpoints: list, search, filtering, GET by ID
- `test_audit_hooks.py` — audit hook integration: verifies actions on bundles, goals, users, rules trigger correct audit log entries
- `test_audit_log_api.py` — audit log API: query filtering (action, resource_type, user_id, since/until), pagination, CSV export
- `test_bundle_state_machine.py` — state machine guards via HTTP: valid transitions succeed, invalid ones return 409
- `test_core_loop.py` — end-to-end core loop: auth → data endpoints → bundle workflow → agent → webhooks → reporting
- `test_export_endpoints.py` — export API: JSON/CSV vulnerability export, filter params, field presence
- `test_invite_flow.py` — invite HTTP lifecycle: POST (admin), accept, revoke, expiry enforcement
- `test_maintenance_windows_enhanced.py` — maintenance window API: datacenter/geography fields, enhanced schedule API
- `test_reporting_endpoints.py` — reporting API: compliance summary, SLA metrics, exposure trends

---

## Coverage by Module (2026-04-24)

| Module | Coverage |
|--------|----------|
| `services/simulator_service.py` | 91% |
| `services/collaboration_service.py` | 83% |
| `services/approval_service.py` | 77% |
| `services/rate_limiter.py` | 71% |
| `services/snapshot_service.py` | 69% |
| `services/scoring.py` | 65% |
| `services/notifications.py` | 48% |
| `services/rule_engine.py` | 32% |
| `services/cache_service.py` | 27% |
| `services/optimization.py` | 14% |
| `services/slack_service.py` | 16% |
| `services/deployment_service.py` | 16% |
| `services/discovery/*` (scanners) | 10–21% |
| `services/connection_health.py` | 7% |
| `services/backup_service.py` | 0% |
| `services/digest_service.py` | 0% |
| `services/error_service.py` | 0% |
| `services/metrics_service.py` | 0% |
| `services/reporting.py` | 0% |
| **TOTAL** | **36%** |

---

## Areas Well Covered

1. **Vulnerability scoring** — 8-factor algorithm fully unit tested, edge cases for clamping/bonuses
2. **Bundle state machine** — both unit and integration tests, guards on invalid transitions
3. **Authentication & tenant isolation** — JWT, API keys, demo login, multi-tenant enforcement
4. **Approval workflow** — creation, risk assessment, policy matching, expiry
5. **Snapshot/rollback** — capture, comparison diff, integrity check, rollback initiation
6. **Patch simulation** — blast radius, downtime, dependency conflicts, dry-run
7. **Compliance reporting logic** — BOD 22-01, SLA deadlines, MTTP calculation
8. **Model schema integrity** — structural index tests prevent accidental schema regression

---

## Known Gaps

- **`services/reporting.py` (0%)** — the heavy HTTP reporting endpoints are tested via integration (`test_reporting_endpoints.py`) but service layer itself has no direct unit tests
- **`services/backup_service.py` (0%)** — no tests; backup/restore paths completely untested
- **`services/digest_service.py` (0%)** — digest service uncovered (unit tests only cover the HTML builder helper)
- **`services/error_service.py` / `metrics_service.py` (0%)** — telemetry and error reporting services have no coverage
- **Discovery scanners (10–21%)** — AWS, Azure, GCP, Nmap, Trivy, Kubescape, ServiceNow, Device42 scanners are mostly untested (network/cloud dependencies make mocking complex)
- **`services/connection_health.py` (7%)** — health probe logic nearly untested
- **`services/cache_service.py` (27%)** — Redis cache service mostly mocked out or skipped
- **Frontend** — React component tests not yet in place (Track 2 work)

---

## Frontend Testing

37 React component tests using React Testing Library and MSW (Mock Service Worker) for API mocking.

Covered flows:
- Login (email/password and demo login)
- Vulnerability list and filtering
- Bundle workflow (create, review, approve)
- Patch simulation UI
- Audit log view and export

---

## Test Commands

```bash
# Run all backend tests
cd backend && python3 -m pytest tests/ -q

# Run unit tests only
cd backend && python3 -m pytest tests/unit/ -q

# Run integration tests only
cd backend && python3 -m pytest tests/integration/ -q

# Run with verbose output
cd backend && python3 -m pytest tests/ -v

# Run with coverage
cd backend && python3 -m pytest tests/ --cov=api --cov=services --cov=models --cov-report=term-missing -q
```

---

## Seed Scripts

- `backend/scripts/seed_audit_log.py` — populates the audit log with realistic sample entries for demo/testing

---

## Sprint History

| Sprint | Tests Added | Total |
|--------|-------------|-------|
| Sprints 16–19 | baseline | 99 |
| Sprints 20–23 | +70 | 169 |
| Code quality pass | +112 | 281 |
| UX/security/maintenance | +82 | 363 |
| Sprint 10 (audit log, simulators, frontend) | +153 | 516 |
| **Current (2026-04-25)** | — | **516** (479 backend + 37 frontend) |
