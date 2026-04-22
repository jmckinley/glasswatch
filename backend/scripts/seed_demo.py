"""
Seed demo data for Glasswatch.

Creates a demo tenant, user, vulnerabilities, assets, goals,
maintenance windows, and bundles for demonstration purposes.

Idempotent — checks before inserting.

Usage:
    PYTHONPATH=/home/node/glasswatch DATABASE_URL="postgresql://..." \
        python3 backend/scripts/seed_demo.py
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

# Register UUID adapter
psycopg2.extras.register_uuid()

# ── Constants ──────────────────────────────────────────────────────────

TENANT_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
USER_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
NOW = datetime.now(timezone.utc)

# ── Helpers ────────────────────────────────────────────────────────────

def uid():
    return uuid.uuid4()


def exists(cur, table, **kwargs):
    """Check if a row exists."""
    conditions = " AND ".join(f"{k} = %s" for k in kwargs)
    cur.execute(f"SELECT 1 FROM {table} WHERE {conditions} LIMIT 1", list(kwargs.values()))
    return cur.fetchone() is not None


# ── Seed Functions ─────────────────────────────────────────────────────

def seed_tenant(cur):
    if exists(cur, "tenants", id=TENANT_ID):
        print("  ✓ Tenant already exists")
        return
    
    # Include mock Slack config in tenant settings for demo
    settings = {
        "features": ["goals", "approvals", "collaboration"],
        "slack": {
            "access_token": "xoxb-demo-token-for-testing",
            "team_id": "T0DEMO123",
            "team_name": "Demo Workspace",
            "bot_user_id": "U0DEMOBOT",
            "installed_at": NOW.isoformat(),
        }
    }
    
    cur.execute("""
        INSERT INTO tenants (id, name, email, region, tier, is_active, encryption_key_id, settings, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        TENANT_ID, "Demo Organization", "admin@demo.patchguide.ai",
        "us-east-1", "enterprise", True, "demo-key-001",
        Json(settings), NOW
    ))
    print("  ✓ Created tenant: Demo Organization (with mock Slack connection)")


def seed_user(cur):
    if exists(cur, "users", id=USER_ID):
        print("  ✓ User already exists")
        return
    cur.execute("""
        INSERT INTO users (id, tenant_id, email, name, is_active, role, permissions, preferences, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        USER_ID, TENANT_ID, "demo@patchguide.ai", "Demo Admin",
        True, "ADMIN",
        Json({"all": True}),
        Json({"theme": "dark", "notifications": True}),
        NOW
    ))
    print("  ✓ Created user: demo@patchguide.ai")


def seed_vulnerabilities(cur):
    """Create 25 sample vulnerabilities."""
    vulns = [
        # Critical
        ("CVE-2024-21762", "critical", 9.8, 0.97, True, True,
         "Fortinet FortiOS Out-of-Bounds Write", "A out-of-bounds write vulnerability in FortiOS SSL VPN may allow a remote unauthenticated attacker to execute arbitrary code."),
        ("CVE-2024-3400", "critical", 10.0, 0.95, True, True,
         "Palo Alto Networks PAN-OS Command Injection", "A command injection vulnerability in GlobalProtect feature of PAN-OS allows unauthenticated attackers to execute arbitrary code with root privileges."),
        ("CVE-2024-1709", "critical", 10.0, 0.94, True, True,
         "ConnectWise ScreenConnect Authentication Bypass", "Authentication bypass vulnerability allowing unauthorized access to the ScreenConnect setup wizard."),
        ("CVE-2024-27198", "critical", 9.8, 0.92, True, True,
         "JetBrains TeamCity Authentication Bypass", "Authentication bypass allowing unauthenticated attacker to gain admin access."),
        ("CVE-2024-23897", "critical", 9.8, 0.89, True, True,
         "Jenkins Arbitrary File Read", "Jenkins CLI allows reading arbitrary files on the controller file system."),
        # High
        ("CVE-2024-0012", "high", 8.8, 0.76, False, True,
         "PAN-OS Management Interface Authentication Bypass", "Authentication bypass in the PAN-OS management web interface."),
        ("CVE-2024-38077", "high", 8.1, 0.71, False, True,
         "Windows Remote Desktop Licensing RCE", "Remote code execution vulnerability in Windows RD Licensing Service."),
        ("CVE-2024-6387", "high", 8.1, 0.68, True, True,
         "OpenSSH regreSSHion Race Condition", "Signal handler race condition in OpenSSH's server allows unauthenticated RCE."),
        ("CVE-2024-4577", "high", 8.0, 0.65, True, True,
         "PHP CGI Argument Injection", "PHP CGI argument injection vulnerability affecting Windows installations."),
        ("CVE-2024-21887", "high", 8.2, 0.73, True, True,
         "Ivanti Connect Secure Command Injection", "Command injection in web components of Ivanti Connect Secure."),
        ("CVE-2024-29824", "high", 7.8, 0.62, False, True,
         "Ivanti EPM SQL Injection", "SQL injection vulnerability in Ivanti Endpoint Manager."),
        ("CVE-2024-20399", "high", 7.5, 0.58, True, True,
         "Cisco NX-OS CLI Command Injection", "Command injection in NX-OS CLI allowing local authenticated attacker to execute arbitrary commands."),
        ("CVE-2024-22252", "high", 7.1, 0.45, False, True,
         "VMware ESXi Use-After-Free", "Use-after-free vulnerability in VMware ESXi XHCI USB controller."),
        # Medium
        ("CVE-2024-30088", "medium", 6.8, 0.35, False, True,
         "Windows Kernel EoP", "Elevation of privilege vulnerability in the Windows kernel."),
        ("CVE-2024-38063", "medium", 6.5, 0.31, False, True,
         "Windows TCP/IP IPv6 Remote Code Execution", "Remote code execution vulnerability in Windows TCP/IP handling of IPv6 packets."),
        ("CVE-2024-28986", "medium", 6.3, 0.28, False, True,
         "SolarWinds Web Help Desk Java Deserialization", "Java deserialization vulnerability in SolarWinds Web Help Desk."),
        ("CVE-2024-5910", "medium", 5.8, 0.22, False, True,
         "Palo Alto Expedition Missing Authentication", "Missing authentication for a critical function in Palo Alto Expedition."),
        ("CVE-2024-38178", "medium", 5.5, 0.19, False, True,
         "Windows Scripting Engine Memory Corruption", "Memory corruption vulnerability in Windows Scripting Engine."),
        ("CVE-2024-37085", "medium", 6.0, 0.25, False, True,
         "VMware ESXi Active Directory Integration", "Active Directory integration vulnerability in VMware ESXi."),
        ("CVE-2024-21893", "medium", 5.3, 0.18, True, True,
         "Ivanti SSRF in SAML Component", "Server-side request forgery in SAML component of Ivanti Connect Secure."),
        ("CVE-2024-9474", "medium", 5.0, 0.15, False, True,
         "PAN-OS Management Interface Privilege Escalation", "Privilege escalation in the management interface of PAN-OS."),
        # Low
        ("CVE-2024-36971", "low", 3.8, 0.08, False, True,
         "Linux Kernel UAF in Route Management", "Use-after-free vulnerability in Linux kernel route management."),
        ("CVE-2024-43573", "low", 3.5, 0.06, False, False,
         "Windows MSHTML Platform Spoofing", "Spoofing vulnerability in Windows MSHTML platform."),
        ("CVE-2024-44068", "low", 3.2, 0.04, False, False,
         "Samsung Mobile Processor Use-After-Free", "Use-after-free in Samsung mobile processor firmware."),
        ("CVE-2024-44243", "low", 2.8, 0.03, False, False,
         "macOS System Integrity Protection Bypass", "Bypass of System Integrity Protection in macOS."),
    ]
    
    vuln_ids = []
    for cve, severity, cvss, epss, kev, patch, title, desc in vulns:
        if exists(cur, "vulnerabilities", identifier=cve):
            cur.execute("SELECT id FROM vulnerabilities WHERE identifier = %s", (cve,))
            vuln_ids.append(cur.fetchone()[0])
            continue
        vid = uid()
        vuln_ids.append(vid)
        cur.execute("""
            INSERT INTO vulnerabilities (id, identifier, source, title, description, severity,
                cvss_score, cvss_vector, epss_score, kev_listed, patch_available,
                exploit_available, exploit_maturity, published_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            vid, cve, "nvd", title, desc, severity,
            cvss, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", epss,
            kev, patch,
            kev, "weaponized" if kev else ("poc" if epss > 0.3 else "none"),
            NOW - timedelta(days=30 + hash(cve) % 180),
            NOW
        ))
    
    print(f"  ✓ Seeded {len(vulns)} vulnerabilities")
    return vuln_ids


def seed_assets(cur):
    """Create 12 sample assets across environments."""
    assets = [
        # (identifier, name, type, platform, env, exposure, crit, team, os_fam, os_ver, tags, patch_group)
        # Production servers
        ("PROD-WEB-01", "prod-web-01.acme.internal", "server", "linux", "production",
         "internet-facing", 9, "Web Services", "Red Hat Enterprise Linux", "9.3",
         ["web-tier", "pci-scope", "internet-facing", "deploy-group-a"], "web-prod"),
        ("PROD-WEB-02", "prod-web-02.acme.internal", "server", "linux", "production",
         "internet-facing", 9, "Web Services", "Red Hat Enterprise Linux", "9.3",
         ["web-tier", "pci-scope", "internet-facing", "deploy-group-a"], "web-prod"),
        ("PROD-API-01", "prod-api-01.acme.internal", "server", "linux", "production",
         "internal", 8, "API Platform", "Ubuntu", "22.04 LTS",
         ["api-tier", "pci-scope", "deploy-group-a"], "api-prod"),
        ("PROD-DB-01", "prod-db-primary.acme.internal", "database", "linux", "production",
         "internal", 10, "Data Services", "Red Hat Enterprise Linux", "9.2",
         ["database-tier", "pci-scope", "critical-data", "deploy-group-b"], "db-prod"),
        ("PROD-DB-02", "prod-db-replica.acme.internal", "database", "linux", "production",
         "internal", 8, "Data Services", "Red Hat Enterprise Linux", "9.2",
         ["database-tier", "pci-scope", "deploy-group-b"], "db-prod"),
        # Staging
        ("STG-WEB-01", "stg-web-01.acme.internal", "server", "linux", "staging",
         "internal", 5, "Web Services", "Ubuntu", "22.04 LTS",
         ["staging", "web-tier"], "staging"),
        ("STG-API-01", "stg-api-01.acme.internal", "server", "linux", "staging",
         "internal", 5, "API Platform", "Ubuntu", "22.04 LTS",
         ["staging", "api-tier"], "staging"),
        # Containers
        ("K8S-NODE-01", "k8s-node-01.acme.internal", "container", "linux", "production",
         "internal", 7, "Platform Engineering", "Flatcar Container Linux", "3815",
         ["k8s-workload", "container-host", "deploy-group-a"], "k8s-prod"),
        ("K8S-NODE-02", "k8s-node-02.acme.internal", "container", "linux", "production",
         "internal", 7, "Platform Engineering", "Flatcar Container Linux", "3815",
         ["k8s-workload", "container-host", "deploy-group-a"], "k8s-prod"),
        # Network
        ("FW-EDGE-01", "fw-edge-01.acme.internal", "server", "other", "production",
         "internet-facing", 10, "Network Security", "PAN-OS", "11.1.2",
         ["network-infra", "internet-facing", "pci-scope", "deploy-group-c"], "network-prod"),
        # Development
        ("DEV-SERVER-01", "dev-server-01.acme.internal", "server", "linux", "development",
         "internal", 3, "Engineering", "Ubuntu", "24.04 LTS",
         ["development", "legacy"], "dev"),
        # Windows
        ("WIN-JUMP-01", "win-jump-01.acme.internal", "server", "windows", "production",
         "internal", 8, "IT Operations", "Windows Server", "2022",
         ["jump-host", "windows", "deploy-group-c"], "windows-prod"),
    ]
    
    asset_ids = []
    for ident, name, atype, platform, env, exposure, crit, team, os_fam, os_ver, tags, patch_group in assets:
        if exists(cur, "assets", identifier=ident, tenant_id=TENANT_ID):
            cur.execute("SELECT id FROM assets WHERE identifier = %s AND tenant_id = %s", (ident, TENANT_ID))
            asset_ids.append(cur.fetchone()[0])
            continue
        aid = uid()
        asset_ids.append(aid)
        cur.execute("""
            INSERT INTO assets (id, tenant_id, identifier, name, type, platform, environment,
                exposure, criticality, owner_team, os_family, os_version, tags, patch_group, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            aid, TENANT_ID, ident, name, atype, platform, env,
            exposure, crit, team, os_fam, os_ver, Json(tags), patch_group, NOW
        ))
    
    print(f"  ✓ Seeded {len(assets)} assets")
    return asset_ids


def seed_asset_vulnerabilities(cur, vuln_ids, asset_ids):
    """Link assets to vulnerabilities with risk scores."""
    count = 0
    for i, aid in enumerate(asset_ids):
        # Each asset gets 3-8 vulnerabilities
        n_vulns = 3 + (hash(str(aid)) % 6)
        for j in range(min(n_vulns, len(vuln_ids))):
            vid = vuln_ids[(i * 3 + j) % len(vuln_ids)]
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            risk = min(100, max(10, 50 + (hash(str(aid) + str(vid)) % 50)))
            statuses = ["ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "MITIGATED"]
            status = statuses[hash(str(aid) + str(vid)) % len(statuses)]
            cur.execute("""
                INSERT INTO asset_vulnerabilities (id, asset_id, vulnerability_id,
                    discovered_at, discovered_by, risk_score, status, patch_available, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=15 + hash(str(vid)) % 60),
                "qualys", risk, status, True, NOW
            ))
            count += 1
    print(f"  ✓ Seeded {count} asset-vulnerability links")


def seed_goals(cur):
    """Create 3 sample goals with varied progress."""
    goals = [
        (uid(), "Glasswing Compliance Deadline", "compliance_deadline",
         "Achieve full Glasswing vulnerability disclosure compliance by the July 2026 deadline. "
         "All critical and high severity vulnerabilities must be patched or mitigated.",
         NOW + timedelta(days=70), 20, None, 72, 25, 8, 17),  # 32% complete, on track
        (uid(), "Zero Critical Vulnerabilities", "zero_critical",
         "Reduce critical vulnerability count to zero across all production assets. "
         "Focus on KEV-listed and actively exploited CVEs first.",
         NOW + timedelta(days=30), None, 0, 0, 5, 4, 1),  # 80% complete, ahead
        (uid(), "Risk Score Reduction Q3", "risk_reduction",
         "Reduce overall risk score by 60% before end of Q3 2026. "
         "Prioritize internet-facing assets and high-business-impact systems.",
         NOW + timedelta(days=90), 30, None, 55, 40, 6, 34),  # 15% complete, at risk
    ]
    
    goal_ids = []
    for gid, name, gtype, desc, target_date, target_risk, target_vuln_count, curr_risk, curr_vuln, patches_done, patches_left in goals:
        if exists(cur, "goals", name=name, tenant_id=TENANT_ID):
            cur.execute("SELECT id FROM goals WHERE name = %s AND tenant_id = %s", (name, TENANT_ID))
            goal_ids.append(cur.fetchone()[0])
            continue
        goal_ids.append(gid)
        cur.execute("""
            INSERT INTO goals (id, tenant_id, name, description, goal_type,
                target_completion_date, target_risk_score, target_vulnerability_count,
                risk_tolerance, status, current_risk_score, current_vulnerability_count,
                patches_completed, patches_remaining, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            gid, TENANT_ID, name, desc, gtype,
            target_date, target_risk, target_vuln_count,
            "balanced", "active", curr_risk, curr_vuln, patches_done, patches_left, NOW
        ))
    
    print(f"  ✓ Seeded {len(goals)} goals")
    return goal_ids


def seed_maintenance_windows(cur, goal_ids):
    """Create maintenance windows with varied scopes (Sprint 13)."""
    mw1_id = uid()
    mw2_id = uid()
    mw3_id = uid()
    mw4_id = uid()
    mw5_id = uid()
    mw6_id = uid()
    mw7_id = uid()
    
    # Sprint 13: Windows with priority/scoping
    # Format: (id, name, desc, type, start, end, env, max_hrs, max_assets, max_risk,
    #          priority, asset_group, service_name, is_default)
    windows = [
        # Default window (priority=0, is_default=True)
        (mw1_id, "Default Maintenance Window",
         "Fallback window for assets without specific matches. General purpose patching.",
         "scheduled",
         NOW + timedelta(days=28, hours=2),
         NOW + timedelta(days=28, hours=6),
         None, 4.0, 50, 70.0,
         0, None, None, True),
        
        # Environment-specific windows (priority=10)
        (mw2_id, "Production - General Patching",
         "Standard production maintenance window. All production systems.",
         "scheduled",
         NOW + timedelta(days=10, hours=2),
         NOW + timedelta(days=10, hours=8),
         "production", 6.0, 30, 80.0,
         10, None, None, False),
        (mw3_id, "Staging - Full Environment",
         "Full staging environment patch cycle. Used to validate patches before production rollout.",
         "scheduled",
         NOW + timedelta(days=5, hours=14),
         NOW + timedelta(days=5, hours=18),
         "staging", 4.0, 40, 60.0,
         10, None, None, False),
        
        # Service-specific windows (priority=20)
        (mw4_id, "Production - Payment Service",
         "High-priority window for payment processing service. Requires PCI compliance.",
         "scheduled",
         NOW + timedelta(days=7, hours=22),
         NOW + timedelta(days=8, hours=2),
         "production", 4.0, 6, 95.0,
         20, None, "payment-service", False),
        (mw5_id, "Staging - API Gateway",
         "Staging window for API gateway service testing before prod rollout.",
         "scheduled",
         NOW + timedelta(days=3, hours=14),
         NOW + timedelta(days=3, hours=18),
         "staging", 4.0, 8, 70.0,
         20, None, "api-gateway", False),
        
        # Emergency window
        (mw6_id, "Production - Emergency KEV Patch",
         "Emergency patching window for critical KEV-listed vulnerabilities.",
         "emergency",
         NOW + timedelta(days=1, hours=2),
         NOW + timedelta(days=1, hours=4),
         "production", 2.0, 10, 90.0,
         30, None, None, False),
        
        # Development window
        (mw7_id, "Development - Platform Updates",
         "Monthly maintenance window for development and CI/CD infrastructure.",
         "scheduled",
         NOW + timedelta(days=21, hours=10),
         NOW + timedelta(days=21, hours=14),
         "development", 4.0, 40, 40.0,
         10, None, None, False),
    ]
    
    mw_ids = []
    for mid, name, desc, mtype, start, end, env, max_hrs, max_assets, max_risk, priority, asset_group, service_name, is_default in windows:
        if exists(cur, "maintenance_windows", name=name, tenant_id=TENANT_ID):
            cur.execute("SELECT id FROM maintenance_windows WHERE name = %s AND tenant_id = %s", (name, TENANT_ID))
            mw_ids.append(cur.fetchone()[0])
            continue
        mw_ids.append(mid)
        cur.execute("""
            INSERT INTO maintenance_windows (id, tenant_id, name, description, type,
                start_time, end_time, timezone, max_duration_hours, max_assets,
                max_risk_score, environment, priority, asset_group, service_name, is_default,
                active, approved, change_freeze, notification_sent, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            mid, TENANT_ID, name, desc, mtype,
            start, end, "America/New_York", max_hrs, max_assets,
            max_risk, env, priority, asset_group, service_name, is_default,
            True, True, False, False, NOW, NOW
        ))
    
    print(f"  ✓ Seeded {len(windows)} maintenance windows (Sprint 13: with priority/scoping)")
    
    # Create bundles for maintenance windows with realistic assignments
    bundles = [
        (uid(), goal_ids[0] if len(goal_ids) > 0 else None, mw_ids[0],
         "Emergency KEV Patch Bundle",
         "Critical patches for CVE-2024-21762 (FortiOS) and CVE-2024-3400 (PAN-OS) on internet-facing systems.",
         "approved", 92.5, "CRITICAL", 4, True, 90),
        (uid(), goal_ids[1] if len(goal_ids) > 1 else None, mw_ids[1],
         "Database Tier Security Updates",
         "Patches for database servers including PostgreSQL and OS-level vulnerabilities.",
         "scheduled", 68.0, "HIGH", 8, True, 180),
        (uid(), goal_ids[2] if len(goal_ids) > 2 else None, mw_ids[2],
         "Staging Pre-Production Validation",
         "Complete patch cycle for staging environment validation before prod rollout.",
         "scheduled", 55.0, "MEDIUM", 12, False, 120),
        (uid(), goal_ids[0] if len(goal_ids) > 0 else None, mw_ids[3],
         "DR Infrastructure Updates",
         "Quarterly updates for backup and disaster recovery systems.",
         "draft", 32.0, "LOW", 6, False, 60),
    ]
    
    bundle_ids = []
    for bid, gid, mwid, name, desc, status, risk, risk_level, asset_count, approval_required, est_minutes in bundles:
        if exists(cur, "bundles", name=name, tenant_id=TENANT_ID):
            continue
        bundle_ids.append(bid)
        cur.execute("""
            INSERT INTO bundles (id, tenant_id, goal_id, maintenance_window_id, name, description,
                status, risk_score, risk_level, assets_affected_count, approval_required,
                estimated_duration_minutes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            bid, TENANT_ID, gid, mwid, name, desc,
            status, risk, risk_level, asset_count, approval_required, est_minutes,
            NOW, NOW
        ))
    
    print(f"  ✓ Seeded {len(bundles)} bundles")
    
    # Now populate bundle_items to link bundles to actual asset-vuln pairs
    cur.execute("""
        SELECT av.id, av.asset_id, av.vulnerability_id, av.risk_score 
        FROM asset_vulnerabilities av
        JOIN vulnerabilities v ON v.id = av.vulnerability_id
        WHERE av.status = 'open'
        ORDER BY av.risk_score DESC
        LIMIT 30
    """)
    asset_vulns = cur.fetchall()
    
    # Distribute asset-vulns across bundles
    items_count = 0
    for i, (av_id, asset_id, vuln_id, risk_score) in enumerate(asset_vulns):
        # First 4 items go to emergency bundle, next 8 to DB bundle, etc.
        if i < 4:
            bundle_id = bundle_ids[0] if len(bundle_ids) > 0 else None
        elif i < 12:
            bundle_id = bundle_ids[1] if len(bundle_ids) > 1 else None
        elif i < 24:
            bundle_id = bundle_ids[2] if len(bundle_ids) > 2 else None
        else:
            bundle_id = bundle_ids[3] if len(bundle_ids) > 3 else None
        
        if bundle_id:
            cur.execute("""
                INSERT INTO bundle_items (id, bundle_id, asset_vulnerability_id, execution_order,
                    estimated_duration_minutes, rollback_plan, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), bundle_id, av_id, i % 10,
                15 + (hash(str(av_id)) % 30),  # 15-45 minutes per patch
                "Standard rollback: restore from snapshot, restart service",
                NOW
            ))
            items_count += 1
    
    print(f"  ✓ Seeded {items_count} bundle items")
    return mw_ids


def seed_connections(cur):
    """Create sample external connections."""
    connections = [
        {
            "provider": "aws",
            "name": "AWS Production Account",
            "config": {
                "access_key_id": "AKIADEMO12345678",
                "secret_access_key": "demo-secret-key-for-testing",
                "region": "us-east-1",
            },
            "status": "active",
        },
        {
            "provider": "azure",
            "name": "Azure Enterprise Subscription",
            "config": {
                "tenant_id": "demo-tenant-id",
                "client_id": "demo-client-id",
                "client_secret": "demo-client-secret",
                "subscription_id": "demo-subscription-id",
            },
            "status": "pending",
        },
        {
            "provider": "jira",
            "name": "Jira Cloud",
            "config": {
                "url": "https://demo.atlassian.net",
                "email": "admin@demo.patchguide.ai",
                "api_token": "demo-jira-token",
                "project_key": "PATCH",
            },
            "status": "error",
            "last_error": "Authentication failed: Invalid credentials",
        },
    ]
    
    conn_count = 0
    for conn_data in connections:
        conn_id = uid()
        if not exists(cur, "connections", id=conn_id):
            cur.execute("""
                INSERT INTO connections (id, tenant_id, provider, name, config, status, last_error, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                conn_id, TENANT_ID, conn_data["provider"], conn_data["name"],
                Json(conn_data["config"]), conn_data["status"],
                conn_data.get("last_error"), NOW
            ))
            conn_count += 1
    
    print(f"  ✓ Seeded {conn_count} connections")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    # Normalize URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else 'configured'}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        print("\nSeeding demo data...")
        seed_tenant(cur)
        seed_user(cur)
        seed_connections(cur)
        vuln_ids = seed_vulnerabilities(cur)
        asset_ids = seed_assets(cur)
        seed_asset_vulnerabilities(cur, vuln_ids, asset_ids)
        goal_ids = seed_goals(cur)
        seed_maintenance_windows(cur, goal_ids)
        
        conn.commit()
        print("\n✅ Demo data seeded successfully!")
        
        # Summary
        cur.execute("SELECT COUNT(*) FROM vulnerabilities")
        print(f"   Vulnerabilities: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM assets WHERE tenant_id = %s", (TENANT_ID,))
        print(f"   Assets: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM asset_vulnerabilities")
        print(f"   Asset-Vuln links: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM goals WHERE tenant_id = %s", (TENANT_ID,))
        print(f"   Goals: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM maintenance_windows WHERE tenant_id = %s", (TENANT_ID,))
        print(f"   Maintenance Windows: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM bundles WHERE tenant_id = %s", (TENANT_ID,))
        print(f"   Bundles: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM connections WHERE tenant_id = %s", (TENANT_ID,))
        print(f"   Connections: {cur.fetchone()[0]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
