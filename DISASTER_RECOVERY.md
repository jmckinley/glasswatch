# Disaster Recovery Plan - Glasswatch

**Document Version:** 1.0  
**Last Updated:** April 2026  
**Review Schedule:** Quarterly

## Executive Summary

This document outlines the disaster recovery procedures for the Glasswatch patch decision platform. It defines recovery objectives, procedures, and responsibilities to ensure business continuity in the event of a catastrophic failure.

### Recovery Objectives

- **RTO (Recovery Time Objective):** 4 hours
- **RPO (Recovery Point Objective):** 1 hour

This means:
- Maximum acceptable downtime: 4 hours
- Maximum acceptable data loss: 1 hour of transactions

## Table of Contents

1. [Backup Architecture](#backup-architecture)
2. [Recovery Procedures](#recovery-procedures)
3. [Failover Procedures](#failover-procedures)
4. [Communication Plan](#communication-plan)
5. [Testing Schedule](#testing-schedule)
6. [Escalation Contacts](#escalation-contacts)
7. [Post-Incident Review](#post-incident-review)

---

## 1. Backup Architecture

### Backup Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                     BACKUP ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────┘

Production Database (PostgreSQL 16)
         │
         ├──► Continuous WAL Archiving ──► S3 Bucket (wal-archive/)
         │                                   └──► Cross-region replication
         │
         ├──► Hourly Incremental Backup ──► Local Storage (/var/backups/)
         │                                   └──► Encrypted (AES-256)
         │                                   └──► S3 Upload (backups/)
         │
         └──► Daily Full Backup (00:00 UTC) ──► Local Storage
                                                 └──► Encrypted (AES-256)
                                                 └──► S3 Upload
                                                 └──► Glacier Archive (30 days)

Retention Policy:
├── Daily Backups:   7 days  (168 hours)
├── Weekly Backups:  4 weeks (28 days)
└── Monthly Backups: 12 months (1 year)

Storage Locations:
├── Primary:   Local NVMe SSD (/var/backups/glasswatch)
├── Secondary: S3 Standard (us-east-1)
└── Archive:   S3 Glacier (us-west-2) - cross-region
```

### Backup Components

1. **Database Backups**
   - Tool: `pg_dump` + custom backup service
   - Frequency: Daily full, hourly incremental
   - Encryption: AES-256 via Fernet (symmetric)
   - Compression: tar.gz (typical 70% reduction)
   - Verification: SHA-256 checksum + test restore

2. **Application State**
   - Configuration files: Version controlled in git
   - Secrets: AWS Secrets Manager + encrypted backups
   - Redis cache: Ephemeral, rebuilt on recovery

3. **Monitoring Data**
   - Logs: Centralized to CloudWatch / S3
   - Metrics: Retained in Prometheus/Grafana for 90 days
   - Audit logs: Retained in database (backed up)

### Backup Monitoring

- **Health Check:** Every 6 hours via cron
- **Alert Triggers:**
  - No successful backup in 25 hours
  - Backup checksum mismatch
  - S3 upload failure
  - Disk space < 10GB free
- **Notification Channels:**
  - Email: ops-team@example.com
  - Slack: #glasswatch-alerts
  - PagerDuty: P1 incident (after 48h no backup)

---

## 2. Recovery Procedures

### 2.1 Database Recovery from Backup

**Time Estimate:** 1-2 hours (depends on database size)

#### Prerequisites
- Access to backup files (local or S3)
- PostgreSQL 16 installed
- Encryption key (`BACKUP_ENCRYPTION_KEY`)

#### Procedure

1. **Identify Recovery Point**
   ```bash
   cd /opt/glasswatch/backend
   python3 scripts/backup_cli.py list
   ```
   Select the backup closest to desired recovery point.

2. **Stop Application**
   ```bash
   kubectl scale deployment glasswatch-backend --replicas=0
   ```

3. **Verify Backup Integrity**
   ```bash
   python3 scripts/backup_cli.py verify <backup-id>
   ```

4. **Restore Database**
   ```bash
   # Restore to staging database first (recommended)
   python3 scripts/backup_cli.py restore <backup-id> --target-db glasswatch_staging
   
   # After verification, restore to production
   python3 scripts/backup_cli.py restore <backup-id>
   ```

5. **Apply WAL Logs (if available for point-in-time recovery)**
   ```bash
   # Download WAL files from S3
   aws s3 sync s3://glasswatch-wal-archive/<date>/ /var/lib/postgresql/wal/
   
   # Apply WAL logs
   pg_wal_replay --target-time="2026-04-20 14:30:00" glasswatch
   ```

6. **Verify Data Integrity**
   ```bash
   psql -U glasswatch -d glasswatch -c "SELECT COUNT(*) FROM tenants;"
   psql -U glasswatch -d glasswatch -c "SELECT MAX(created_at) FROM audit_log;"
   ```

7. **Restart Application**
   ```bash
   kubectl scale deployment glasswatch-backend --replicas=3
   kubectl rollout status deployment glasswatch-backend
   ```

8. **Health Check**
   ```bash
   curl https://api.glasswatch.example.com/health
   ```

### 2.2 Full System Recovery (Infrastructure Failure)

**Time Estimate:** 3-4 hours

#### Scenario: Complete infrastructure loss (e.g., datacenter failure, K8s cluster destroyed)

1. **Provision New Infrastructure**
   - Deploy Kubernetes cluster (use Terraform/IaC scripts)
   - Estimated time: 30 minutes

2. **Deploy Application**
   ```bash
   kubectl apply -f deploy/k8s/namespace.yaml
   kubectl apply -f deploy/k8s/secrets.yaml
   kubectl apply -f deploy/k8s/configmap.yaml
   kubectl apply -f deploy/k8s/
   ```
   Estimated time: 15 minutes

3. **Restore Database** (see section 2.1)
   Estimated time: 1-2 hours

4. **Restore Redis Cache**
   Redis is ephemeral - cache will rebuild on first requests.
   No action required.

5. **DNS & Load Balancer**
   ```bash
   # Update DNS to point to new cluster
   aws route53 change-resource-record-sets --hosted-zone-id Z123 --change-batch file://dns-update.json
   ```
   Estimated time: 10 minutes (+ DNS propagation up to 1 hour)

6. **SSL Certificates**
   Cert-manager will auto-provision Let's Encrypt certificates.
   Estimated time: 5 minutes

7. **Verification**
   - Run smoke tests
   - Check monitoring dashboards
   - Verify user login
   - Test API endpoints

### 2.3 Data Corruption Recovery

**Scenario:** Application bug causes data corruption

1. **Assess Damage**
   - Identify affected tables/records
   - Determine corruption time window

2. **Isolate Corrupted Data**
   ```sql
   -- Create backup of corrupted data
   CREATE TABLE vulnerabilities_corrupted AS 
   SELECT * FROM vulnerabilities WHERE updated_at > '2026-04-20 14:00:00';
   
   -- Delete corrupted records
   DELETE FROM vulnerabilities WHERE updated_at > '2026-04-20 14:00:00';
   ```

3. **Restore from Backup**
   - Restore to staging database
   - Export clean data
   - Import to production

4. **Reprocess Recent Changes**
   - Replay audit logs if available
   - Re-run data collection jobs

---

## 3. Failover Procedures

### 3.1 Primary Database Failover

**Architecture:** Primary-Replica with automatic failover via Patroni

```
Primary DB (RW) ──► Synchronous Replication ──► Standby DB (RO)
     │                                               │
     └──────── Patroni/etcd ──────────────────────────┘
                    │
                    └──► Automatic failover on primary failure
```

#### Automatic Failover

Patroni monitors primary health every 10 seconds. On failure:
1. Standby promoted to primary (< 30 seconds)
2. Application connections redirected via service discovery
3. Alerts sent to ops team

#### Manual Failover

```bash
# Check cluster status
patronictl list glasswatch-cluster

# Initiate controlled failover
patronictl switchover glasswatch-cluster --candidate standby-1

# Verify new primary
psql -h glasswatch-db-service -U glasswatch -c "SELECT pg_is_in_recovery();"
# Should return: f (false = primary)
```

### 3.2 Application Pod Failover

**Kubernetes handles this automatically:**
- Min 3 replicas at all times (PodDisruptionBudget)
- Health probes every 10 seconds
- Failed pods restarted within 30 seconds
- HPA scales up under load

#### Manual Pod Restart

```bash
# Restart all pods (rolling update)
kubectl rollout restart deployment glasswatch-backend

# Force delete stuck pod
kubectl delete pod <pod-name> --force --grace-period=0
```

### 3.3 Multi-Region Failover

**Current setup:** Single region (us-east-1)  
**Future roadmap:** Multi-region with active-passive

Planned architecture:
- Primary: us-east-1
- Standby: us-west-2 (database replica + standby application)
- Failover time: < 15 minutes (manual process initially)

---

## 4. Communication Plan

### 4.1 Incident Classification

| Severity | Definition | Example | Response Time |
|----------|------------|---------|---------------|
| **P1 - Critical** | Total service outage | Database down, all users affected | Immediate |
| **P2 - High** | Partial outage | Single tenant down, degraded performance | 30 minutes |
| **P3 - Medium** | Minor issues | Feature not working, affects < 5% users | 2 hours |
| **P4 - Low** | Cosmetic issues | UI glitch, non-critical feature | 1 business day |

### 4.2 Communication Templates

#### P1 Incident - Initial Notification

```
Subject: [P1 INCIDENT] Glasswatch Service Outage

Status: INVESTIGATING
Severity: P1 - Critical
Impact: All users unable to access Glasswatch
Start Time: [UTC timestamp]

We are investigating a service outage affecting all Glasswatch users. 
Our team is actively working to restore service.

Next update: In 30 minutes or when status changes
Contact: ops-team@example.com

Incident Commander: [Name]
```

#### P1 Incident - Resolution

```
Subject: [RESOLVED] Glasswatch Service Restored

Status: RESOLVED
Duration: [X hours Y minutes]
Root Cause: [Brief description]

Service has been fully restored. All systems are operational.

Affected services: [List]
Recovery actions taken: [Brief list]

A detailed post-incident review will be published within 48 hours.

Thank you for your patience.
```

### 4.3 Stakeholder Contact List

**Internal Team:**
- Incident Commander: [Name] - [Phone] - [Email]
- Infrastructure Lead: [Name] - [Phone] - [Email]
- Database Admin: [Name] - [Phone] - [Email]
- Security Lead: [Name] - [Phone] - [Email]

**External Contacts:**
- AWS Support: 1-800-xxx-xxxx (Enterprise Support)
- DNS Provider: support@dnsvendor.com
- SSL Vendor: support@sslvendor.com

**Customer Communication:**
- Status Page: https://status.glasswatch.example.com
- Email: customers@example.com
- Twitter: @glasswatchstatus

---

## 5. Testing Schedule

### 5.1 Monthly DR Drill

**When:** First Sunday of each month, 02:00 UTC  
**Duration:** 2-3 hours  
**Environment:** Staging

#### Drill Scenarios (rotate monthly)

**Month 1:** Database restore from backup
- Restore yesterday's backup to staging
- Verify data integrity
- Document time taken

**Month 2:** Full infrastructure recovery
- Tear down staging cluster
- Rebuild from IaC
- Deploy application
- Restore database

**Month 3:** Failover testing
- Test database failover
- Test application pod failures
- Test network partition

**Month 4:** Data corruption recovery
- Simulate corruption
- Partial restore
- Verify fix

#### Drill Checklist

- [ ] Notify team 72 hours in advance
- [ ] Prepare test data
- [ ] Assign roles (Incident Commander, etc.)
- [ ] Execute drill
- [ ] Time each step
- [ ] Document issues found
- [ ] Update procedures based on learnings
- [ ] Send drill report to stakeholders

### 5.2 Quarterly Full DR Test

**When:** Last Sunday of March, June, September, December  
**Duration:** 4-6 hours  
**Environment:** Production-like isolated environment

**Scope:**
- Full infrastructure tear-down and rebuild
- Database restore from production backup
- End-to-end testing
- Performance validation

### 5.3 Annual Tabletop Exercise

**When:** January (Q1)  
**Duration:** 4 hours  
**Participants:** Full engineering + management team

**Format:**
- Scenario-based walkthrough
- No actual systems involved
- Focus on decision-making and communication
- Test escalation procedures

---

## 6. Escalation Contacts

### Escalation Matrix

```
Level 1 (0-15 min):
├── On-Call Engineer
│   └── Attempts recovery procedures
│   └── Opens incident in PagerDuty
│
Level 2 (15-30 min):
├── Infrastructure Lead
├── Database Administrator
│   └── Advanced troubleshooting
│   └── Decision: Restore from backup?
│
Level 3 (30-60 min):
├── Engineering Manager
├── CTO
│   └── Resource allocation
│   └── Customer communication decisions
│
Level 4 (60+ min):
└── CEO / Executive Team
    └── Major customer impact
    └── Public relations
```

### Contact Template

```markdown
## [ROLE NAME]
- **Primary Contact:** [Name]
- **Email:** [email]
- **Phone:** [phone]
- **Backup:** [Name]
- **Backup Phone:** [phone]
- **Availability:** 24/7 / Business hours / Weekdays only
- **Escalation Trigger:** [When to escalate to this person]
```

**Example:**

## Database Administrator
- **Primary Contact:** Jane Smith
- **Email:** jane.smith@example.com
- **Phone:** +1-555-123-4567
- **Backup:** John Doe
- **Backup Phone:** +1-555-987-6543
- **Availability:** 24/7
- **Escalation Trigger:** Database unavailable for > 15 minutes OR data corruption suspected

---

## 7. Post-Incident Review

### PIR Template

To be completed within 48 hours of incident resolution.

```markdown
# Post-Incident Review - [INCIDENT TITLE]

**Date:** [Date]
**Duration:** [Start] - [End] ([X] hours)
**Severity:** P[1-4]
**Incident Commander:** [Name]
**Participants:** [List all involved]

## Executive Summary
[2-3 sentence summary of what happened]

## Timeline
| Time (UTC) | Event | Action Taken | Actor |
|------------|-------|--------------|-------|
| 14:23 | Database CPU spike to 100% | Alert triggered | Monitoring |
| 14:25 | On-call paged | Acknowledged | Engineer A |
| 14:30 | Database unresponsive | Started investigation | Engineer A |
| ... | ... | ... | ... |

## Impact
- **Users Affected:** [Number / Percentage]
- **Tenants Affected:** [List if small number, otherwise count]
- **Data Loss:** Yes/No - [Description]
- **Revenue Impact:** $[Amount] (estimated)

## Root Cause
[Detailed technical explanation]

**5 Whys Analysis:**
1. Why did the system fail? [Answer]
2. Why did [answer 1]? [Answer]
3. Why did [answer 2]? [Answer]
4. Why did [answer 3]? [Answer]
5. Why did [answer 4]? [Answer] ← Root cause

## What Went Well
- [Thing 1]
- [Thing 2]

## What Went Wrong
- [Thing 1]
- [Thing 2]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Add monitoring for X | Engineer B | 2026-05-01 | Open |
| Update runbook with Y | Engineer C | 2026-04-25 | In Progress |

## Lessons Learned
- [Lesson 1]
- [Lesson 2]

## Prevention
How we will prevent this from happening again:
- [Prevention measure 1]
- [Prevention measure 2]

---
**Next Review:** [Date] - Verify action items completed
```

### PIR Distribution

- Engineering team (mandatory read)
- Customer success team (if customer-facing)
- Management (executive summary)
- Public status page (sanitized version for P1/P2)

---

## Appendix A: Quick Reference

### Emergency Contacts
- **PagerDuty:** https://example.pagerduty.com
- **Incident Slack:** #incident-response
- **Status Page:** https://status.glasswatch.example.com

### Critical Passwords / Secrets
- Stored in: AWS Secrets Manager (production) / 1Password (team)
- Backup encryption key: AWS Secrets Manager: `glasswatch/backup-key`
- Database master password: AWS Secrets Manager: `glasswatch/db-master`

### Key Commands

```bash
# Backup status
python3 scripts/backup_cli.py status

# List backups
python3 scripts/backup_cli.py list

# Restore backup
python3 scripts/backup_cli.py restore <id>

# Scale deployment
kubectl scale deployment glasswatch-backend --replicas=N

# View logs
kubectl logs -f deployment/glasswatch-backend

# Database connection
kubectl port-forward svc/glasswatch-db 5432:5432
psql -h localhost -U glasswatch -d glasswatch
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-20 | Glasswatch Ops | Initial version |

---

**Next Review:** 2026-07-20 (Quarterly)
