"""
Reporting & Compliance API endpoints.

Provides compliance framework status, MTTP metrics, SLA tracking,
and executive summary for PDF export.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.vulnerability import Vulnerability
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.bundle import Bundle
from backend.models.goal import Goal
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant

router = APIRouter()

SLA_DAYS = {
    "CRITICAL": 7,
    "HIGH": 30,
    "MEDIUM": 90,
    "LOW": 180,
}


# ─────────────────────────────────────────────
# Compliance Summary
# ─────────────────────────────────────────────

@router.get("/compliance-summary")
async def get_compliance_summary(
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Compute compliance status for BOD 22-01, SOC 2 Type II, and PCI DSS.
    """
    now = datetime.now(timezone.utc)
    # 5-minute cache — compliance data changes infrequently
    response.headers["Cache-Control"] = "private, max-age=300"

    # ── BOD 22-01 (KEV) ──────────────────────────────────────────────────────
    # Use SQL counts instead of loading all KEV rows into Python
    kev_total_q = (
        select(func.count(AssetVulnerability.id))
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                Vulnerability.kev_listed == True,
                AssetVulnerability.status.in_(["ACTIVE", "PATCHED", "MITIGATED"]),
            )
        )
    )
    kev_patched_q = (
        select(func.count(AssetVulnerability.id))
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                Vulnerability.kev_listed == True,
                AssetVulnerability.status.in_(["PATCHED", "MITIGATED"]),
            )
        )
    )
    kev_total = (await db.execute(kev_total_q)).scalar() or 0
    kev_patched = (await db.execute(kev_patched_q)).scalar() or 0

    # Fetch only ACTIVE KEV rows for the detail list (bounded — unpatched KEVs should be few)
    kev_unpatched_q = (
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                Vulnerability.kev_listed == True,
                AssetVulnerability.status == "ACTIVE",
            )
        )
        .limit(500)  # safety cap
    )
    kev_unpatched_rows = (await db.execute(kev_unpatched_q)).scalars().all()
    kev_unpatched = [
        {
            "cve_id": r.vulnerability.identifier,
            "severity": r.vulnerability.severity,
            "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None,
            "days_overdue": max(
                0,
                (now - r.discovered_at).days - SLA_DAYS.get(r.vulnerability.severity or "HIGH", 30)
            ) if r.discovered_at else 0,
            "sla_deadline": (
                r.discovered_at + timedelta(days=SLA_DAYS.get(r.vulnerability.severity or "HIGH", 30))
            ).isoformat() if r.discovered_at else None,
        }
        for r in kev_unpatched_rows
    ]

    bod_pct = round(kev_patched / kev_total * 100, 1) if kev_total else 100.0
    if kev_total == 0 or bod_pct >= 100:
        bod_status = "COMPLIANT"
    elif bod_pct >= 80:
        bod_status = "AT_RISK"
    else:
        bod_status = "NON_COMPLIANT"

    # ── SOC 2 Type II ────────────────────────────────────────────────────────
    # Use SQL GROUP BY aggregation instead of fetching all rows to Python
    soc2_q = (
        select(
            Vulnerability.severity,
            func.count(AssetVulnerability.id).label("total"),
            func.sum(
                case(
                    (
                        AssetVulnerability.status.in_(["PATCHED", "MITIGATED"]),
                        1,
                    ),
                    else_=0,
                )
            ).label("patched_count"),
        )
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                Vulnerability.severity.in_(["CRITICAL", "HIGH"]),
                AssetVulnerability.status.in_(["ACTIVE", "PATCHED", "MITIGATED"]),
            )
        )
        .group_by(Vulnerability.severity)
    )
    soc2_rows = (await db.execute(soc2_q)).all()
    soc2_by_sev = {row.severity: row for row in soc2_rows}

    c_row = soc2_by_sev.get("CRITICAL")
    c_total = c_row.total if c_row else 0
    c_patched = c_row.patched_count if c_row else 0
    soc2_critical_pct = round(c_patched / c_total * 100, 1) if c_total else 100.0

    h_row = soc2_by_sev.get("HIGH")
    h_total = h_row.total if h_row else 0
    h_patched = h_row.patched_count if h_row else 0
    soc2_high_pct = round(h_patched / h_total * 100, 1) if h_total else 100.0

    avg_soc2 = round((soc2_critical_pct + soc2_high_pct) / 2, 1)
    if avg_soc2 >= 95:
        soc2_status = "COMPLIANT"
    elif avg_soc2 >= 75:
        soc2_status = "AT_RISK"
    else:
        soc2_status = "NON_COMPLIANT"

    # ── PCI DSS ───────────────────────────────────────────────────────────────
    # % of internet-facing assets with zero critical vulns — use SQL subquery
    internet_asset_subq = (
        select(Asset.id)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                or_(
                    func.upper(Asset.exposure) == "INTERNET",
                    func.upper(Asset.exposure) == "INTERNET-FACING",
                ),
            )
        )
        .scalar_subquery()
    )
    total_internet_q = (
        select(func.count(Asset.id))
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                or_(
                    func.upper(Asset.exposure) == "INTERNET",
                    func.upper(Asset.exposure) == "INTERNET-FACING",
                ),
            )
        )
    )
    total_internet = (await db.execute(total_internet_q)).scalar() or 0

    if total_internet > 0:
        critical_on_internet_q = (
            select(func.count(func.distinct(AssetVulnerability.asset_id)))
            .join(AssetVulnerability.vulnerability)
            .where(
                and_(
                    AssetVulnerability.asset_id.in_(internet_asset_subq),
                    Vulnerability.severity == "CRITICAL",
                    AssetVulnerability.status == "ACTIVE",
                )
            )
        )
        affected_count = (await db.execute(critical_on_internet_q)).scalar() or 0
        clean_assets = total_internet - affected_count
        pci_pct = round(clean_assets / total_internet * 100, 1)
    else:
        pci_pct = 100.0
        affected_count = 0
        clean_assets = 0

    if pci_pct >= 100:
        pci_status = "COMPLIANT"
    elif pci_pct >= 80:
        pci_status = "AT_RISK"
    else:
        pci_status = "NON_COMPLIANT"

    return {
        "generated_at": now.isoformat(),
        "frameworks": {
            "bod_22_01": {
                "name": "CISA BOD 22-01",
                "description": "Known Exploited Vulnerabilities (KEV) Catalog",
                "status": bod_status,
                "kev_total": kev_total,
                "kev_patched": kev_patched,
                "patch_rate_pct": bod_pct,
                "unpatched_items": kev_unpatched,
            },
            "soc2": {
                "name": "SOC 2 Type II",
                "description": "Patch Management Controls",
                "status": soc2_status,
                "critical_patched_within_30d_pct": soc2_critical_pct,
                "critical_total": c_total,
                "high_patched_within_90d_pct": soc2_high_pct,
                "high_total": h_total,
            },
            "pci_dss": {
                "name": "PCI DSS",
                "description": "Internet-facing assets with no critical vulns",
                "status": pci_status,
                "internet_assets_total": total_internet,
                "clean_assets": clean_assets,
                "assets_with_critical_vulns": affected_count,
                "clean_pct": pci_pct,
            },
        },
    }


# ─────────────────────────────────────────────
# MTTP
# ─────────────────────────────────────────────

@router.get("/mttp")
async def get_mttp(
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Mean Time To Patch — grouped by severity, environment, and team.
    """
    # 10-minute cache — MTTP is an expensive aggregation that changes slowly
    response.headers["Cache-Control"] = "private, max-age=600"
    # Query patched vulns: discovered_at on asset_vulnerability, status PATCHED
    q = (
        select(AssetVulnerability)
        .options(
            selectinload(AssetVulnerability.vulnerability),
            selectinload(AssetVulnerability.asset),
        )
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                AssetVulnerability.status.in_(["PATCHED", "MITIGATED"]),
                AssetVulnerability.discovered_at.isnot(None),
            )
        )
    )
    rows = (await db.execute(q)).scalars().all()

    # By severity
    severity_days: Dict[str, List[float]] = {}
    env_days: Dict[str, List[float]] = {}
    team_days: Dict[str, List[float]] = {}

    now = datetime.now(timezone.utc)

    for r in rows:
        # Use updated_at as proxy for patch time if no explicit field
        patch_time = getattr(r, "updated_at", None) or now
        if r.discovered_at:
            days = max(0.0, (patch_time - r.discovered_at).total_seconds() / 86400)
        else:
            continue

        sev = (r.vulnerability.severity or "UNKNOWN").upper()
        severity_days.setdefault(sev, []).append(days)

        env = (r.asset.environment or "unknown").lower()
        env_days.setdefault(env, []).append(days)

        team = r.asset.owner_team or "unassigned"
        team_days.setdefault(team, []).append(days)

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    by_severity = {
        sev: {"avg_days": avg(vals), "sample_size": len(vals)}
        for sev, vals in severity_days.items()
    }

    by_environment = {
        env: {"avg_days": avg(vals), "sample_size": len(vals)}
        for env, vals in env_days.items()
    }

    by_team = [
        {"team": team, "avg_days": avg(vals), "sample_size": len(vals)}
        for team, vals in sorted(team_days.items())
    ]

    return {
        "generated_at": now.isoformat(),
        "total_patched": len(rows),
        "by_severity": by_severity,
        "by_environment": by_environment,
        "by_team": by_team,
    }


# ─────────────────────────────────────────────
# SLA Tracking
# ─────────────────────────────────────────────

@router.get("/sla-tracking")
async def get_sla_tracking(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
) -> Dict[str, Any]:
    """
    List active vulnerabilities with SLA deadlines and status.
    """
    now = datetime.now(timezone.utc)

    q = (
        select(AssetVulnerability)
        .options(
            selectinload(AssetVulnerability.vulnerability),
            selectinload(AssetVulnerability.asset),
        )
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                AssetVulnerability.status == "ACTIVE",
                AssetVulnerability.discovered_at.isnot(None),
            )
        )
        .offset(skip)
        .limit(limit)
    )

    if severity:
        q = q.where(Vulnerability.severity.ilike(severity))

    rows = (await db.execute(q)).scalars().all()

    items = []
    for r in rows:
        sev = (r.vulnerability.severity or "MEDIUM").upper()
        sla_days = SLA_DAYS.get(sev, 90)
        deadline = r.discovered_at + timedelta(days=sla_days)
        days_remaining = (deadline - now).days

        if days_remaining < 0:
            sla_status = "BREACHED"
        elif days_remaining <= 3:
            sla_status = "AT_RISK"
        else:
            sla_status = "ON_TRACK"

        if status_filter and sla_status.lower() != status_filter.lower():
            continue

        items.append({
            "id": str(r.id),
            "cve_id": r.vulnerability.identifier,
            "title": r.vulnerability.title,
            "severity": sev,
            "asset_name": r.asset.name,
            "asset_environment": r.asset.environment,
            "discovered_at": r.discovered_at.isoformat(),
            "sla_days": sla_days,
            "sla_deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
            "sla_status": sla_status,
            "kev_listed": r.vulnerability.kev_listed,
            "cvss_score": r.vulnerability.cvss_score,
            "risk_score": r.risk_score,
        })

    # Sort: BREACHED first, then AT_RISK, then by days_remaining ascending
    priority = {"BREACHED": 0, "AT_RISK": 1, "ON_TRACK": 2}
    items.sort(key=lambda x: (priority.get(x["sla_status"], 3), x["days_remaining"]))

    counts = {
        "total": len(items),
        "breached": sum(1 for i in items if i["sla_status"] == "BREACHED"),
        "at_risk": sum(1 for i in items if i["sla_status"] == "AT_RISK"),
        "on_track": sum(1 for i in items if i["sla_status"] == "ON_TRACK"),
    }

    return {
        "generated_at": now.isoformat(),
        "counts": counts,
        "items": items,
    }


# ─────────────────────────────────────────────
# Executive Summary (for PDF export)
# ─────────────────────────────────────────────

@router.get("/executive-summary")
async def get_executive_summary(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Aggregated summary for executive reporting and PDF export.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ── Top 5 riskiest assets ─────────────────────────────────────────────────
    top_assets_q = (
        select(Asset)
        .where(Asset.tenant_id == tenant.id)
        .order_by(Asset.criticality.desc())
        .limit(5)
    )
    top_assets = (await db.execute(top_assets_q)).scalars().all()

    # Single GROUP BY query instead of N+1 per-asset count queries
    top_asset_ids = [a.id for a in top_assets]
    if top_asset_ids:
        vuln_counts_q = (
            select(
                AssetVulnerability.asset_id,
                func.count(AssetVulnerability.id).label("cnt"),
            )
            .where(
                and_(
                    AssetVulnerability.asset_id.in_(top_asset_ids),
                    AssetVulnerability.status == "ACTIVE",
                )
            )
            .group_by(AssetVulnerability.asset_id)
        )
        vuln_counts_result = (await db.execute(vuln_counts_q)).all()
        vuln_counts_map = {row.asset_id: row.cnt for row in vuln_counts_result}
    else:
        vuln_counts_map = {}

    top_asset_list = [
        {
            "id": str(a.id),
            "name": a.name,
            "environment": a.environment,
            "criticality": a.criticality,
            "exposure": a.exposure,
            "owner_team": a.owner_team,
            "active_vuln_count": vuln_counts_map.get(a.id, 0),
        }
        for a in top_assets
    ]

    # ── Bundles this month ────────────────────────────────────────────────────
    try:
        bundles_q = (
            select(Bundle)
            .where(
                and_(
                    Bundle.tenant_id == tenant.id,
                    Bundle.created_at >= thirty_days_ago,
                )
            )
        )
        bundles = (await db.execute(bundles_q)).scalars().all()
    except Exception:
        bundles = []

    bundle_summary = {
        "total": len(bundles),
        "scheduled": sum(1 for b in bundles if getattr(b, "status", "") in ("scheduled", "approved", "SCHEDULED", "APPROVED")),
        "completed": sum(1 for b in bundles if getattr(b, "status", "") in ("completed", "success", "COMPLETED", "SUCCESS")),
        "failed": sum(1 for b in bundles if getattr(b, "status", "") in ("failed", "error", "FAILED", "ERROR")),
    }

    # ── Goals progress ────────────────────────────────────────────────────────
    goals_q = select(Goal).where(
        and_(
            Goal.tenant_id == tenant.id,
            Goal.active == True,
        )
    )
    goals = (await db.execute(goals_q)).scalars().all()
    goals_summary = [
        {
            "id": str(g.id),
            "name": g.name,
            "type": g.goal_type,
            "target_value": g.target_value,
            "current_value": g.current_risk_score,
            "progress_pct": round(g.progress_percentage, 1),
        }
        for g in goals
    ]

    # ── Vuln totals ───────────────────────────────────────────────────────────
    total_q = (
        select(func.count(AssetVulnerability.id))
        .join(AssetVulnerability.asset)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                AssetVulnerability.status == "ACTIVE",
            )
        )
    )
    total_active = (await db.execute(total_q)).scalar() or 0

    critical_q = (
        select(func.count(AssetVulnerability.id))
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                AssetVulnerability.status == "ACTIVE",
                Vulnerability.severity == "CRITICAL",
            )
        )
    )
    total_critical = (await db.execute(critical_q)).scalar() or 0

    kev_q = (
        select(func.count(AssetVulnerability.id))
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                AssetVulnerability.status == "ACTIVE",
                Vulnerability.kev_listed == True,
            )
        )
    )
    total_kev = (await db.execute(kev_q)).scalar() or 0

    return {
        "generated_at": now.isoformat(),
        "tenant_name": tenant.name if hasattr(tenant, "name") else "Organization",
        "report_period": {
            "start": thirty_days_ago.isoformat(),
            "end": now.isoformat(),
        },
        "vulnerability_summary": {
            "total_active": total_active,
            "critical": total_critical,
            "kev_listed": total_kev,
        },
        "top_riskiest_assets": top_asset_list,
        "bundles_this_month": bundle_summary,
        "goals": goals_summary,
    }
