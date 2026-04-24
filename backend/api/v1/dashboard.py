"""
Dashboard API endpoints.

Provides aggregated data for the main dashboard view.
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant


router = APIRouter()


@router.get("/top-risk-pairs")
async def get_top_risk_pairs(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(5, ge=1, le=50, description="Number of top risk pairs to return"),
) -> List[Dict[str, Any]]:
    """
    Get the top asset-vulnerability pairs sorted by risk score.
    
    Returns detailed information about the riskiest vulnerability instances
    on specific assets, including all risk factors.
    """
    # Query asset_vulnerabilities joined with assets and vulnerabilities
    # Filter for current tenant and either ACTIVE status or NULL (for compatibility)
    query = (
        select(AssetVulnerability)
        .options(
            selectinload(AssetVulnerability.asset),
            selectinload(AssetVulnerability.vulnerability)
        )
        .join(AssetVulnerability.asset)
        .join(AssetVulnerability.vulnerability)
        .where(
            and_(
                AssetVulnerability.asset.has(tenant_id=tenant.id),
                or_(
                    AssetVulnerability.status == "ACTIVE",
                    AssetVulnerability.status.is_(None),
                    AssetVulnerability.status == "open",
                    AssetVulnerability.status == "in_progress"
                )
            )
        )
        .order_by(AssetVulnerability.risk_score.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    asset_vulns = result.scalars().all()
    
    # Transform to response format
    pairs = []
    for av in asset_vulns:
        vuln = av.vulnerability
        asset = av.asset
        
        pairs.append({
            "vulnerability_id": str(vuln.id),
            "vulnerability_identifier": vuln.identifier,
            "vulnerability_title": vuln.title,
            "vulnerability_severity": vuln.severity,
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "asset_environment": asset.environment,
            "risk_score": av.risk_score,
            "risk_factors": {
                "severity": vuln.severity,
                "kev_listed": vuln.kev_listed,
                "epss_score": vuln.epss_score,
                "exploit_available": vuln.exploit_available,
                "asset_exposure": asset.exposure,
                "asset_criticality": asset.criticality,
            },
        })
    
    return pairs
