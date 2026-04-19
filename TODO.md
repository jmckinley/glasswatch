# Glasswatch TODO

## Sprint 0 - Foundation (70% Complete)

### ✅ Completed
- [x] Database models (8 core + 3 optimization)
- [x] Alembic migration setup
- [x] Scoring service with Snapper integration  
- [x] Vulnerability API (CRUD + search + stats)
- [x] Assets API (CRUD + bulk import)
- [x] Goals API with constraint solver
- [x] Optimization service (OR-Tools + heuristic)
- [x] Frontend scaffold (Next.js 15)
- [x] Dark theme dashboard
- [x] Goals, Vulnerabilities, Schedule pages
- [x] Docker Compose setup
- [x] Basic auth (header-based tenant)

### 🔄 In Progress
- [ ] Run database migrations
- [ ] Test full stack with docker-compose
- [ ] Connect frontend to real API (remove mocks)

### 📋 TODO for Sprint 0 Completion
- [ ] Bundles API endpoints
- [ ] Maintenance Windows API
- [ ] WebSocket for real-time updates
- [ ] Error handling improvements
- [ ] API documentation (OpenAPI)
- [ ] Frontend error states
- [ ] Loading states for all pages
- [ ] Basic e2e tests

## Sprint 1 - Integration (Next)

### ITSM Integration
- [ ] ServiceNow connector
- [ ] Jira Service Management
- [ ] Change request automation
- [ ] Approval workflows

### Vulnerability Sources  
- [ ] NVD feed ingestion
- [ ] GitHub Security Advisories
- [ ] OSV integration
- [ ] KEV catalog sync

### Asset Discovery
- [ ] AWS integration
- [ ] Azure integration  
- [ ] Kubernetes discovery
- [ ] CMDB import

## Sprint 2 - Intelligence

### Patch Weather
- [ ] Community reporting endpoints
- [ ] Success/failure tracking
- [ ] Vendor acknowledgment tracking
- [ ] Weather score calculation

### AI Assistant
- [ ] Natural language goal creation
- [ ] Conversational insights
- [ ] Anomaly detection
- [ ] Recommendation engine

## Sprint 3 - Production

### Security & Auth
- [ ] WorkOS SSO integration
- [ ] Role-based access control
- [ ] API rate limiting
- [ ] Audit logging

### Performance
- [ ] Redis caching layer
- [ ] Query optimization
- [ ] Background job processing
- [ ] Horizontal scaling

### Deployment
- [ ] Kubernetes manifests
- [ ] Helm charts
- [ ] Multi-region deployment
- [ ] Backup and recovery

## Technical Debt
- [ ] Comprehensive test coverage
- [ ] API versioning strategy
- [ ] Monitoring and alerting
- [ ] Performance benchmarks
- [ ] Security audit

## Nice to Have
- [ ] Mobile app
- [ ] Slack/Teams integration
- [ ] Executive dashboards
- [ ] Custom reporting
- [ ] API SDK (Python, Go, JS)