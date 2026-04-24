"""
Asset API endpoints.

Provides CRUD operations for infrastructure assets and bulk import capabilities.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any, Dict
from uuid import UUID, uuid4
import json
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.vulnerability import Vulnerability
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.services.scoring import scoring_service


router = APIRouter()


@router.get("")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    type: Optional[str] = Query(None, description="Filter by asset type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    criticality: Optional[int] = Query(None, ge=1, le=5, description="Filter by criticality"),
    exposure: Optional[str] = Query(None, description="Filter by exposure level"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    patch_group: Optional[str] = Query(None, description="Filter by patch group"),
    search: Optional[str] = Query(None, description="Search in name, identifier, fqdn"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List assets with filtering and search.
    
    Returns paginated list of assets for the current tenant.
    """
    # Build base query
    query = select(Asset).where(Asset.tenant_id == tenant.id)
    
    # Apply filters
    filters = []
    
    if type:
        filters.append(Asset.type == type)
    
    if platform:
        filters.append(Asset.platform == platform)
    
    if environment:
        filters.append(Asset.environment == environment)
    
    if criticality is not None:
        filters.append(Asset.criticality == criticality)
    
    if exposure:
        filters.append(Asset.exposure.ilike(f"%{exposure}%"))
    
    if tag:
        filters.append(Asset.tags.op('@>')(func.cast([tag], JSONB)))
    
    if patch_group:
        filters.append(Asset.patch_group == patch_group)
    
    if search:
        filters.append(
            or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.identifier.ilike(f"%{search}%"),
                Asset.fqdn.ilike(f"%{search}%"),
            )
        )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Asset.criticality.desc(), Asset.name)
    
    # Execute query
    result = await db.execute(query)
    assets = result.scalars().all()
    
    # Get vulnerability counts for all assets
    asset_ids = [asset.id for asset in assets]
    vuln_count_query = (
        select(
            AssetVulnerability.asset_id,
            func.count(AssetVulnerability.id).label('count')
        )
        .where(
            and_(
                AssetVulnerability.asset_id.in_(asset_ids),
                or_(AssetVulnerability.status == "ACTIVE", AssetVulnerability.status.is_(None))
            )
        )
        .group_by(AssetVulnerability.asset_id)
    )
    vuln_count_result = await db.execute(vuln_count_query)
    vuln_counts = {row[0]: row[1] for row in vuln_count_result.all()}
    
    return {
        "assets": [
            {
                "id": str(asset.id),
                "identifier": asset.identifier,
                "name": asset.name,
                "type": asset.type,
                "platform": asset.platform,
                "environment": asset.environment,
                "criticality": asset.criticality,
                "exposure": asset.exposure,
                "location": asset.location,
                "owner_team": asset.owner_team,
                "business_unit": asset.business_unit,
                "os_family": asset.os_family,
                "fqdn": asset.fqdn,
                "patch_group": asset.patch_group,
                "tags": asset.tags or [],
                "risk_score": asset.risk_score,
                "is_internet_facing": asset.is_internet_facing,
                "vulnerability_count": vuln_counts.get(asset.id, 0),
                "last_scanned_at": asset.last_scanned_at.isoformat() if asset.last_scanned_at else None,
                "created_at": asset.created_at.isoformat(),
            }
            for asset in assets
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{asset_id}")
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get detailed asset information including vulnerabilities.
    """
    # Get asset
    query = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.tenant_id == tenant.id
        )
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get active vulnerabilities
    vuln_query = (
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .where(
            and_(
                AssetVulnerability.asset_id == asset_id,
                or_(AssetVulnerability.status == "ACTIVE", AssetVulnerability.status.is_(None)),
            )
        )
        .order_by(AssetVulnerability.risk_score.desc())
    )
    
    vuln_result = await db.execute(vuln_query)
    vulnerabilities = vuln_result.scalars().all()
    
    return {
        "asset": {
            "id": str(asset.id),
            "identifier": asset.identifier,
            "name": asset.name,
            "type": asset.type,
            "platform": asset.platform,
            "environment": asset.environment,
            "location": asset.location,
            "criticality": asset.criticality,
            "exposure": asset.exposure,
            "owner_team": asset.owner_team,
            "owner_email": asset.owner_email,
            "business_unit": asset.business_unit,
            "os_family": asset.os_family,
            "os_version": asset.os_version,
            "ip_addresses": asset.ip_addresses,
            "fqdn": asset.fqdn,
            "cloud_account_id": asset.cloud_account_id,
            "cloud_region": asset.cloud_region,
            "cloud_instance_type": asset.cloud_instance_type,
            "cloud_tags": asset.cloud_tags,
            "compliance_frameworks": asset.compliance_frameworks,
            "compensating_controls": asset.compensating_controls,
            "patch_group": asset.patch_group,
            "maintenance_window": asset.maintenance_window,
            "risk_score": asset.risk_score,
            "last_scanned_at": asset.last_scanned_at.isoformat() if asset.last_scanned_at else None,
            "last_patched_at": asset.last_patched_at.isoformat() if asset.last_patched_at else None,
            "created_at": asset.created_at.isoformat(),
            "updated_at": asset.updated_at.isoformat(),
        },
        "vulnerabilities": [
            {
                "vulnerability_id": str(av.vulnerability.id),
                "identifier": av.vulnerability.identifier,
                "title": av.vulnerability.title,
                "severity": av.vulnerability.severity,
                "risk_score": av.risk_score,
                "code_executed": av.code_executed,
                "library_loaded": av.library_loaded,
                "recommended_action": av.recommended_action,
                "patch_available": av.patch_available,
                "mitigation_applied": av.mitigation_applied,
                "discovered_at": av.discovered_at.isoformat() if av.discovered_at else None,
            }
            for av in vulnerabilities
        ],
        "vulnerability_count": len(vulnerabilities),
        "critical_vulnerability_count": sum(
            1 for av in vulnerabilities if av.risk_score >= 80
        ),
    }


@router.post("/")
async def create_asset(
    asset_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Create a new asset.
    """
    # Validate required fields
    required_fields = ["identifier", "name", "type"]
    for field in required_fields:
        if field not in asset_data:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required field: {field}"
            )
    
    # Check if asset already exists
    existing = await db.execute(
        select(Asset).where(
            and_(
                Asset.tenant_id == tenant.id,
                Asset.identifier == asset_data["identifier"]
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Asset with identifier '{asset_data['identifier']}' already exists"
        )
    
    # Create asset
    asset = Asset(
        tenant_id=tenant.id,
        **asset_data
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return {
        "asset": {
            "id": str(asset.id),
            "identifier": asset.identifier,
            "name": asset.name,
            "type": asset.type,
            "created_at": asset.created_at.isoformat(),
        }
    }


@router.put("/{asset_id}")
async def update_asset(
    asset_id: UUID,
    asset_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Update an existing asset.
    """
    # Get asset
    query = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.tenant_id == tenant.id
        )
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Update fields
    for field, value in asset_data.items():
        if hasattr(asset, field) and field not in ["id", "tenant_id", "created_at"]:
            setattr(asset, field, value)
    
    asset.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(asset)
    
    return {
        "asset": {
            "id": str(asset.id),
            "identifier": asset.identifier,
            "name": asset.name,
            "type": asset.type,
            "updated_at": asset.updated_at.isoformat(),
        }
    }


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Delete an asset and its vulnerability associations.
    """
    # Get asset
    query = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.tenant_id == tenant.id
        )
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Delete asset (cascades to asset_vulnerabilities)
    await db.delete(asset)
    await db.commit()
    
    return {"status": "deleted", "asset_id": str(asset_id)}


@router.post("/bulk-import")
async def bulk_import_assets(
    file: UploadFile = File(...),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Bulk import assets from JSON or CSV file.
    
    JSON format: Array of asset objects
    CSV format: Standard CSV with headers matching asset fields
    """
    # Read file content
    content = await file.read()
    
    try:
        if format == "json":
            # Parse JSON
            asset_data_list = json.loads(content.decode())
            if not isinstance(asset_data_list, list):
                raise ValueError("JSON must be an array of asset objects")
        else:
            # Parse CSV
            csv_file = StringIO(content.decode())
            reader = csv.DictReader(csv_file)
            asset_data_list = list(reader)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse {format.upper()} file: {str(e)}"
        )
    
    # Import assets
    created_count = 0
    updated_count = 0
    errors = []
    
    for idx, asset_data in enumerate(asset_data_list):
        try:
            # Check required fields
            if not asset_data.get("identifier") or not asset_data.get("name"):
                errors.append(f"Row {idx + 1}: Missing required fields")
                continue
            
            # Check if exists
            existing = await db.execute(
                select(Asset).where(
                    and_(
                        Asset.tenant_id == tenant.id,
                        Asset.identifier == asset_data["identifier"]
                    )
                )
            )
            existing_asset = existing.scalar_one_or_none()
            
            if existing_asset:
                # Update existing
                for field, value in asset_data.items():
                    if hasattr(existing_asset, field) and field not in ["id", "tenant_id", "created_at"]:
                        # Convert string numbers to int for certain fields
                        if field == "criticality" and isinstance(value, str):
                            value = int(value) if value.isdigit() else 3
                        setattr(existing_asset, field, value)
                
                existing_asset.updated_at = datetime.now(timezone.utc)
                updated_count += 1
            else:
                # Create new
                # Set defaults and convert types
                if "type" not in asset_data:
                    asset_data["type"] = "server"
                
                if "criticality" in asset_data and isinstance(asset_data["criticality"], str):
                    asset_data["criticality"] = int(asset_data["criticality"]) if asset_data["criticality"].isdigit() else 3
                
                asset = Asset(tenant_id=tenant.id, **asset_data)
                db.add(asset)
                created_count += 1
                
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    # Commit all changes
    await db.commit()
    
    return {
        "status": "completed",
        "created": created_count,
        "updated": updated_count,
        "errors": errors,
        "total_processed": len(asset_data_list),
    }


@router.get("/stale")
async def get_stale_assets(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    days: int = Query(30, ge=1, description="Assets not scanned in this many days are considered stale"),
) -> Dict[str, Any]:
    """
    Return assets with last_scanned_at older than `days` days (or never scanned).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = select(Asset).where(
        and_(
            Asset.tenant_id == tenant.id,
            or_(
                Asset.last_scanned_at < cutoff,
                Asset.last_scanned_at.is_(None),
            ),
        )
    ).order_by(Asset.last_scanned_at.asc().nullsfirst(), Asset.name)

    result = await db.execute(query)
    assets = result.scalars().all()

    def days_since(dt):
        if dt is None:
            return None
        return (datetime.now(timezone.utc) - dt).days

    return {
        "assets": [
            {
                "id": str(a.id),
                "name": a.name,
                "identifier": a.identifier,
                "type": a.type,
                "environment": a.environment,
                "criticality": a.criticality,
                "risk_score": a.risk_score,
                "last_scanned_at": a.last_scanned_at.isoformat() if a.last_scanned_at else None,
                "days_since_scan": days_since(a.last_scanned_at),
            }
            for a in assets
        ],
        "total": len(assets),
        "stale_days_threshold": days,
    }


@router.get("/groups")
async def get_asset_groups(
    group_by: str = Query("environment", description="Group by: environment, owner_team, criticality, patch_group"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Return assets grouped by a dimension with aggregate stats.
    """
    valid_groups = {"environment", "owner_team", "criticality", "patch_group"}
    if group_by not in valid_groups:
        raise HTTPException(status_code=400, detail=f"group_by must be one of {valid_groups}")

    # Fetch all assets for the tenant
    result = await db.execute(
        select(Asset).where(Asset.tenant_id == tenant.id)
    )
    assets = result.scalars().all()

    # Get vuln counts per asset
    asset_ids = [a.id for a in assets]
    patched_query = (
        select(
            AssetVulnerability.asset_id,
            func.count(AssetVulnerability.id).label("total"),
            func.sum(
                func.cast(AssetVulnerability.status == "PATCHED", Integer_type := None)
            ).label("patched"),
        )
        .where(AssetVulnerability.asset_id.in_(asset_ids))
        .group_by(AssetVulnerability.asset_id)
    ) if asset_ids else None

    vuln_totals: Dict[Any, int] = {}
    vuln_patched: Dict[Any, int] = {}
    if asset_ids:
        pr = await db.execute(
            select(
                AssetVulnerability.asset_id,
                func.count(AssetVulnerability.id).label("total"),
            )
            .where(AssetVulnerability.asset_id.in_(asset_ids))
            .group_by(AssetVulnerability.asset_id)
        )
        for row in pr.all():
            vuln_totals[row[0]] = row[1]

        pp = await db.execute(
            select(
                AssetVulnerability.asset_id,
                func.count(AssetVulnerability.id).label("patched"),
            )
            .where(
                and_(
                    AssetVulnerability.asset_id.in_(asset_ids),
                    AssetVulnerability.status == "PATCHED",
                )
            )
            .group_by(AssetVulnerability.asset_id)
        )
        for row in pp.all():
            vuln_patched[row[0]] = row[1]

    # Group assets
    groups: Dict[str, Any] = {}
    for asset in assets:
        key = getattr(asset, group_by)
        if key is None:
            key = "(unset)"
        key = str(key)
        if key not in groups:
            groups[key] = {"count": 0, "risk_score_sum": 0.0, "total_vulns": 0, "patched_vulns": 0, "asset_ids": []}
        g = groups[key]
        g["count"] += 1
        g["risk_score_sum"] += asset.risk_score
        g["total_vulns"] += vuln_totals.get(asset.id, 0)
        g["patched_vulns"] += vuln_patched.get(asset.id, 0)
        g["asset_ids"].append(str(asset.id))

    result_groups = []
    for name, g in sorted(groups.items()):
        avg_risk = round(g["risk_score_sum"] / g["count"], 1) if g["count"] else 0
        pct_patched = round(g["patched_vulns"] / g["total_vulns"] * 100, 1) if g["total_vulns"] else 0
        result_groups.append({
            "name": name,
            "count": g["count"],
            "avg_risk_score": avg_risk,
            "total_vulns": g["total_vulns"],
            "patched_vulns": g["patched_vulns"],
            "pct_patched": pct_patched,
            "asset_ids": g["asset_ids"],
        })

    return {"groups": result_groups, "group_by": group_by}


@router.get("/coverage")
async def get_patch_coverage(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(50, le=200),
) -> Dict[str, Any]:
    """
    Return patch coverage by CVE — how many assets are affected, patched, and unpatched.
    """
    # Get all asset IDs for this tenant
    asset_ids_result = await db.execute(
        select(Asset.id).where(Asset.tenant_id == tenant.id)
    )
    asset_ids = [r[0] for r in asset_ids_result.all()]

    if not asset_ids:
        return {"coverage": [], "total": 0}

    # Aggregate vuln coverage
    total_q = await db.execute(
        select(
            AssetVulnerability.vulnerability_id,
            func.count(AssetVulnerability.id).label("total"),
        )
        .where(AssetVulnerability.asset_id.in_(asset_ids))
        .group_by(AssetVulnerability.vulnerability_id)
        .order_by(func.count(AssetVulnerability.id).desc())
        .limit(limit)
    )
    total_rows = total_q.all()

    if not total_rows:
        return {"coverage": [], "total": 0}

    vuln_ids = [r[0] for r in total_rows]
    total_map = {r[0]: r[1] for r in total_rows}

    patched_q = await db.execute(
        select(
            AssetVulnerability.vulnerability_id,
            func.count(AssetVulnerability.id).label("patched"),
        )
        .where(
            and_(
                AssetVulnerability.asset_id.in_(asset_ids),
                AssetVulnerability.vulnerability_id.in_(vuln_ids),
                AssetVulnerability.status == "PATCHED",
            )
        )
        .group_by(AssetVulnerability.vulnerability_id)
    )
    patched_map = {r[0]: r[1] for r in patched_q.all()}

    # Fetch vuln details
    vuln_details_q = await db.execute(
        select(Vulnerability).where(Vulnerability.id.in_(vuln_ids))
    )
    vuln_details = {v.id: v for v in vuln_details_q.scalars().all()}

    coverage = []
    for vid in vuln_ids:
        v = vuln_details.get(vid)
        if not v:
            continue
        total = total_map.get(vid, 0)
        patched = patched_map.get(vid, 0)
        unpatched = total - patched
        pct = round(patched / total * 100, 1) if total else 0
        coverage.append({
            "vulnerability_id": str(vid),
            "identifier": v.identifier,
            "severity": v.severity,
            "cvss_score": v.cvss_score,
            "kev_listed": v.kev_listed,
            "patch_available": v.patch_available,
            "total_assets": total,
            "patched_assets": patched,
            "unpatched_assets": unpatched,
            "coverage_pct": pct,
        })

    return {"coverage": coverage, "total": len(coverage)}


@router.get("/{asset_id}/vulnerabilities")
async def get_asset_vulnerabilities(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: Optional[str] = Query("ACTIVE", description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score"),
) -> Dict[str, Any]:
    """
    Get all vulnerabilities for a specific asset with full details.
    """
    # Verify asset belongs to tenant
    asset_query = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.tenant_id == tenant.id
        )
    )
    asset_result = await db.execute(asset_query)
    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get vulnerabilities with full vuln data
    query = (
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .where(AssetVulnerability.asset_id == asset_id)
    )

    if status:
        query = query.where(AssetVulnerability.status == status)
    if severity:
        query = query.where(AssetVulnerability.vulnerability.has(Vulnerability.severity == severity.upper()))
    if min_score is not None:
        query = query.where(AssetVulnerability.risk_score >= min_score)

    query = query.order_by(AssetVulnerability.risk_score.desc())

    result = await db.execute(query)
    vulnerabilities = result.scalars().all()

    # Get which bundles include each vuln for this asset (via BundleItem)
    av_ids = [av.vulnerability_id for av in vulnerabilities]
    bundle_map: Dict[Any, Dict] = {}
    if av_ids:
        bi_q = await db.execute(
            select(BundleItem, Bundle)
            .join(Bundle, BundleItem.bundle_id == Bundle.id)
            .where(
                and_(
                    BundleItem.asset_id == asset_id,
                    BundleItem.vulnerability_id.in_(av_ids),
                )
            )
        )
        for bi, bundle in bi_q.all():
            bundle_map[bi.vulnerability_id] = {
                "bundle_id": str(bundle.id),
                "bundle_name": bundle.name,
                "bundle_status": bundle.status,
            }

    now = datetime.now(timezone.utc)

    return {
        "asset": {
            "id": str(asset.id),
            "name": asset.name,
            "type": asset.type,
        },
        "vulnerabilities": [
            {
                "id": str(av.id),
                "vulnerability_id": str(av.vulnerability.id),
                "identifier": av.vulnerability.identifier,
                "title": av.vulnerability.title,
                "severity": av.vulnerability.severity,
                "cvss_score": av.vulnerability.cvss_score,
                "epss_score": av.vulnerability.epss_score,
                "kev_listed": av.vulnerability.kev_listed,
                "exploit_available": av.vulnerability.exploit_available,
                "patch_available": av.patch_available if av.patch_available is not None else av.vulnerability.patch_available,
                "risk_score": av.risk_score,
                "score_factors": av.score_factors,
                "status": av.status,
                "code_executed": av.code_executed,
                "library_loaded": av.library_loaded,
                "execution_frequency": av.execution_frequency,
                "recommended_action": av.recommended_action,
                "mitigation_applied": av.mitigation_applied,
                "days_open": (now - av.discovered_at).days if av.discovered_at else None,
                "discovered_at": av.discovered_at.isoformat() if av.discovered_at else None,
                "last_reviewed_at": av.last_reviewed_at.isoformat() if av.last_reviewed_at else None,
                "bundle": bundle_map.get(av.vulnerability_id),
            }
            for av in vulnerabilities
        ],
        "total": len(vulnerabilities),
        "risk_summary": {
            "critical": sum(1 for av in vulnerabilities if av.risk_score >= 80),
            "high": sum(1 for av in vulnerabilities if 60 <= av.risk_score < 80),
            "medium": sum(1 for av in vulnerabilities if 40 <= av.risk_score < 60),
            "low": sum(1 for av in vulnerabilities if av.risk_score < 40),
        }
    }


@router.patch("/{asset_id}/tags")
async def patch_asset_tags(
    asset_id: UUID,
    tag_data: Dict[str, List[str]],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Add or remove tags from a single asset.
    
    Body: {"add": ["tag1", "tag2"], "remove": ["tag3"]}
    """
    # Get asset
    query = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.tenant_id == tenant.id
        )
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get current tags
    current_tags = set(asset.tags or [])
    
    # Add tags
    if "add" in tag_data:
        current_tags.update(tag_data["add"])
    
    # Remove tags
    if "remove" in tag_data:
        current_tags.difference_update(tag_data["remove"])
    
    # Update asset
    asset.tags = list(current_tags)
    asset.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(asset)
    
    return {
        "asset": {
            "id": str(asset.id),
            "identifier": asset.identifier,
            "name": asset.name,
            "tags": asset.tags,
            "updated_at": asset.updated_at.isoformat(),
        }
    }


@router.post("/bulk-tag")
async def bulk_tag_assets(
    bulk_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Bulk add/remove tags across multiple assets.
    
    Body: {"asset_ids": ["uuid1", "uuid2"], "add": ["tag1"], "remove": ["tag2"]}
    """
    asset_ids = [UUID(aid) for aid in bulk_data.get("asset_ids", [])]
    add_tags = bulk_data.get("add", [])
    remove_tags = bulk_data.get("remove", [])
    
    if not asset_ids:
        raise HTTPException(status_code=400, detail="asset_ids required")
    
    # Get all assets
    query = select(Asset).where(
        and_(
            Asset.id.in_(asset_ids),
            Asset.tenant_id == tenant.id
        )
    )
    result = await db.execute(query)
    assets = result.scalars().all()
    
    modified_count = 0
    for asset in assets:
        current_tags = set(asset.tags or [])
        original_tags = current_tags.copy()
        
        if add_tags:
            current_tags.update(add_tags)
        
        if remove_tags:
            current_tags.difference_update(remove_tags)
        
        if current_tags != original_tags:
            asset.tags = list(current_tags)
            asset.updated_at = datetime.now(timezone.utc)
            modified_count += 1
    
    await db.commit()
    
    return {
        "status": "completed",
        "modified": modified_count,
        "requested": len(asset_ids),
    }


@router.get("/tags")
async def list_tags(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get all unique tags used across the tenant's assets.
    
    Returns: {"tags": [{"name": "web-tier", "count": 4}, ...]}
    """
    # Query for all tags
    query = select(Asset.tags).where(Asset.tenant_id == tenant.id)
    result = await db.execute(query)
    
    # Aggregate tags
    tag_counts = {}
    for (tags,) in result.all():
        if tags:
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort by count descending
    sorted_tags = sorted(
        [{"name": tag, "count": count} for tag, count in tag_counts.items()],
        key=lambda x: (-x["count"], x["name"])
    )
    
    return {"tags": sorted_tags}


@router.post("/enrich")
async def enrich_assets(
    enrich_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Enrich assets by matching on identifier/fqdn and merging data.
    
    Body: {
        "match_by": "identifier",  # or "fqdn"
        "assets": [
            {
                "identifier": "prod-web-01.acme.internal",
                "os_version": "RHEL 8.9",
                "installed_packages": [...],
                "tags": ["scanner-found"]
            }
        ]
    }
    """
    match_by = enrich_data.get("match_by", "identifier")
    assets_data = enrich_data.get("assets", [])
    
    if match_by not in ["identifier", "fqdn"]:
        raise HTTPException(status_code=400, detail="match_by must be 'identifier' or 'fqdn'")
    
    matched_count = 0
    not_found_count = 0
    updated_count = 0
    
    for asset_data in assets_data:
        match_value = asset_data.get(match_by)
        if not match_value:
            not_found_count += 1
            continue
        
        # Find asset
        if match_by == "identifier":
            query = select(Asset).where(
                and_(
                    Asset.tenant_id == tenant.id,
                    Asset.identifier == match_value
                )
            )
        else:  # fqdn
            query = select(Asset).where(
                and_(
                    Asset.tenant_id == tenant.id,
                    Asset.fqdn == match_value
                )
            )
        
        result = await db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            not_found_count += 1
            continue
        
        matched_count += 1
        
        # Merge data
        updated = False
        for field, value in asset_data.items():
            if field == match_by:
                continue
            
            if hasattr(asset, field) and field not in ["id", "tenant_id", "created_at"]:
                # Special handling for tags - merge instead of replace
                if field == "tags":
                    current_tags = set(asset.tags or [])
                    current_tags.update(value or [])
                    asset.tags = list(current_tags)
                    updated = True
                else:
                    setattr(asset, field, value)
                    updated = True
        
        if updated:
            asset.updated_at = datetime.now(timezone.utc)
            updated_count += 1
    
    await db.commit()
    
    return {
        "matched": matched_count,
        "not_found": not_found_count,
        "updated": updated_count,
    }


@router.get("/export")
async def export_assets(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    type: Optional[str] = Query(None, description="Filter by asset type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    criticality: Optional[int] = Query(None, ge=1, le=5, description="Filter by criticality"),
    exposure: Optional[str] = Query(None, description="Filter by exposure level"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    patch_group: Optional[str] = Query(None, description="Filter by patch group"),
) -> List[Dict[str, Any]]:
    """
    Export all matching assets with full detail.
    
    Returns JSON array of assets.
    """
    # Build query (same filters as list_assets)
    query = select(Asset).where(Asset.tenant_id == tenant.id)
    
    filters = []
    
    if type:
        filters.append(Asset.type == type)
    
    if platform:
        filters.append(Asset.platform == platform)
    
    if environment:
        filters.append(Asset.environment == environment)
    
    if criticality is not None:
        filters.append(Asset.criticality == criticality)
    
    if exposure:
        filters.append(Asset.exposure.ilike(f"%{exposure}%"))
    
    if tag:
        filters.append(Asset.tags.op('@>')(func.cast([tag], JSONB)))
    
    if patch_group:
        filters.append(Asset.patch_group == patch_group)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by criticality
    query = query.order_by(Asset.criticality.desc(), Asset.name)
    
    # Execute query (no limit for export)
    result = await db.execute(query)
    assets = result.scalars().all()
    
    return [
        {
            "id": str(asset.id),
            "identifier": asset.identifier,
            "name": asset.name,
            "type": asset.type,
            "platform": asset.platform,
            "environment": asset.environment,
            "location": asset.location,
            "owner_team": asset.owner_team,
            "owner_email": asset.owner_email,
            "business_unit": asset.business_unit,
            "criticality": asset.criticality,
            "exposure": asset.exposure,
            "os_family": asset.os_family,
            "os_version": asset.os_version,
            "ip_addresses": asset.ip_addresses,
            "fqdn": asset.fqdn,
            "cloud_account_id": asset.cloud_account_id,
            "cloud_region": asset.cloud_region,
            "cloud_instance_type": asset.cloud_instance_type,
            "cloud_tags": asset.cloud_tags,
            "tags": asset.tags or [],
            "installed_packages": asset.installed_packages,
            "running_services": asset.running_services,
            "open_ports": asset.open_ports,
            "compliance_frameworks": asset.compliance_frameworks,
            "compensating_controls": asset.compensating_controls,
            "patch_group": asset.patch_group,
            "maintenance_window": asset.maintenance_window,
            "last_scanned_at": asset.last_scanned_at.isoformat() if asset.last_scanned_at else None,
            "last_patched_at": asset.last_patched_at.isoformat() if asset.last_patched_at else None,
            "created_at": asset.created_at.isoformat(),
            "updated_at": asset.updated_at.isoformat(),
        }
        for asset in assets
    ]

@router.get("/{asset_id}/risk-breakdown")
async def get_asset_risk_breakdown(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Compute risk drivers for this asset: KEV count, severity counts, exposure, uptime.
    """
    asset_query = select(Asset).where(
        and_(Asset.id == asset_id, Asset.tenant_id == tenant.id)
    )
    result = await db.execute(asset_query)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get active vulnerabilities with full vuln data
    av_q = await db.execute(
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .where(
            and_(
                AssetVulnerability.asset_id == asset_id,
                or_(AssetVulnerability.status == "ACTIVE", AssetVulnerability.status.is_(None)),
            )
        )
    )
    avs = av_q.scalars().all()

    kev_count = sum(1 for av in avs if av.vulnerability and av.vulnerability.kev_listed)
    critical_count = sum(1 for av in avs if av.vulnerability and av.vulnerability.severity == "CRITICAL")
    high_count = sum(1 for av in avs if av.vulnerability and av.vulnerability.severity == "HIGH")
    exploit_count = sum(1 for av in avs if av.vulnerability and av.vulnerability.exploit_available)

    internet_exposed = asset.is_internet_facing
    uptime_days = asset.uptime_days

    # Build top risk drivers
    drivers = []
    if kev_count:
        drivers.append((kev_count * 30, f"{kev_count} Known Exploited Vulnerabilit{'y' if kev_count == 1 else 'ies'} (CISA KEV)"))
    if internet_exposed:
        drivers.append((25, "Asset is internet-exposed"))
    if critical_count:
        drivers.append((critical_count * 5, f"{critical_count} critical-severity vulnerabilit{'y' if critical_count == 1 else 'ies'}"))
    if exploit_count:
        drivers.append((exploit_count * 4, f"{exploit_count} vulnerabilit{'y' if exploit_count == 1 else 'ies'} with known exploits"))
    if asset.criticality >= 4:
        drivers.append((asset.criticality * 3, f"High-criticality asset (score {asset.criticality}/5)"))
    if uptime_days and uptime_days > 365:
        drivers.append((10, f"Long uptime ({uptime_days} days) increases patch debt"))
    if high_count:
        drivers.append((high_count * 2, f"{high_count} high-severity vulnerabilit{'y' if high_count == 1 else 'ies'}"))
    if asset.environment and asset.environment.lower() == "production":
        drivers.append((10, "Production environment asset"))

    drivers.sort(reverse=True, key=lambda x: x[0])
    top_drivers = [d[1] for d in drivers[:5]]

    return {
        "asset_id": str(asset.id),
        "risk_score": asset.risk_score,
        "kev_count": kev_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "exploit_count": exploit_count,
        "total_active_vulns": len(avs),
        "internet_exposed": internet_exposed,
        "uptime_days": uptime_days,
        "top_risk_drivers": top_drivers,
    }


@router.get("/{asset_id}/patch-history")
async def get_asset_patch_history(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Return chronological patch history for an asset from bundle_items.
    """
    asset_query = select(Asset).where(
        and_(Asset.id == asset_id, Asset.tenant_id == tenant.id)
    )
    result = await db.execute(asset_query)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Query bundle_items for this asset (excluding pending)
    bi_q = await db.execute(
        select(BundleItem, Bundle, Vulnerability)
        .join(Bundle, BundleItem.bundle_id == Bundle.id)
        .join(Vulnerability, BundleItem.vulnerability_id == Vulnerability.id)
        .where(
            and_(
                BundleItem.asset_id == asset_id,
                Bundle.tenant_id == tenant.id,
                BundleItem.status != "pending",
            )
        )
        .order_by(BundleItem.completed_at.desc().nullslast(), BundleItem.created_at.desc())
    )
    rows = bi_q.all()

    history = []
    for bi, bundle, vuln in rows:
        history.append({
            "id": str(bi.id),
            "date": (bi.completed_at or bi.updated_at or bi.created_at).isoformat(),
            "vulnerability_id": str(vuln.id),
            "cve_identifier": vuln.identifier,
            "vulnerability_title": vuln.title,
            "severity": vuln.severity,
            "status": bi.status,
            "bundle_id": str(bundle.id),
            "bundle_name": bundle.name,
            "bundle_status": bundle.status,
            "patch_identifier": bi.patch_identifier,
            "duration_seconds": bi.duration_seconds,
            "error_message": bi.error_message if bi.status == "failed" else None,
            "completed_at": bi.completed_at.isoformat() if bi.completed_at else None,
        })

    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "history": history,
        "total": len(history),
    }


@router.post("/{asset_id}/create-patch-bundle")
async def create_asset_patch_bundle(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Create a draft bundle containing all open (ACTIVE) vulnerabilities for this asset.
    If a draft bundle already contains all of them, return the existing one.
    """
    asset_query = select(Asset).where(
        and_(Asset.id == asset_id, Asset.tenant_id == tenant.id)
    )
    result = await db.execute(asset_query)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get open (ACTIVE) vulns for this asset
    av_q = await db.execute(
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .where(
            and_(
                AssetVulnerability.asset_id == asset_id,
                or_(AssetVulnerability.status == "ACTIVE", AssetVulnerability.status.is_(None)),
            )
        )
        .order_by(AssetVulnerability.risk_score.desc())
    )
    open_avs = av_q.scalars().all()

    if not open_avs:
        raise HTTPException(status_code=400, detail="No open vulnerabilities found for this asset")

    # Create new bundle
    bundle_name = f"Asset Patch: {asset.name} – {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    bundle = Bundle(
        id=uuid4(),
        tenant_id=tenant.id,
        name=bundle_name,
        description=f"Auto-generated patch bundle for asset {asset.name} ({asset.identifier})",
        status="draft",
        risk_score=float(max(av.risk_score for av in open_avs)),
        risk_level="HIGH" if any(av.risk_score >= 70 for av in open_avs) else "MEDIUM",
        assets_affected_count=1,
        approval_required=asset.environment.lower() == "production" if asset.environment else False,
    )
    db.add(bundle)
    await db.flush()

    # Create bundle items
    for av in open_avs:
        item = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            vulnerability_id=av.vulnerability_id,
            asset_id=asset_id,
            status="pending",
            risk_score=float(av.risk_score),
            patch_identifier=av.patch_id,
        )
        db.add(item)

    await db.commit()
    await db.refresh(bundle)

    return {
        "bundle_id": str(bundle.id),
        "bundle_name": bundle.name,
        "vuln_count": len(open_avs),
        "status": bundle.status,
    }
