"""
Enhanced seed data for Glasswatch - expands the demo data significantly.

This is a supplement to seed_demo.py that adds:
- 50+ additional vulnerabilities
- 20+ additional assets  
- More diverse asset-vulnerability associations with runtime data
- 2 additional goals
- 3 additional maintenance windows

Usage:
    Run after seed_demo.py to expand the dataset
    PYTHONPATH=/home/node/glasswatch DATABASE_URL="postgresql://..." \
        python3 backend/scripts/seed_demo_enhanced.py
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

psycopg2.extras.register_uuid()

TENANT_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
NOW = datetime.now(timezone.utc)

def uid():
    return uuid.uuid4()

def exists(cur, table, **kwargs):
    """Check if a row exists."""
    conditions = " AND ".join(f"{k} = %s" for k in kwargs)
    cur.execute(f"SELECT 1 FROM {table} WHERE {conditions} LIMIT 1", list(kwargs.values()))
    return cur.fetchone() is not None

def seed_additional_vulnerabilities(cur):
    """Add 50+ more vulnerabilities for testing optimization."""
    vulns = [
        # More Critical
        ("CVE-2024-43451", "critical", 9.9, 0.93, True, True,
         "Windows NTLM Hash Disclosure", "Information disclosure vulnerability allowing NTLM hash disclosure."),
        ("CVE-2024-38812", "critical", 9.8, 0.88, True, True,
         "vCenter Server RCE", "Remote code execution in VMware vCenter Server."),
        ("CVE-2024-26234", "critical", 10.0, 0.96, True, True,
         "Proxy Overflow", "Heap overflow in Squid proxy server."),
        ("CVE-2024-33891", "critical", 9.8, 0.91, True, True,
         "GitLab Account Takeover", "Authentication bypass in GitLab CE/EE."),
        ("CVE-2024-42315", "critical", 9.9, 0.87, True, True,
         "Apache Struts2 OGNL Injection", "Remote code execution via OGNL injection."),
        
        # More High
        ("CVE-2024-51021", "high", 8.8, 0.74, False, True,
         "Kubernetes Privilege Escalation", "Privilege escalation in Kubernetes kubelet."),
        ("CVE-2024-49012", "high", 8.1, 0.69, True, True,
         "Docker Engine Escape", "Container escape vulnerability in Docker Engine."),
        ("CVE-2024-47832", "high", 8.5, 0.72, True, True,
         "PostgreSQL Buffer Overflow", "Buffer overflow in PostgreSQL server."),
        ("CVE-2024-46211", "high", 8.2, 0.67, False, True,
         "Redis RCE", "Remote code execution in Redis server."),
        ("CVE-2024-45190", "high", 8.0, 0.64, True, True,
         "Nginx Path Traversal", "Path traversal in nginx web server."),
        ("CVE-2024-44523", "high", 7.8, 0.61, False, True,
         "MySQL Injection", "SQL injection in MySQL server."),
        ("CVE-2024-43902", "high", 7.5, 0.59, False, True,
         "Tomcat Session Hijacking", "Session fixation in Apache Tomcat."),
        ("CVE-2024-42761", "high", 8.3, 0.70, True, True,
         "Elasticsearch RCE", "Remote code execution in Elasticsearch."),
        ("CVE-2024-41834", "high", 7.9, 0.63, False, True,
         "MongoDB NoSQL Injection", "NoSQL injection in MongoDB."),
        ("CVE-2024-40912", "high", 8.1, 0.66, True, True,
         "RabbitMQ Auth Bypass", "Authentication bypass in RabbitMQ."),
        ("CVE-2024-39701", "high", 7.7, 0.60, False, True,
         "Jenkins Plugin RCE", "Code execution in Jenkins plugin."),
        ("CVE-2024-38594", "high", 8.0, 0.65, False, True,
         "Grafana Path Traversal", "Path traversal in Grafana."),
        ("CVE-2024-37283", "high", 7.8, 0.62, True, True,
         "Prometheus DoS", "Denial of service in Prometheus."),
        ("CVE-2024-36172", "high", 8.2, 0.68, False, True,
         "Harbor Registry Bypass", "Authentication bypass in Harbor."),
        ("CVE-2024-35061", "high", 7.6, 0.58, False, True,
         "Vault Secret Leak", "Information disclosure in HashiCorp Vault."),
        
        # More Medium
        ("CVE-2024-52341", "medium", 6.5, 0.34, False, True,
         "Node.js Prototype Pollution", "Prototype pollution in Node.js packages."),
        ("CVE-2024-51220", "medium", 6.3, 0.32, False, True,
         "Python Pickle RCE", "Insecure deserialization in Python."),
        ("CVE-2024-50119", "medium", 6.8, 0.36, False, True,
         "Ruby on Rails SQL Injection", "SQL injection in ActiveRecord."),
        ("CVE-2024-49008", "medium", 6.2, 0.30, False, True,
         "Django CSRF Bypass", "CSRF protection bypass in Django."),
        ("CVE-2024-47897", "medium", 5.9, 0.27, False, True,
         "Flask Session Tampering", "Session tampering in Flask."),
        ("CVE-2024-46786", "medium", 6.4, 0.33, False, True,
         "Spring Boot Info Disclosure", "Information disclosure in Spring Boot."),
        ("CVE-2024-45675", "medium", 6.1, 0.29, False, True,
         ".NET Core XSS", "Cross-site scripting in ASP.NET Core."),
        ("CVE-2024-44564", "medium", 5.8, 0.26, False, True,
         "React XSS", "Cross-site scripting via React component."),
        ("CVE-2024-43453", "medium", 6.0, 0.28, False, True,
         "Angular Template Injection", "Template injection in Angular."),
        ("CVE-2024-42342", "medium", 5.7, 0.24, False, False,
         "Vue.js DOM XSS", "DOM-based XSS in Vue.js."),
        ("CVE-2024-41231", "medium", 6.3, 0.31, False, True,
         "Express.js Path Traversal", "Path traversal in Express.js."),
        ("CVE-2024-40120", "medium", 5.5, 0.23, False, True,
         "Laravel Mass Assignment", "Mass assignment vulnerability in Laravel."),
        ("CVE-2024-39019", "medium", 6.2, 0.30, False, True,
         "Symfony Security Bypass", "Security component bypass in Symfony."),
        ("CVE-2024-37908", "medium", 5.9, 0.27, False, True,
         "FastAPI Injection", "Query parameter injection in FastAPI."),
        ("CVE-2024-36797", "medium", 6.1, 0.29, False, True,
         "Sanic SSRF", "Server-side request forgery in Sanic."),
        
        # More Low
        ("CVE-2024-53412", "low", 3.9, 0.09, False, True,
         "jQuery DOM XSS", "DOM-based XSS in jQuery."),
        ("CVE-2024-52301", "low", 3.7, 0.08, False, False,
         "Bootstrap CSS Injection", "CSS injection in Bootstrap."),
        ("CVE-2024-51190", "low", 3.3, 0.06, False, False,
         "Lodash Prototype Pollution", "Low-impact prototype pollution."),
        ("CVE-2024-50081", "low", 3.1, 0.05, False, False,
         "Moment.js DoS", "ReDoS in moment.js parsing."),
        ("CVE-2024-48970", "low", 2.9, 0.04, False, False,
         "Axios SSRF", "Minor SSRF in axios library."),
        ("CVE-2024-47861", "low", 3.5, 0.07, False, True,
         "Webpack Info Leak", "Source map information leakage."),
        ("CVE-2024-46752", "low", 3.2, 0.06, False, False,
         "Babel Transform Bypass", "Security transform bypass."),
        ("CVE-2024-45643", "low", 2.8, 0.04, False, False,
         "ESLint Config Bypass", "Security rule bypass."),
        ("CVE-2024-44534", "low", 3.4, 0.07, False, True,
         "Prettier Code Injection", "Template injection in formatting."),
        ("CVE-2024-43425", "low", 3.0, 0.05, False, False,
         "TypeScript Type Confusion", "Type confusion issue."),
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
            NOW - timedelta(days=10 + hash(cve) % 120),
            NOW
        ))
    
    print(f"  ✓ Added {len(vulns)} additional vulnerabilities")
    return vuln_ids

def seed_additional_assets(cur):
    """Add 20+ more assets for richer optimization scenarios."""
    assets = [
        # More Production Servers
        ("PROD-WEB-03", "prod-web-03.acme.internal", "server", "linux", "production",
         "internet-facing", 9, "Web Services", "Ubuntu", "22.04 LTS",
         ["web-tier", "pci-scope", "internet-facing", "deploy-group-b"], "web-prod"),
        ("PROD-APP-01", "prod-app-01.acme.internal", "server", "linux", "production",
         "internal", 8, "Application Services", "Red Hat Enterprise Linux", "8.8",
         ["app-tier", "pci-scope", "deploy-group-a"], "app-prod"),
        ("PROD-APP-02", "prod-app-02.acme.internal", "server", "linux", "production",
         "internal", 8, "Application Services", "Red Hat Enterprise Linux", "8.8",
         ["app-tier", "pci-scope", "deploy-group-a"], "app-prod"),
        ("PROD-CACHE-01", "prod-cache-01.acme.internal", "server", "linux", "production",
         "internal", 7, "Data Services", "Ubuntu", "22.04 LTS",
         ["cache-tier", "deploy-group-b"], "cache-prod"),
        ("PROD-QUEUE-01", "prod-queue-01.acme.internal", "server", "linux", "production",
         "internal", 7, "Integration Services", "Ubuntu", "22.04 LTS",
         ["queue-tier", "deploy-group-b"], "queue-prod"),
        
        # More Staging
        ("STG-DB-01", "stg-db-01.acme.internal", "database", "linux", "staging",
         "internal", 4, "Data Services", "PostgreSQL", "15.4",
         ["staging", "database-tier"], "staging"),
        ("STG-APP-01", "stg-app-01.acme.internal", "server", "linux", "staging",
         "internal", 5, "Application Services", "Ubuntu", "22.04 LTS",
         ["staging", "app-tier"], "staging"),
        ("STG-APP-02", "stg-app-02.acme.internal", "server", "linux", "staging",
         "internal", 5, "Application Services", "Ubuntu", "22.04 LTS",
         ["staging", "app-tier"], "staging"),
        
        # More Kubernetes
        ("K8S-NODE-03", "k8s-node-03.acme.internal", "container", "linux", "production",
         "internal", 7, "Platform Engineering", "Flatcar Container Linux", "3815",
         ["k8s-workload", "container-host", "deploy-group-b"], "k8s-prod"),
        ("K8S-NODE-04", "k8s-node-04.acme.internal", "container", "linux", "production",
         "internal", 7, "Platform Engineering", "Flatcar Container Linux", "3815",
         ["k8s-workload", "container-host", "deploy-group-b"], "k8s-prod"),
        ("K8S-MASTER-01", "k8s-master-01.acme.internal", "container", "linux", "production",
         "internal", 9, "Platform Engineering", "Ubuntu", "22.04 LTS",
         ["k8s-control-plane", "critical-infra", "deploy-group-c"], "k8s-prod"),
        
        # Windows Servers
        ("WIN-APP-01", "win-app-01.acme.internal", "server", "windows", "production",
         "internal", 7, "Application Services", "Windows Server", "2022",
         ["app-tier", "windows", "deploy-group-c"], "windows-prod"),
        ("WIN-DB-01", "win-db-01.acme.internal", "database", "windows", "production",
         "internal", 9, "Data Services", "Windows Server", "2022",
         ["database-tier", "windows", "pci-scope", "deploy-group-c"], "windows-prod"),
        ("WIN-FILE-01", "win-file-01.acme.internal", "server", "windows", "production",
         "internal", 6, "IT Operations", "Windows Server", "2019",
         ["file-services", "windows", "deploy-group-c"], "windows-prod"),
        
        # Network & Security
        ("LB-PROD-01", "lb-prod-01.acme.internal", "server", "other", "production",
         "internet-facing", 10, "Network Operations", "F5 BIG-IP", "17.1.0",
         ["load-balancer", "internet-facing", "critical-infra"], "network-prod"),
        ("VPN-EDGE-01", "vpn-edge-01.acme.internal", "server", "other", "production",
         "internet-facing", 8, "Network Security", "Cisco IOS", "15.9",
         ["vpn", "internet-facing", "remote-access"], "network-prod"),
        
        # Development
        ("DEV-WEB-01", "dev-web-01.acme.internal", "server", "linux", "development",
         "internal", 2, "Engineering", "Ubuntu", "24.04 LTS",
         ["development", "web-tier"], "dev"),
        ("DEV-DB-01", "dev-db-01.acme.internal", "database", "linux", "development",
         "internal", 2, "Engineering", "PostgreSQL", "16.0",
         ["development", "database-tier"], "dev"),
        
        # Testing
        ("TEST-APP-01", "test-app-01.acme.internal", "server", "linux", "testing",
         "internal", 4, "QA", "Ubuntu", "22.04 LTS",
         ["testing", "app-tier"], "testing"),
        ("TEST-API-01", "test-api-01.acme.internal", "server", "linux", "testing",
         "internal", 4, "QA", "Ubuntu", "22.04 LTS",
         ["testing", "api-tier"], "testing"),
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
    
    print(f"  ✓ Added {len(assets)} additional assets")
    return asset_ids

def seed_enhanced_asset_vulnerabilities(cur, all_vuln_ids, all_asset_ids):
    """Create asset-vulnerability associations with runtime data for realistic scoring."""
    # This creates more interesting associations with varied runtime execution states
    count = 0
    
    # Get a sample of critical/high vulns for heavy exposure
    critical_vulns = all_vuln_ids[:10]  # Assume first vulns are critical
    high_vulns = all_vuln_ids[10:25]
    medium_vulns = all_vuln_ids[25:40]
    low_vulns = all_vuln_ids[40:]
    
    # Production assets get more critical vulns
    prod_assets = all_asset_ids[:15]  # First assets are production
    staging_assets = all_asset_ids[15:20]
    dev_assets = all_asset_ids[20:]
    
    # Scenario 1: Some prod assets have many critical vulns with code execution confirmed
    for aid in prod_assets[:5]:
        for vid in critical_vulns[:4]:
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            cur.execute("""
                INSERT INTO asset_vulnerabilities (
                    id, asset_id, vulnerability_id, discovered_at, discovered_by,
                    status, patch_available, code_executed, library_loaded,
                    execution_frequency, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=5 + hash(str(vid)) % 30),
                "snapper",
                "ACTIVE", True, True, True, "high", NOW
            ))
            count += 1
    
    # Scenario 2: Some assets have vulns where library is loaded but not executed
    for aid in prod_assets[5:10]:
        for vid in high_vulns[:3]:
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            cur.execute("""
                INSERT INTO asset_vulnerabilities (
                    id, asset_id, vulnerability_id, discovered_at, discovered_by,
                    status, patch_available, code_executed, library_loaded,
                    execution_frequency, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=10 + hash(str(vid)) % 40),
                "snapper",
                "ACTIVE", True, False, True, "medium", NOW
            ))
            count += 1
    
    # Scenario 3: Some have vulns not loaded at all (lower priority)
    for aid in prod_assets[10:15]:
        for vid in medium_vulns[:5]:
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            cur.execute("""
                INSERT INTO asset_vulnerabilities (
                    id, asset_id, vulnerability_id, discovered_at, discovered_by,
                    status, patch_available, code_executed, library_loaded,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=20 + hash(str(vid)) % 50),
                "qualys",
                "ACTIVE", True, False, False, NOW
            ))
            count += 1
    
    # Staging gets medium severity
    for aid in staging_assets:
        for vid in medium_vulns[:3]:
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            cur.execute("""
                INSERT INTO asset_vulnerabilities (
                    id, asset_id, vulnerability_id, discovered_at, discovered_by,
                    status, patch_available, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=15 + hash(str(vid)) % 45),
                "qualys",
                "ACTIVE", True, NOW
            ))
            count += 1
    
    # Dev gets low severity
    for aid in dev_assets:
        for vid in low_vulns[:2]:
            if exists(cur, "asset_vulnerabilities", asset_id=aid, vulnerability_id=vid):
                continue
            cur.execute("""
                INSERT INTO asset_vulnerabilities (
                    id, asset_id, vulnerability_id, discovered_at, discovered_by,
                    status, patch_available, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                uid(), aid, vid,
                NOW - timedelta(days=30 + hash(str(vid)) % 60),
                "snyk",
                "ACTIVE", False, NOW
            ))
            count += 1
    
    print(f"  ✓ Created {count} enhanced asset-vulnerability associations")
    return count

def seed_additional_goals(cur):
    """Add 2 more goals with different strategies."""
    goals = [
        (uid(), "Container Security Hardening", "kev_elimination",
         "Eliminate all KEV-listed vulnerabilities from container infrastructure. "
         "Focus on Kubernetes nodes and container hosts with confirmed code execution.",
         NOW + timedelta(days=45), None, 0, 0, 12, 10, 2),
        (uid(), "PCI-DSS Quarterly Patching", "compliance_deadline",
         "Quarterly PCI-DSS compliance patching cycle. All in-scope systems must be "
         "patched for critical/high vulnerabilities within regulatory timeline.",
         NOW + timedelta(days=85), 20, None, 45, 65, 18, 47),
    ]
    
    goal_ids = []
    for gid, name, gtype, desc, target_date, target_risk, target_vuln_count, curr_risk, curr_vuln, patches_done, patches_left in goals:
        if exists(cur, "goals", name=name, tenant_id=TENANT_ID):
            cur.execute("SELECT id FROM goals WHERE name = %s AND tenant_id = %s", (name, TENANT_ID))
            goal_ids.append(cur.fetchone()[0])
            continue
        goal_ids.append(gid)
        cur.execute("""
            INSERT INTO goals (
                id, tenant_id, name, type, description, target_date, target_metric,
                target_value, active, progress_percentage, vulnerabilities_total,
                current_risk_score, patches_deployed, patches_remaining,
                max_vulns_per_window, max_downtime_hours, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            gid, TENANT_ID, name, gtype, desc, target_date, "risk_score",
            target_risk if target_risk else target_vuln_count,
            True,
            (patches_done / (patches_done + patches_left) * 100) if patches_done + patches_left > 0 else 0,
            curr_vuln, curr_risk, patches_done, patches_left,
            10, 4.0, NOW
        ))
    
    print(f"  ✓ Added {len(goals)} additional goals")
    return goal_ids

def seed_additional_windows(cur):
    """Add 3 more maintenance windows with different characteristics."""
    windows = [
        (uid(), "Staging Weekly Patch", "staging", "Weekly staging environment patching",
         NOW + timedelta(days=3, hours=2), NOW + timedelta(days=3, hours=6),
         4.0, None, None, None, False),
        (uid(), "Production Monthly Emergency", "production", "Emergency production patching window",
         NOW + timedelta(days=7, hours=3), NOW + timedelta(days=7, hours=5),
         2.0, 80.0, 10, 30, False),
        (uid(), "Holiday Blackout", "production", "No patching during holiday period",
         NOW + timedelta(days=60), NOW + timedelta(days=65),
         0.0, None, None, None, True),  # Blackout window
    ]
    
    window_ids = []
    for wid, name, env, desc, start, end, duration, max_risk, max_assets, max_downtime, blackout in windows:
        if exists(cur, "maintenance_windows", name=name, tenant_id=TENANT_ID):
            cur.execute("SELECT id FROM maintenance_windows WHERE name = %s AND tenant_id = %s", (name, TENANT_ID))
            window_ids.append(cur.fetchone()[0])
            continue
        window_ids.append(wid)
        cur.execute("""
            INSERT INTO maintenance_windows (
                id, tenant_id, name, environment, description, start_time, end_time,
                duration_hours, max_risk_score, max_assets, max_downtime_minutes,
                is_blackout, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            wid, TENANT_ID, name, env, desc, start, end, duration,
            max_risk, max_assets,
            int(max_downtime * 60) if max_downtime else None,
            blackout, NOW
        ))
    
    print(f"  ✓ Added {len(windows)} additional maintenance windows")
    return window_ids

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    try:
        print("\n🌱 Seeding enhanced demo data...\n")
        
        # Add more vulnerabilities
        vuln_ids = seed_additional_vulnerabilities(cur)
        
        # Add more assets
        asset_ids = seed_additional_assets(cur)
        
        # Get ALL existing vulnerabilities and assets for associations
        cur.execute("SELECT id FROM vulnerabilities ORDER BY created_at")
        all_vuln_ids = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT id FROM assets WHERE tenant_id = %s ORDER BY criticality DESC, created_at", (TENANT_ID,))
        all_asset_ids = [row[0] for row in cur.fetchall()]
        
        # Create enhanced asset-vulnerability associations
        seed_enhanced_asset_vulnerabilities(cur, all_vuln_ids, all_asset_ids)
        
        # Add more goals
        seed_additional_goals(cur)
        
        # Add more maintenance windows
        seed_additional_windows(cur)
        
        conn.commit()
        
        # Print summary
        print("\n✅ Enhanced seeding complete!\n")
        print("Summary:")
        cur.execute("SELECT COUNT(*) FROM vulnerabilities")
        print(f"  Total vulnerabilities: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM assets WHERE tenant_id = %s", (TENANT_ID,))
        print(f"  Total assets: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM asset_vulnerabilities")
        print(f"  Total asset-vulnerability links: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM goals WHERE tenant_id = %s", (TENANT_ID,))
        print(f"  Total goals: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM maintenance_windows WHERE tenant_id = %s", (TENANT_ID,))
        print(f"  Total maintenance windows: {cur.fetchone()[0]}")
        print()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}\n")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
