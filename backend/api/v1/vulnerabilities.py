"""
Vulnerability API endpoints.

Provides CRUD operations for vulnerabilities and search capabilities.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.vulnerability import Vulnerability
from backend.models.asset_vulnerability import AssetVulnerability
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.models.tenant import Tenant


router = APIRouter()


@router.get("")
async def list_vulnerabilities(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    kev_only: bool = Query(False, description="Only show KEV-listed vulnerabilities"),
    source: Optional[str] = Query(None, description="Filter by source (nvd, ghsa, etc)"),
    search: Optional[str] = Query(None, description="Search in identifier, title, description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List vulnerabilities with filtering and search.
    
    Returns paginated list of vulnerabilities.
    """
    # Build base query
    query = select(Vulnerability)
    
    # Apply filters
    filters = []
    
    if severity:
        filters.append(Vulnerability.severity.ilike(f"%{severity}%"))
    
    if kev_only:
        filters.append(Vulnerability.kev_listed == True)
    
    if source:
        filters.append(Vulnerability.source == source.lower())
    
    if search:
        filters.append(
            or_(
                Vulnerability.identifier.ilike(f"%{search}%"),
                Vulnerability.title.ilike(f"%{search}%"),
                Vulnerability.description.ilike(f"%{search}%"),
            )
        )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Vulnerability.published_at.desc())
    
    # Execute query
    result = await db.execute(query)
    vulnerabilities = result.scalars().all()
    
    return {
        "vulnerabilities": [
            {
                "id": str(vuln.id),
                "identifier": vuln.identifier,
                "source": vuln.source,
                "title": vuln.title,
                "severity": vuln.severity,
                "cvss_score": vuln.cvss_score,
                "epss_score": vuln.epss_score,
                "kev_listed": vuln.kev_listed,
                "exploit_available": vuln.exploit_available,
                "patch_available": vuln.patch_available,
                "published_at": vuln.published_at.isoformat() if vuln.published_at else None,
                "is_critical": vuln.is_critical,
            }
            for vuln in vulnerabilities
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }




@router.get("/stats")
async def get_vulnerability_stats(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Get vulnerability statistics for the tenant."""
    severity_stats = await db.execute(
        select(
            Vulnerability.severity,
            func.count(Vulnerability.id).label("count")
        ).group_by(Vulnerability.severity)
    )
    by_severity = {row.severity.upper() if row.severity else "UNKNOWN": row.count for row in severity_stats}

    total_count = await db.scalar(select(func.count(Vulnerability.id)))
    kev_count = await db.scalar(
        select(func.count(Vulnerability.id)).where(Vulnerability.kev_listed == True)
    )
    exploit_count = await db.scalar(
        select(func.count(Vulnerability.id)).where(Vulnerability.exploit_available == True)
    )
    patch_count = await db.scalar(
        select(func.count(Vulnerability.id)).where(Vulnerability.patch_available == True)
    )
    recent_count = await db.scalar(
        select(func.count(Vulnerability.id))
        .where(Vulnerability.published_at >= func.now() - text("interval '7 days'"))
    )

    return {
        "total": total_count,
        "by_severity": by_severity,
        "kev_listed": kev_count,
        "exploits_available": exploit_count,
        "patches_available": patch_count,
        "recent_7d": recent_count,
        "total_risk_score": total_count * 100,  # Simplified for MVP
    }


@router.get("/{vulnerability_id}/runtime")
async def get_vulnerability_runtime_analysis(
    vulnerability_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get runtime analysis data for a vulnerability.
    
    Returns Snapper runtime analysis data showing whether vulnerable code
    is actually executing in the environment.
    """
    # Get any asset_vulnerability record for this vulnerability in this tenant
    # that has snapper runtime data
    query = (
        select(AssetVulnerability)
        .join(AssetVulnerability.asset)
        .where(
            and_(
                AssetVulnerability.vulnerability_id == vulnerability_id,
                AssetVulnerability.asset.has(tenant_id=tenant.id),
                AssetVulnerability.snapper_data.isnot(None),
            )
        )
        .limit(1)  # Get first asset with runtime data
    )
    
    result = await db.execute(query)
    asset_vuln = result.scalar_one_or_none()
    
    if not asset_vuln or not asset_vuln.snapper_data:
        raise HTTPException(
            status_code=404,
            detail="No runtime analysis data available for this vulnerability"
        )
    
    # Calculate impact score based on runtime data
    impact_score = 0
    if asset_vuln.code_executed:
        impact_score = 15
    elif asset_vuln.library_loaded:
        impact_score = 0
    else:
        impact_score = -10
    
    # Build response from asset_vulnerability runtime fields
    return {
        "vulnerability_id": str(vulnerability_id),
        "code_executed": asset_vuln.code_executed or False,
        "library_loaded": asset_vuln.library_loaded or False,
        "function_called": asset_vuln.snapper_data.get("function_called", False) if isinstance(asset_vuln.snapper_data, dict) else False,
        "execution_frequency": asset_vuln.snapper_data.get("execution_frequency", 0) if isinstance(asset_vuln.snapper_data, dict) else 0,
        "last_seen": asset_vuln.last_execution.isoformat() if asset_vuln.last_execution else None,
        "confidence": asset_vuln.scanner_confidence * 100 if asset_vuln.scanner_confidence else 85,
        "impact_score": impact_score,
    }


@router.get("/{vulnerability_id}")
async def get_vulnerability(
    vulnerability_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get detailed vulnerability information.
    
    Includes affected assets for the current tenant.
    """
    # Get vulnerability
    query = select(Vulnerability).where(Vulnerability.id == vulnerability_id)
    result = await db.execute(query)
    vulnerability = result.scalar_one_or_none()
    
    if not vulnerability:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    # Get affected assets for this tenant
    assets_query = (
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.asset))
        .join(AssetVulnerability.asset)
        .where(
            and_(
                AssetVulnerability.vulnerability_id == vulnerability_id,
                AssetVulnerability.asset.has(tenant_id=tenant.id),
                or_(
                    AssetVulnerability.status == "ACTIVE",
                    AssetVulnerability.status.is_(None),
                    AssetVulnerability.status == "open",
                    AssetVulnerability.status == "in_progress"
                ),
            )
        )
    )
    
    assets_result = await db.execute(assets_query)
    affected_assets = assets_result.scalars().all()
    
    return {
        "vulnerability": {
            "id": str(vulnerability.id),
            "identifier": vulnerability.identifier,
            "source": vulnerability.source,
            "title": vulnerability.title,
            "description": vulnerability.description,
            "severity": vulnerability.severity,
            "cvss_score": vulnerability.cvss_score,
            "cvss_vector": vulnerability.cvss_vector,
            "epss_score": vulnerability.epss_score,
            "kev_listed": vulnerability.kev_listed,
            "exploit_available": vulnerability.exploit_available,
            "exploit_maturity": vulnerability.exploit_maturity,
            "patch_available": vulnerability.patch_available,
            "patch_released_at": vulnerability.patch_released_at.isoformat() if vulnerability.patch_released_at else None,
            "vendor_advisory_url": vulnerability.vendor_advisory_url,
            "affected_products": vulnerability.affected_products,
            "cpe_list": vulnerability.cpe_list,
            "published_at": vulnerability.published_at.isoformat() if vulnerability.published_at else None,
            "updated_at": vulnerability.updated_at.isoformat() if vulnerability.updated_at else None,
            "days_since_published": vulnerability.days_since_published,
        },
        "affected_assets": [
            {
                "asset_id": str(av.asset.id),
                "asset_name": av.asset.name,
                "asset_type": av.asset.type,
                "environment": av.asset.environment,
                "criticality": av.asset.criticality,
                "exposure": av.asset.exposure,
                "risk_score": av.risk_score,
                "recommended_action": av.recommended_action,
                "patch_scheduled": av.scheduled_patch_date.isoformat() if av.scheduled_patch_date else None,
                "mitigation_applied": av.mitigation_applied,
                "code_executed": av.code_executed,  # Snapper data
                "library_loaded": av.library_loaded,
            }
            for av in affected_assets
        ],
        "affected_asset_count": len(affected_assets),
    }


@router.post("/search")
async def search_vulnerabilities(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    identifiers: Optional[List[str]] = None,
    min_cvss: Optional[float] = None,
    max_cvss: Optional[float] = None,
    min_epss: Optional[float] = None,
    published_after: Optional[datetime] = None,
    published_before: Optional[datetime] = None,
    has_exploit: Optional[bool] = None,
    has_patch: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Advanced vulnerability search with multiple criteria.
    
    Used for complex queries and reporting.
    """
    query = select(Vulnerability)
    
    filters = []
    
    if identifiers:
        filters.append(Vulnerability.identifier.in_(identifiers))
    
    if min_cvss is not None:
        filters.append(Vulnerability.cvss_score >= min_cvss)
    
    if max_cvss is not None:
        filters.append(Vulnerability.cvss_score <= max_cvss)
    
    if min_epss is not None:
        filters.append(Vulnerability.epss_score >= min_epss)
    
    if published_after:
        filters.append(Vulnerability.published_at >= published_after)
    
    if published_before:
        filters.append(Vulnerability.published_at <= published_before)
    
    if has_exploit is not None:
        filters.append(Vulnerability.exploit_available == has_exploit)
    
    if has_patch is not None:
        filters.append(Vulnerability.patch_available == has_patch)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(
        Vulnerability.cvss_score.desc().nullslast(),
        Vulnerability.published_at.desc()
    )
    
    result = await db.execute(query)
    vulnerabilities = result.scalars().all()
    
    return {
        "vulnerabilities": [
            {
                "id": str(vuln.id),
                "identifier": vuln.identifier,
                "source": vuln.source,
                "title": vuln.title,
                "severity": vuln.severity,
                "cvss_score": vuln.cvss_score,
                "epss_score": vuln.epss_score,
                "kev_listed": vuln.kev_listed,
                "exploit_available": vuln.exploit_available,
                "patch_available": vuln.patch_available,
                "published_at": vuln.published_at.isoformat() if vuln.published_at else None,
            }
            for vuln in vulnerabilities
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "search_criteria": {
            "identifiers": identifiers,
            "min_cvss": min_cvss,
            "max_cvss": max_cvss,
            "min_epss": min_epss,
            "published_after": published_after.isoformat() if published_after else None,
            "published_before": published_before.isoformat() if published_before else None,
            "has_exploit": has_exploit,
            "has_patch": has_patch,
        }
    }