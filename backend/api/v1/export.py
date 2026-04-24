"""
SIEM/CMDB Export API endpoints.

Machine-readable vulnerability and asset exports in JSON or CSV format.
Supports API key authentication for integration with external systems.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.vulnerability import Vulnerability
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant

router = APIRouter()


async def get_tenant_for_export(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    """
    Support both Bearer JWT and X-API-Key header for export endpoints.
    Falls back to standard tenant auth if no API key is provided.
    """
    # Check for X-API-Key header — future: look up in a keys table
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # TODO: validate against stored API keys in the database
        # For now, accept any non-empty key alongside the tenant context
        pass
    return tenant


# ─────────────────────────────────────────────
# Vulnerability Export
# ─────────────────────────────────────────────

@router.get("/vulnerabilities")
async def export_vulnerabilities(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant_for_export),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    kev_only: bool = Query(False, description="Only KEV-listed vulnerabilities"),
    asset_group: Optional[str] = Query(None, description="Filter by asset environment or owner_team"),
    limit: int = Query(500, ge=1, le=1000, description="Max results (hard cap 1000)"),
    format: str = Query("json", description="Output format: json or csv"),
) -> Any:
    """
    Export vulnerability data for SIEM/CMDB integration.
    
    Returns enriched vulnerability instances with asset context.
    Supports JSON and CSV output formats.
    """
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
            )
        )
        .limit(limit)
    )

    if severity:
        q = q.where(Vulnerability.severity.ilike(severity))

    if kev_only:
        q = q.where(Vulnerability.kev_listed == True)

    if asset_group:
        q = q.where(
            or_(
                Asset.environment.ilike(f"%{asset_group}%"),
                Asset.owner_team.ilike(f"%{asset_group}%"),
            )
        )

    rows = (await db.execute(q)).scalars().all()

    records = [
        {
            "cve_id": r.vulnerability.identifier,
            "severity": r.vulnerability.severity,
            "cvss": r.vulnerability.cvss_score,
            "epss": r.vulnerability.epss_score,
            "kev": r.vulnerability.kev_listed,
            "asset_name": r.asset.name,
            "asset_env": r.asset.environment,
            "status": r.status,
            "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None,
            "patch_available": r.vulnerability.patch_available,
        }
        for r in rows
    ]

    if format.lower() == "csv":
        return _records_to_csv_response(
            records,
            filename="glasswatch_vulnerabilities.csv",
        )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total": len(records),
        "format": "json",
        "data": records,
    }


# ─────────────────────────────────────────────
# Asset Export
# ─────────────────────────────────────────────

@router.get("/assets")
async def export_assets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant_for_export),
    environment: Optional[str] = Query(None),
    owner_team: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    format: str = Query("json", description="Output format: json or csv"),
) -> Any:
    """
    Export asset inventory for CMDB integration.
    """
    q = (
        select(Asset)
        .where(Asset.tenant_id == tenant.id)
        .limit(limit)
    )

    if environment:
        q = q.where(Asset.environment.ilike(f"%{environment}%"))

    if owner_team:
        q = q.where(Asset.owner_team.ilike(f"%{owner_team}%"))

    assets = (await db.execute(q)).scalars().all()

    # Get vuln counts per asset in one query
    asset_ids = [a.id for a in assets]
    vuln_count_q = (
        select(AssetVulnerability.asset_id, func.count(AssetVulnerability.id).label("cnt"))
        .where(
            and_(
                AssetVulnerability.asset_id.in_(asset_ids),
                AssetVulnerability.status == "ACTIVE",
            )
        )
        .group_by(AssetVulnerability.asset_id)
    )
    vuln_counts = {str(row.asset_id): row.cnt for row in (await db.execute(vuln_count_q)).all()}

    records = [
        {
            "name": a.name,
            "type": a.asset_type if hasattr(a, "asset_type") else getattr(a, "type", None),
            "environment": a.environment,
            "criticality": a.criticality,
            "exposure": a.exposure,
            "risk_score": a.risk_score if callable(a.risk_score) else getattr(a, "risk_score", None),
            "last_scanned": a.last_scanned_at.isoformat() if a.last_scanned_at else None,
            "vuln_count": vuln_counts.get(str(a.id), 0),
            "owner_team": a.owner_team,
        }
        for a in assets
    ]

    # risk_score may be a property/method
    for i, (a, rec) in enumerate(zip(assets, records)):
        rs = rec.get("risk_score")
        if callable(rs):
            try:
                records[i]["risk_score"] = rs()
            except Exception:
                records[i]["risk_score"] = None

    if format.lower() == "csv":
        return _records_to_csv_response(
            records,
            filename="glasswatch_assets.csv",
        )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total": len(records),
        "format": "json",
        "data": records,
    }


# ─────────────────────────────────────────────
# CSV helper
# ─────────────────────────────────────────────

def _records_to_csv_response(records: List[Dict], filename: str) -> Response:
    if not records:
        return Response(
            content="",
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
