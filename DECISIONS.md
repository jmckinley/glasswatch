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