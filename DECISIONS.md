# Glasswatch Technical Decisions

## Architecture Decisions

### 1. Goal-Based Optimization (Core Differentiator)
**Decision**: Use constraint solving (OR-Tools) for patch scheduling instead of simple prioritization.

**Rationale**: 
- No competitor does true optimization - they just sort by severity
- Business objectives drive technical decisions
- Balances multiple constraints: risk, downtime, deadlines
- Creates defensible IP moat

**Trade-offs**:
- More complex than priority queues
- Requires OR-Tools dependency
- Optimization can be computationally expensive

### 2. Dark Theme Default
**Decision**: Dark theme as the only theme for MVP.

**Rationale**:
- Operations teams work at night
- Reduces eye strain during incidents
- Industry standard for ops tools
- Faster to build one theme well

### 3. Async Everything (FastAPI + SQLAlchemy)
**Decision**: Full async stack with FastAPI and async SQLAlchemy.

**Rationale**:
- Better performance under load
- Natural fit for real-time features
- Modern Python best practice
- Scales better than sync alternatives

### 4. Multi-Tenant from Day One
**Decision**: Build multi-tenancy into every query and model.

**Rationale**:
- Enterprise requirement
- Much harder to add later
- Enables SaaS business model
- Row-level security by default

### 5. Snapper Runtime Integration
**Decision**: ±25 point scoring adjustment based on runtime analysis.

**Rationale**:
- Unique differentiator - actual code execution data
- Dramatically improves prioritization accuracy
- Deep integration with Snapper (sister product)
- Real competitive advantage

## Technology Stack

### Backend: FastAPI + PostgreSQL
**Why not Django/Flask?**
- FastAPI has better async support
- Built-in OpenAPI documentation
- Type safety with Pydantic
- Modern and fast

### Frontend: Next.js 15 + TypeScript
**Why not React SPA?**
- Server components for better performance
- Built-in routing and optimization
- TypeScript by default
- App Router is the future

### Database: PostgreSQL + Redis
**Why not MongoDB?**
- Relational data model is perfect fit
- ACID compliance for financial data
- Row-level security support
- Redis for caching only

### Optimization: OR-Tools
**Why not custom algorithm?**
- Industry-standard constraint solver
- Well-tested and optimized
- Handles complex constraints
- Good Python bindings

## Data Model Decisions

### 1. Separate Bundle and PatchBundle
**Decision**: Two different models for optimization output vs. execution.

**Rationale**:
- Bundle = planned collection (from optimizer)
- PatchBundle = actual execution record
- Allows re-planning without losing history
- Clean separation of concerns

### 2. JSON Fields for Flexibility  
**Decision**: Use JSON columns for variable data (risk_assessment, implementation_plan, etc).

**Rationale**:
- Requirements still evolving
- Avoids constant migrations
- PostgreSQL JSON support is excellent
- Allows customer customization

### 3. Vulnerability Sources as Strings
**Decision**: Store source as string enum, not foreign key.

**Rationale**:
- Sources are well-known (nvd, ghsa, osv, kev)
- Avoids extra join
- Simpler data ingestion
- Can always normalize later

## API Design

### 1. RESTful + Async
**Decision**: Traditional REST API with async handlers.

**Rationale**:
- Well understood by developers
- Great tooling support
- GraphQL overkill for this use case
- Can add GraphQL later if needed

### 2. Pagination Everywhere
**Decision**: All list endpoints support skip/limit pagination.

**Rationale**:
- Consistent API experience
- Prevents accidental DoS
- Works well with frontend
- Simple to implement

### 3. Header-Based Tenant ID
**Decision**: Use X-Tenant-ID header for MVP instead of JWT.

**Rationale**:
- Faster to implement
- Easy to test
- WorkOS integration planned for production
- Clear upgrade path

## Security Decisions

### 1. Encryption at Rest (Future)
**Decision**: Design for encryption but implement later.

**Rationale**:
- Architecture supports it (encryption_key_id)
- Not needed for MVP
- AWS KMS integration planned
- Avoid premature optimization

### 2. Demo Mode First
**Decision**: Build fully functional demo mode before real auth.

**Rationale**:
- Faster development
- Better for demos and sales
- Auth can be added cleanly
- Reduces initial complexity

## Performance Decisions

### 1. Materialized Scores (Future)
**Decision**: Calculate scores on-demand for MVP, materialize later.

**Rationale**:
- Keeps data model simple
- Accurate scores always
- Can add caching when needed
- Premature optimization is evil

### 2. Bulk Operations
**Decision**: Support bulk import/export from day one.

**Rationale**:
- Enterprise requirement
- Painful to add later
- Enables easy onboarding
- Good for testing

## Sprint 10 Decisions (Production Hardening)

### 1. JWT Instead of WorkOS for MVP
**Decision**: Implement JWT-based authentication for v1.0, defer WorkOS SSO to v1.1.

**Rationale**:
- Faster time to market
- Full control over auth flow
- No vendor dependency for MVP
- WorkOS can be added as alternative provider
- JWT sufficient for beta/early customers

**Trade-offs**:
- Need to build user management UI
- No built-in SSO (Google, Microsoft, Okta)
- More auth code to maintain
- Clear migration path to WorkOS later

### 2. Multi-Level Approval Chains
**Decision**: Support both parallel and sequential approval workflows.

**Rationale**:
- Different organizations have different approval policies
- Parallel approvals for distributed teams (any 2 of 5 can approve)
- Sequential approvals for hierarchical orgs (L1 → L2 → L3)
- Flexibility is key selling point for enterprise

**Implementation**:
- Approval request stores chain configuration
- Engine evaluates completion based on chain type
- Auto-approval rules for low-risk bundles
- Escalation after timeout

### 3. Snapshot-Based Rollback
**Decision**: Capture full system state snapshots before patching instead of incremental backups.

**Rationale**:
- Simpler to implement
- Easier to restore (one operation)
- Complete state capture (configs + data)
- Acceptable storage cost for critical operations

**Trade-offs**:
- Higher storage requirements
- Snapshot creation time
- Point-in-time snapshots (not continuous)

### 4. Deterministic Patch Simulation
**Decision**: Build rule-based simulator instead of ML-based prediction.

**Rationale**:
- Predictable and explainable results
- No training data required
- Faster to implement
- Sufficient accuracy for v1.0
- Can add ML layer later for refinement

**Approach**:
- Dependency graph analysis
- Historical failure rate by patch type
- Service criticality scoring
- Downtime estimation formulas

### 5. @Mention Syntax and Parsing
**Decision**: Use `@username` for user mentions, `@team:teamname` for team mentions.

**Rationale**:
- Familiar syntax (Slack, GitHub, Discord)
- Easy to parse with regex
- Distinguishes users from teams
- Supports autocomplete

**Implementation**:
- Regex: `@([a-zA-Z0-9_-]+)` for users
- Regex: `@team:([a-zA-Z0-9_-]+)` for teams
- Notification routing based on mention type

### 6. Activity Feed Granularity
**Decision**: Log all user actions, filter on display (not on insert).

**Rationale**:
- Complete audit trail
- Flexible filtering later
- Better debugging and forensics
- Storage is cheap

**Trade-off**:
- Higher database writes
- More storage usage
- Need efficient queries
- Acceptable for production scale

### 7. Test Coverage Target: 70%+
**Decision**: Aim for 70%+ code coverage, prioritize critical paths.

**Rationale**:
- Balance between coverage and velocity
- 70% is industry standard for production apps
- Focus on business logic and workflows
- UI tests are lower priority for MVP

**Coverage Priority**:
1. Authentication and authorization (100%)
2. Approval workflows (100%)
3. Rollback and simulation (80%+)
4. Collaboration features (70%+)
5. UI components (50%+)

### 8. Security Headers Configuration
**Decision**: Strict security headers from day one (CSP, HSTS, X-Frame-Options).

**Rationale**:
- Easier to start strict than to tighten later
- Prevents common vulnerabilities
- Enterprise security requirement
- SOC 2 compliance preparation

**Headers Implemented**:
- Content-Security-Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

### 9. Separate Unit and Integration Tests
**Decision**: Split test suite into `tests/unit/` and `tests/integration/`.

**Rationale**:
- Unit tests run fast (no DB, no external services)
- Integration tests validate workflows
- Can run unit tests in CI, integration tests pre-deploy
- Clear separation of concerns

**Test Strategy**:
- Unit: Service logic, business rules, calculations
- Integration: API contracts, workflows, database operations
- Target: 65 unit tests, 22 integration tests (87 total)

### 10. PostgreSQL Over MySQL for Production
**Decision**: Stick with PostgreSQL, no MySQL support for v1.0.

**Rationale**:
- Better JSON support (critical for our schema)
- Superior query optimizer
- Better concurrency (MVCC)
- JSON operators used extensively
- Multi-tenant row-level security

**Trade-off**:
- Limits deployment options slightly
- PostgreSQL is industry standard for modern apps
- Cloud providers all support it well