# Glasswatch Launch Checklist

**Target Launch Date:** July 2026 (Glasswing disclosure window)  
**Version:** 1.0  
**Status:** Pre-Launch  
**Last Updated:** 2026-04-20

---

## Overview

This checklist ensures Glasswatch is production-ready before launch. Complete all HIGH PRIORITY items before going live. MEDIUM and LOW priority items can be addressed in early access or post-launch.

---

## 🔴 HIGH PRIORITY - Must Complete Before Launch

### Infrastructure

- [ ] **DNS Configuration**
  - [ ] Production domain registered (e.g., glasswatch.io)
  - [ ] DNS records configured (A, AAAA, CNAME)
  - [ ] Subdomain setup (app.glasswatch.io, api.glasswatch.io)
  - [ ] TTL optimized for failover (300s or less)
  - [ ] DNSSEC enabled
  - [ ] Health check DNS queries verified

- [ ] **SSL/TLS Certificates**
  - [ ] Wildcard SSL certificate obtained (*.glasswatch.io)
  - [ ] Certificate installed on load balancer/ingress
  - [ ] TLS 1.3 enforced (1.2 minimum)
  - [ ] HSTS header configured (max-age=31536000)
  - [ ] Certificate auto-renewal configured (Let's Encrypt/AWS ACM)
  - [ ] SSL Labs test: A+ rating

- [ ] **CDN Setup**
  - [ ] CDN provider selected (CloudFlare/Fastly/AWS CloudFront)
  - [ ] Static assets cached (JS, CSS, images)
  - [ ] Cache headers configured (Cache-Control, ETag)
  - [ ] Cache invalidation webhook configured
  - [ ] DDoS protection enabled
  - [ ] WAF rules configured (OWASP ModSecurity Core Rule Set)

- [ ] **Load Balancer**
  - [ ] Production load balancer configured (AWS ALB/GCP LB/Azure LB)
  - [ ] Health checks enabled (HTTP 200 on /health)
  - [ ] Session affinity configured (for WebSocket)
  - [ ] Connection draining enabled (30s timeout)
  - [ ] Multi-AZ deployment verified
  - [ ] SSL termination at LB

### Security

- [ ] **Penetration Testing**
  - [ ] Pen test completed by external security firm
  - [ ] Critical vulnerabilities remediated
  - [ ] High vulnerabilities remediated or accepted (with justification)
  - [ ] Pen test report filed
  - [ ] Retest scheduled (quarterly)

- [ ] **Secrets Management**
  - [ ] All secrets rotated (database passwords, API keys, JWT secrets)
  - [ ] Secrets stored in vault (HashiCorp Vault/AWS Secrets Manager)
  - [ ] No secrets in code or config files (verified with git-secrets scan)
  - [ ] Secret rotation policy documented (90 days)
  - [ ] Emergency secret rotation procedure tested

- [ ] **OWASP Audit**
  - [ ] OWASP Top 10 checklist completed
  - [ ] SQL injection testing passed (automated + manual)
  - [ ] XSS testing passed (automated + manual)
  - [ ] CSRF protection verified (all state-changing endpoints)
  - [ ] Clickjacking protection verified (X-Frame-Options: DENY)
  - [ ] Security headers validated (see ARCHITECTURE.md)

- [ ] **Dependency Security**
  - [ ] Dependency vulnerability scan clean (Snyk/Dependabot)
  - [ ] Critical vulnerabilities patched (0 outstanding)
  - [ ] High vulnerabilities patched or mitigated
  - [ ] Automated dependency updates enabled (Dependabot/Renovate)
  - [ ] Software Bill of Materials (SBOM) generated

- [ ] **Compliance**
  - [ ] Data processing agreement (DPA) template ready
  - [ ] GDPR compliance checklist completed (if EU customers)
  - [ ] Data retention policy documented
  - [ ] Data deletion procedure tested
  - [ ] Privacy policy published and linked

### Database

- [ ] **Production Database**
  - [ ] PostgreSQL 15+ deployed in production
  - [ ] Multi-AZ/HA configuration verified (streaming replication)
  - [ ] Connection pooling configured (PgBouncer or SQLAlchemy pool)
  - [ ] Database firewall rules configured (VPC/private subnet)
  - [ ] Database encryption at rest enabled (TDE)
  - [ ] Audit logging enabled (pgAudit or cloud provider)

- [ ] **Migrations**
  - [ ] All Alembic migrations tested on production-like data
  - [ ] Migration rollback procedures documented and tested
  - [ ] Migration performance validated (no long locks)
  - [ ] Migration monitoring during deployment (lock timeouts, query times)

- [ ] **Backups**
  - [ ] Automated daily backups configured
  - [ ] Backup retention: 30 days (daily), 12 months (monthly)
  - [ ] Backups encrypted (AES-256)
  - [ ] Backup restore tested successfully (last 7 days)
  - [ ] Point-in-time recovery (PITR) enabled (if supported)
  - [ ] Off-site backup storage configured (different region/cloud)
  - [ ] Backup monitoring and alerts configured

### Monitoring

- [ ] **Error Tracking (Sentry)**
  - [ ] Sentry project created and configured
  - [ ] Source maps uploaded (frontend)
  - [ ] User context enabled (tenant, user ID)
  - [ ] Release tracking configured (git SHA)
  - [ ] Alert rules configured (critical errors → PagerDuty)
  - [ ] Error grouping and fingerprinting validated

- [ ] **Metrics (Prometheus + Grafana)**
  - [ ] Prometheus server deployed and scraping metrics
  - [ ] Grafana dashboards created:
    - [ ] Application overview (request rate, latency, errors)
    - [ ] Database metrics (connections, query time, slow queries)
    - [ ] Infrastructure metrics (CPU, memory, disk, network)
    - [ ] Business metrics (assets discovered, patches applied, goals achieved)
  - [ ] Metric retention: 30 days (detailed), 1 year (aggregated)

- [ ] **Alerts (PagerDuty)**
  - [ ] PagerDuty integration configured
  - [ ] On-call rotation schedule created (24/7 coverage)
  - [ ] Alert rules configured:
    - [ ] API down (health check fails >3 min) → Critical
    - [ ] High error rate (>5% in 5 min) → High
    - [ ] Database connection pool exhausted → High
    - [ ] Disk usage >80% → Medium
    - [ ] Failed backup → High
  - [ ] Alert escalation policy configured (15 min → manager, 30 min → director)
  - [ ] Test alert sent and acknowledged

- [ ] **Uptime Monitoring**
  - [ ] External uptime service configured (Pingdom/UptimeRobot/StatusCake)
  - [ ] Monitors created:
    - [ ] Frontend (app.glasswatch.io) - check every 1 min
    - [ ] API (/api/health) - check every 1 min
    - [ ] Database health - check every 5 min
  - [ ] Status page configured (status.glasswatch.io)
  - [ ] Incident notification webhook → Slack/Teams

### Performance

- [ ] **Load Testing**
  - [ ] Load test completed (1000+ concurrent users)
  - [ ] Stress test completed (find breaking point)
  - [ ] Soak test completed (24h sustained load)
  - [ ] Results documented:
    - [ ] P95 latency <500ms ✅
    - [ ] P99 latency <1s ✅
    - [ ] Error rate <0.1% ✅
    - [ ] Throughput: 10k+ req/min ✅
  - [ ] Performance bottlenecks identified and addressed

- [ ] **Database Indexes**
  - [ ] Query performance analysis completed (EXPLAIN ANALYZE)
  - [ ] Indexes created for all frequent queries
  - [ ] Composite indexes for multi-column filters
  - [ ] Partial indexes for filtered queries
  - [ ] Index usage verified (pg_stat_user_indexes)
  - [ ] Unused indexes removed

- [ ] **Caching**
  - [ ] Redis deployed and configured
  - [ ] Cache strategy implemented (see ARCHITECTURE.md)
  - [ ] Cache hit rate monitored (target: >80%)
  - [ ] Cache invalidation tested
  - [ ] Cache eviction policy configured (LRU)

### Documentation

- [ ] **API Documentation**
  - [ ] OpenAPI/Swagger spec complete and accurate
  - [ ] Example requests/responses for all endpoints
  - [ ] Authentication guide (JWT flow)
  - [ ] Rate limiting documented
  - [ ] Error codes and messages documented
  - [ ] API versioning strategy documented
  - [ ] Postman collection published

- [ ] **User Guide**
  - [ ] Getting started tutorial (15 min quickstart)
  - [ ] Feature walkthroughs (with screenshots):
    - [ ] Dashboard overview
    - [ ] Asset discovery
    - [ ] Vulnerability management
    - [ ] Goal creation and optimization
    - [ ] Approval workflows
    - [ ] Rollback procedures
  - [ ] Best practices documented
  - [ ] FAQ section (10+ common questions)
  - [ ] Video tutorials created (optional but recommended)

- [ ] **Admin Guide**
  - [ ] Installation instructions (Docker Compose + Kubernetes)
  - [ ] Configuration reference (environment variables)
  - [ ] Troubleshooting guide (common issues + solutions)
  - [ ] Maintenance procedures:
    - [ ] Database backups and restore
    - [ ] Log rotation
    - [ ] Certificate renewal
    - [ ] Scaling procedures
  - [ ] Security hardening checklist
  - [ ] Disaster recovery procedures

- [ ] **Deployment Guide**
  - [ ] Infrastructure requirements documented
  - [ ] Kubernetes manifests provided (Helm chart recommended)
  - [ ] Environment configuration guide (dev/staging/prod)
  - [ ] CI/CD pipeline setup guide (GitHub Actions)
  - [ ] Rollback procedures documented
  - [ ] Blue/green deployment guide (zero-downtime)

---

## 🟡 MEDIUM PRIORITY - Should Complete Before Launch

### Email Deliverability

- [ ] **Email Infrastructure**
  - [ ] Dedicated IP address obtained (if high volume)
  - [ ] SPF record configured (TXT record)
  - [ ] DKIM signing enabled
  - [ ] DMARC policy configured (start with p=none, monitor, then p=quarantine)
  - [ ] Email warming schedule executed (gradual volume ramp)
  - [ ] Bounce handling configured (hard bounce = unsubscribe)
  - [ ] Unsubscribe link in all marketing emails
  - [ ] Email deliverability monitored (Gmail Postmaster Tools)

- [ ] **Email Templates**
  - [ ] Transactional email templates designed (welcome, password reset, approval)
  - [ ] Marketing email templates designed (launch announcement, feature updates)
  - [ ] Email templates tested across clients (Gmail, Outlook, Apple Mail)
  - [ ] Plain text fallback for all HTML emails

### Legal & Compliance

- [ ] **Terms of Service**
  - [ ] Terms of service drafted by legal counsel
  - [ ] Terms reviewed for SaaS best practices
  - [ ] Terms published and linked in footer
  - [ ] Acceptance flow during signup

- [ ] **Privacy Policy**
  - [ ] Privacy policy drafted by legal counsel
  - [ ] GDPR compliance verified (if EU customers)
  - [ ] CCPA compliance verified (if CA customers)
  - [ ] Cookie consent banner configured (if tracking)
  - [ ] Privacy policy published and linked in footer

- [ ] **Data Processing Agreement (DPA)**
  - [ ] DPA template created
  - [ ] DPA reviewed by legal counsel
  - [ ] DPA available for enterprise customers
  - [ ] Sub-processor list maintained

### Team Readiness

- [ ] **On-Call Rotation**
  - [ ] On-call schedule created (24/7 coverage)
  - [ ] Team members trained on on-call procedures
  - [ ] Runbook created (common incidents + resolution steps)
  - [ ] Escalation path documented (L1 → L2 → L3)
  - [ ] On-call compensation policy documented

- [ ] **Runbook**
  - [ ] Incident response procedures documented:
    - [ ] API outage
    - [ ] Database failure
    - [ ] Cache failure
    - [ ] Disk full
    - [ ] Certificate expiration
  - [ ] Runbook tested in tabletop exercise
  - [ ] Runbook accessible to all on-call engineers

- [ ] **War Room**
  - [ ] Incident war room channel created (Slack #incidents)
  - [ ] War room roles defined (Incident Commander, Scribe, etc.)
  - [ ] Post-mortem template created
  - [ ] Blameless post-mortem culture established

### Rollback & Disaster Recovery

- [ ] **Rollback Plan**
  - [ ] Rollback procedures documented for:
    - [ ] Application code (git revert + redeploy)
    - [ ] Database migrations (Alembic downgrade)
    - [ ] Infrastructure changes (Terraform/CloudFormation revert)
  - [ ] Rollback tested in staging environment
  - [ ] Rollback time target: <15 minutes
  - [ ] Team briefed on rollback procedures

- [ ] **Disaster Recovery**
  - [ ] Disaster recovery plan documented (RTO/RPO targets)
  - [ ] RTO target: 4 hours (time to restore service)
  - [ ] RPO target: 1 hour (max data loss)
  - [ ] DR drill completed (restore from backup)
  - [ ] DR plan reviewed quarterly
  - [ ] Failover procedures documented (multi-region if applicable)

### Marketing & Communication

- [ ] **Launch Announcement**
  - [ ] Launch email drafted (to beta users + mailing list)
  - [ ] Blog post written (product overview, key features, launch story)
  - [ ] Social media posts prepared (Twitter, LinkedIn, Product Hunt)
  - [ ] Press release drafted (optional, for major outlets)
  - [ ] Launch timeline coordinated (email → blog → social → Product Hunt)

- [ ] **Product Hunt Launch**
  - [ ] Product Hunt profile created and optimized
  - [ ] Product Hunt thumbnail and gallery images prepared
  - [ ] Product Hunt launch scheduled (Tuesday-Thursday recommended)
  - [ ] Launch team coordinated (upvotes, comments, support)
  - [ ] "Maker" comment drafted (tell the story)

- [ ] **Website**
  - [ ] Landing page live and optimized
  - [ ] Product screenshots updated (latest UI)
  - [ ] Feature highlights section
  - [ ] Pricing page (if applicable)
  - [ ] Call-to-action buttons (Sign Up, Request Demo)
  - [ ] SEO optimized (meta tags, alt text, sitemap)

---

## 🟢 LOW PRIORITY - Post-Launch or Nice-to-Have

### Beta Testing

- [ ] **Beta Program**
  - [ ] Beta user recruitment (3-5 organizations)
  - [ ] Beta environment provisioned (separate from production)
  - [ ] Beta access provisioning automated
  - [ ] Beta feedback form created (Google Form/Typeform)
  - [ ] Beta user onboarding guide sent

- [ ] **Feedback Collection**
  - [ ] User interviews scheduled (1-on-1, 30 min each)
  - [ ] Bug reports tracked (GitHub Issues/Jira)
  - [ ] Feature requests tracked (ProductBoard/Canny)
  - [ ] Usability testing sessions conducted
  - [ ] Net Promoter Score (NPS) survey sent

- [ ] **Bug Fixes**
  - [ ] Critical bugs resolved (0 outstanding)
  - [ ] High priority bugs resolved or scheduled
  - [ ] UI/UX improvements based on feedback
  - [ ] Performance improvements based on profiling
  - [ ] Documentation updates based on feedback

### Sales Enablement

- [ ] **Product Deck**
  - [ ] Sales deck created (15-20 slides)
  - [ ] Deck sections: Problem, Solution, Features, Demo, Pricing, Case Studies
  - [ ] Deck reviewed by sales team
  - [ ] Deck uploaded to shared drive (accessible to all)

- [ ] **One-Pagers**
  - [ ] Product one-pager (single-page overview)
  - [ ] Feature comparison chart (vs competitors)
  - [ ] Technical one-pager (architecture, integrations, security)

- [ ] **Case Studies**
  - [ ] Beta customer case study written (with permission)
  - [ ] Case study includes: Challenge, Solution, Results (metrics)
  - [ ] Case study published on website

- [ ] **ROI Calculator**
  - [ ] ROI calculator built (spreadsheet or web app)
  - [ ] Calculator inputs: # of assets, # of vulnerabilities, current process
  - [ ] Calculator outputs: Time saved, cost saved, risk reduced
  - [ ] Calculator validated with real customer data

### Analytics & Tracking

- [ ] **Product Analytics**
  - [ ] Analytics tool configured (Mixpanel/Amplitude/PostHog)
  - [ ] Key events tracked:
    - [ ] User signup
    - [ ] Asset discovery run
    - [ ] Goal created
    - [ ] Bundle approved
    - [ ] Patch executed
  - [ ] Funnel analysis configured (signup → onboarding → activation)
  - [ ] Retention cohort analysis configured

- [ ] **Business Metrics Dashboard**
  - [ ] Dashboard created (Grafana/Metabase/Looker)
  - [ ] Metrics tracked:
    - [ ] Monthly Recurring Revenue (MRR)
    - [ ] Customer Acquisition Cost (CAC)
    - [ ] Customer Lifetime Value (LTV)
    - [ ] Churn rate
    - [ ] Net Promoter Score (NPS)
  - [ ] Dashboard shared with leadership (view-only)

### Post-Launch Roadmap

- [ ] **Phase 2 Features Planned**
  - [ ] ML-based asset classification
  - [ ] Anomaly detection (new assets, unusual changes)
  - [ ] Advanced reporting (custom dashboards)
  - [ ] Mobile app (iOS/Android)

- [ ] **Integrations Planned**
  - [ ] Jira ticketing integration
  - [ ] PagerDuty incident integration
  - [ ] Splunk log integration
  - [ ] ServiceNow ITSM integration

---

## Launch Day Checklist

**T-1 Week:**
- [ ] Final security scan (no critical vulnerabilities)
- [ ] Final performance test (load + soak)
- [ ] Final backup test (restore from production snapshot)
- [ ] Launch announcement scheduled
- [ ] Support team briefed and ready
- [ ] Marketing materials finalized

**T-1 Day:**
- [ ] All HIGH PRIORITY items completed
- [ ] Monitoring dashboards live and validated
- [ ] On-call rotation confirmed (people available)
- [ ] War room channel active
- [ ] Rollback plan accessible
- [ ] Launch communication ready to send

**T-0 (Launch Day):**
- [ ] Deploy to production (during low-traffic window)
- [ ] Smoke test production (critical user flows)
- [ ] Monitor dashboards for anomalies (first 4 hours)
- [ ] Send launch announcement (email, blog, social)
- [ ] Monitor support channels (Slack, email, chat)
- [ ] Post-launch standup (team debrief)

**T+1 Day:**
- [ ] Review metrics (signups, errors, performance)
- [ ] Address critical issues (if any)
- [ ] Respond to user feedback
- [ ] Update status page (all systems operational)

**T+1 Week:**
- [ ] Post-launch retrospective (what went well, what didn't)
- [ ] Document lessons learned
- [ ] Plan post-launch improvements
- [ ] Celebrate 🎉

---

## Rollback Criteria

If any of these occur within first 24 hours of launch, consider rollback:

- [ ] Critical security vulnerability discovered
- [ ] Data loss or corruption detected
- [ ] >5% error rate sustained for >15 minutes
- [ ] API downtime >15 minutes
- [ ] Database failure unrecoverable within 30 minutes
- [ ] Customer-reported critical bug affecting >10% of users

**Rollback Decision Maker:** CTO or designated incident commander

---

## Notes

- This checklist is a living document. Update as needed.
- HIGH PRIORITY items are blockers for launch.
- MEDIUM PRIORITY items reduce launch risk but are not blockers.
- LOW PRIORITY items are post-launch or nice-to-have.
- Use this checklist in weekly launch readiness meetings.

---

**Status:** 📋 In Progress  
**Target Completion:** June 30, 2026  
**Launch Date:** July 1, 2026  
**Owner:** CTO + Engineering Lead

**Last Updated:** 2026-04-20  
**Next Review:** Weekly until launch
