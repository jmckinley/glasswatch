"""
External Webhook Simulators

Accepts payloads from Tenable, Qualys, Rapid7, Slack, and Jira.
Scanner webhooks are authenticated via X-Webhook-Secret header matched
against tenant.settings.integrations.snapper_webhook_secret.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.asset import Asset
from backend.models.vulnerability import Vulnerability
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.audit_log import AuditLog


router = APIRouter()


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def get_tenant_from_webhook_secret(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Authenticate webhook via X-Webhook-Secret header."""
    secret = request.headers.get("X-Webhook-Secret")
    if not secret:
        raise HTTPException(status_code=401, detail="X-Webhook-Secret header required")

    result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    tenants = result.scalars().all()
    for tenant in tenants:
        stored = (tenant.settings or {}).get("integrations", {}).get("snapper_webhook_secret")
        if stored and stored == secret:
            return tenant
    raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ---------------------------------------------------------------------------
# Severity mappings
# ---------------------------------------------------------------------------

TENABLE_SEVERITY_MAP = {
    4: "CRITICAL",
    3: "HIGH",
    2: "MEDIUM",
    1: "LOW",
    0: "LOW",
}

QUALYS_SEVERITY_MAP = {
    5: "CRITICAL",
    4: "HIGH",
    3: "MEDIUM",
    2: "LOW",
    1: "LOW",
}

RAPID7_SEVERITY_MAP = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
    "informational": "LOW",
    "moderate": "MEDIUM",
    "severe": "HIGH",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _upsert_asset(db: AsyncSession, tenant_id, identifier: str, name: str, ip: str, os_name: str, platform: str = "unknown") -> Asset:
    """Get or create an Asset record."""
    result = await db.execute(
        select(Asset).where(Asset.tenant_id == tenant_id, Asset.identifier == identifier)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        asset = Asset(
            tenant_id=tenant_id,
            identifier=identifier,
            name=name or identifier,
            type="server",
            platform=platform,
            environment="production",
            ip_addresses=[ip] if ip else [],
            fqdn=name if "." in (name or "") else None,
            os_family=os_name.split()[0].lower() if os_name else None,
            os_version=os_name,
            criticality=3,
            exposure="INTRANET",
        )
        db.add(asset)
        await db.flush()
    return asset


async def _upsert_vulnerability(db: AsyncSession, cve_id: str, title: str, severity: str, source: str, cvss_score: Optional[float] = None) -> Vulnerability:
    """Get or create a Vulnerability record."""
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.identifier == cve_id)
    )
    vuln = result.scalar_one_or_none()
    if not vuln:
        vuln = Vulnerability(
            identifier=cve_id,
            source=source,
            title=title or cve_id,
            severity=severity,
            cvss_score=cvss_score,
            patch_available=False,
        )
        db.add(vuln)
        await db.flush()
    return vuln


async def _link_asset_vulnerability(db: AsyncSession, asset: Asset, vuln: Vulnerability, scanner: str) -> bool:
    """Create AssetVulnerability link if not already present. Returns True if created."""
    result = await db.execute(
        select(AssetVulnerability).where(
            AssetVulnerability.asset_id == asset.id,
            AssetVulnerability.vulnerability_id == vuln.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return False
    av = AssetVulnerability(
        asset_id=asset.id,
        vulnerability_id=vuln.id,
        discovered_by=scanner,
        risk_score=0,
    )
    db.add(av)
    return True


# ---------------------------------------------------------------------------
# Health endpoint (no auth)
# ---------------------------------------------------------------------------

@router.get("/health")
async def webhook_health():
    """Health check — no authentication required."""
    return {"status": "ok", "version": "1.0"}


# ---------------------------------------------------------------------------
# Tenable scanner webhook
# ---------------------------------------------------------------------------

@router.post("/scanner/tenable")
async def tenable_webhook(
    body: Dict[str, Any],
    tenant: Tenant = Depends(get_tenant_from_webhook_secret),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept Tenable export format:
    {
      "assets": [{"id": "uuid", "fqdn": ["host.example.com"], "ipv4": ["10.0.0.1"], "operating_system": ["Linux"]}],
      "vulnerabilities": [{"plugin_id": 12345, "cve": ["CVE-2024-1234"], "severity": 4, "asset_id": "uuid", "plugin_name": "..."}]
    }
    """
    assets_raw = body.get("assets", [])
    vulns_raw = body.get("vulnerabilities", [])

    # Build asset lookup by Tenable asset id
    asset_map: Dict[str, Asset] = {}
    assets_created = 0
    for a in assets_raw:
        asset_id = str(a.get("id", ""))
        fqdns = a.get("fqdn", [])
        ips = a.get("ipv4", [])
        os_list = a.get("operating_system", [])
        identifier = fqdns[0] if fqdns else (ips[0] if ips else asset_id)
        name = fqdns[0] if fqdns else identifier
        ip = ips[0] if ips else ""
        os_name = os_list[0] if os_list else ""

        asset = await _upsert_asset(db, tenant.id, identifier, name, ip, os_name)
        asset_map[asset_id] = asset
        assets_created += 1

    vulns_created = 0
    links_created = 0
    for v in vulns_raw:
        cves = v.get("cve", [])
        if not cves:
            cves = [f"PLUGIN-{v.get('plugin_id', 'unknown')}"]
        sev_int = v.get("severity", 2)
        severity = TENABLE_SEVERITY_MAP.get(sev_int, "MEDIUM")
        title = v.get("plugin_name", cves[0])
        asset_id = str(v.get("asset_id", ""))
        asset = asset_map.get(asset_id)

        for cve in cves:
            vuln = await _upsert_vulnerability(db, cve, title, severity, "tenable")
            vulns_created += 1
            if asset:
                created = await _link_asset_vulnerability(db, asset, vuln, "tenable")
                if created:
                    links_created += 1

    await db.commit()
    return {
        "processed": len(vulns_raw),
        "assets_created": assets_created,
        "vulns_created": vulns_created,
    }


# ---------------------------------------------------------------------------
# Qualys scanner webhook
# ---------------------------------------------------------------------------

@router.post("/scanner/qualys")
async def qualys_webhook(
    body: Dict[str, Any],
    tenant: Tenant = Depends(get_tenant_from_webhook_secret),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept Qualys HOST_LIST_VM_DETECTION_OUTPUT format.
    """
    try:
        host_list = (
            body
            .get("HOST_LIST_VM_DETECTION_OUTPUT", {})
            .get("RESPONSE", {})
            .get("HOST_LIST", {})
            .get("HOST", [])
        )
    except (AttributeError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid Qualys payload structure")

    if isinstance(host_list, dict):
        host_list = [host_list]

    assets_created = 0
    vulns_created = 0

    for host in host_list:
        ip = host.get("IP", "")
        dns = host.get("DNS", ip)
        identifier = dns or ip
        asset = await _upsert_asset(db, tenant.id, identifier, dns, ip, "")
        assets_created += 1

        detections = host.get("DETECTION_LIST", {}).get("DETECTION", [])
        if isinstance(detections, dict):
            detections = [detections]

        for det in detections:
            sev_int = int(det.get("SEVERITY", 2))
            severity = QUALYS_SEVERITY_MAP.get(sev_int, "MEDIUM")
            cve_data = det.get("CVE_LIST", {}).get("CVE", {})
            if isinstance(cve_data, dict):
                cve_list = [cve_data.get("ID", f"QID-{det.get('QID', 'unknown')}")]
            elif isinstance(cve_data, list):
                cve_list = [c.get("ID") for c in cve_data if c.get("ID")]
            else:
                cve_list = [f"QID-{det.get('QID', 'unknown')}"]

            for cve in cve_list:
                vuln = await _upsert_vulnerability(db, cve, cve, severity, "qualys")
                vulns_created += 1
                await _link_asset_vulnerability(db, asset, vuln, "qualys")

    await db.commit()
    return {
        "processed": len(host_list),
        "assets_created": assets_created,
        "vulns_created": vulns_created,
    }


# ---------------------------------------------------------------------------
# Rapid7 InsightVM webhook
# ---------------------------------------------------------------------------

@router.post("/scanner/rapid7")
async def rapid7_webhook(
    body: Dict[str, Any],
    tenant: Tenant = Depends(get_tenant_from_webhook_secret),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept Rapid7 InsightVM format:
    {"assets": [{"ip": "10.0.0.1", "hostName": "host.example.com",
                 "vulnerabilities": [{"id": "CVE-...", "title": "...", "severity": "Critical", "cvssScore": 9.8}]}]}
    """
    assets_raw = body.get("assets", [])
    assets_created = 0
    vulns_created = 0

    for a in assets_raw:
        ip = a.get("ip", "")
        hostname = a.get("hostName", ip)
        identifier = hostname or ip
        asset = await _upsert_asset(db, tenant.id, identifier, hostname, ip, "")
        assets_created += 1

        for v in a.get("vulnerabilities", []):
            cve = v.get("id", "")
            if not cve:
                continue
            title = v.get("title", cve)
            sev_str = v.get("severity", "medium").lower()
            severity = RAPID7_SEVERITY_MAP.get(sev_str, "MEDIUM")
            cvss = v.get("cvssScore")

            vuln = await _upsert_vulnerability(db, cve, title, severity, "rapid7", cvss_score=float(cvss) if cvss is not None else None)
            vulns_created += 1
            await _link_asset_vulnerability(db, asset, vuln, "rapid7")

    await db.commit()
    return {
        "processed": len(assets_raw),
        "assets_created": assets_created,
        "vulns_created": vulns_created,
    }


# ---------------------------------------------------------------------------
# Slack events API
# ---------------------------------------------------------------------------

@router.post("/slack/events")
async def slack_events(body: Dict[str, Any]):
    """
    Slack Events API callback.
    Handles URL verification challenge and acknowledges other events.
    No authentication required — Slack uses signing secret validation separately.
    """
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    return {"ok": True}


# ---------------------------------------------------------------------------
# Jira webhook
# ---------------------------------------------------------------------------

@router.post("/jira/webhook")
async def jira_webhook(
    body: Dict[str, Any],
    tenant: Tenant = Depends(get_tenant_from_webhook_secret),
    db: AsyncSession = Depends(get_db),
):
    """
    Jira webhook callback.
    Logs the event to audit_logs and acknowledges.
    """
    issue = body.get("issue", {})
    issue_key = issue.get("key", "unknown")

    await AuditLog.log_action(
        db_session=db,
        tenant_id=tenant.id,
        user_id=None,
        action="jira_webhook",
        resource_type="jira_issue",
        resource_id=issue_key,
        details=body,
    )
    await db.commit()
    return {"received": True}
