# Glasswatch Backend Test Suite

Comprehensive test suite for Sprint 10: Production Hardening.

## Coverage

### Unit Tests (`tests/unit/`)

1. **`test_scoring.py`** - Vulnerability scoring service (13 tests)
   - All 8 scoring factors (severity, EPSS, KEV, criticality, exposure, runtime, patch, controls)
   - Edge cases (max/min scores, missing data)
   - Score clamping (0-100 range)
   - Snapper runtime modifiers

2. **`test_approval_service.py`** - Approval workflows (10 tests)
   - Create approval requests
   - Auto risk assessment (low/medium/high/critical)
   - Single and multi-approver thresholds
   - Approve/reject flows
   - Expiration handling
   - Policy matching
   - Auto-approve low risk

3. **`test_simulator_service.py`** - Patch impact simulation (8 tests)
   - Impact prediction structure
   - Risk score calculation (0-100)
   - Blast radius calculation
   - Dependency conflict detection
   - Downtime estimation and scaling
   - Dry-run validation
   - Criticality impact on risk

4. **`test_snapshot_service.py`** - Snapshots and rollback (10 tests)
   - Pre/post-patch snapshot capture
   - Package and service state tracking
   - Snapshot comparison and diff generation
   - Rollback initiation
   - Snapshot type validation
   - Integrity validation (checksum)
   - Corruption detection

5. **`test_collaboration_service.py`** - Team collaboration (10 tests)
   - Add comments
   - @mention parsing (email and username)
   - Threaded replies
   - Edit/delete (own vs others)
   - Permission enforcement
   - Emoji reactions
   - Reaction toggling
   - Activity feed

### Integration Tests (`tests/integration/`)

6. **`test_api_auth.py`** - Authentication API (7 tests)
   - Demo login
   - /me profile endpoint
   - API key generation
   - Unauthorized access (401)
   - Forbidden access (403)
   - Preferences update
   - Logout

7. **`test_api_approvals.py`** - Approvals API (9 tests)
   - Create approval request
   - List approvals
   - Filter by status
   - Approve flow
   - Reject flow
   - Create/list/update policies
   - CRUD operations

8. **`test_api_vulnerabilities.py`** - Vulnerabilities API (10 tests)
   - CRUD operations
   - Search by CVE
   - Filter by severity
   - Filter by KEV status
   - Pagination
   - Update/delete

9. **`test_api_assets.py`** - Assets API (10 tests)
   - CRUD operations
   - Filter by criticality
   - Filter internet-facing
   - Bulk import (3 assets)
   - Bulk import validation

## Total Coverage

- **Unit tests**: 51 test cases
- **Integration tests**: 36 test cases
- **Total**: 87 test cases

Target: 70%+ service coverage ✓

## Running Tests

### Run All Tests
```bash
cd ~/glasswatch/backend
./tests/run_tests.sh
```

### Run Specific Test Files
```bash
cd ~/glasswatch/backend
python -m pytest tests/unit/test_scoring.py -v
python -m pytest tests/integration/test_api_auth.py -v
```

### Run by Marker
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v
```

### With Coverage
```bash
python -m pytest tests/ --cov=backend --cov-report=html
```

## Test Fixtures

All fixtures are defined in `tests/conftest.py`:

- `test_engine` - Async SQLite test database
- `test_session` - Database session with auto-rollback
- `client` - FastAPI test client
- `create_test_tenant` - Factory for tenants
- `create_test_user` - Factory for users (with roles)
- `create_test_vulnerability` - Factory for vulnerabilities
- `create_test_asset` - Factory for assets
- `create_test_bundle` - Factory for bundles
- `authenticated_client` - Client with engineer JWT
- `admin_client` - Client with admin JWT
- `viewer_client` - Client with viewer JWT

## Requirements

```bash
pip install pytest pytest-asyncio httpx pytest-timeout
```

## Notes

- Tests use in-memory SQLite for speed
- All external dependencies are mocked
- Async tests use `pytest.mark.asyncio`
- Tests are isolated with automatic DB cleanup
- 30-second timeout per test
