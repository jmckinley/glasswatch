"""
Asset API endpoints.

Provides CRUD operations for infrastructure assets and bulk import capabilities.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
import json
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, and_, or_, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
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
    
    asset.updated_at = datetime.utcnow()
    
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
                
                existing_asset.updated_at = datetime.utcnow()
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


@router.get("/{asset_id}/vulnerabilities")
async def get_asset_vulnerabilities(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: Optional[str] = Query("ACTIVE", description="Filter by status"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score"),
) -> Dict[str, Any]:
    """
    Get all vulnerabilities for a specific asset.
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
    
    # Get vulnerabilities
    query = (
        select(AssetVulnerability)
        .options(selectinload(AssetVulnerability.vulnerability))
        .where(AssetVulnerability.asset_id == asset_id)
    )
    
    # Apply filters
    if status:
        query = query.where(AssetVulnerability.status == status)
    
    if min_score is not None:
        query = query.where(AssetVulnerability.risk_score >= min_score)
    
    # Order by risk score
    query = query.order_by(AssetVulnerability.risk_score.desc())
    
    result = await db.execute(query)
    vulnerabilities = result.scalars().all()
    
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
                "risk_score": av.risk_score,
                "score_factors": av.score_factors,
                "status": av.status,
                "code_executed": av.code_executed,
                "library_loaded": av.library_loaded,
                "execution_frequency": av.execution_frequency,
                "recommended_action": av.recommended_action,
                "patch_available": av.patch_available,
                "mitigation_applied": av.mitigation_applied,
                "discovered_at": av.discovered_at.isoformat(),
                "last_reviewed_at": av.last_reviewed_at.isoformat() if av.last_reviewed_at else None,
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
    asset.updated_at = datetime.utcnow()
    
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
            asset.updated_at = datetime.utcnow()
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
            asset.updated_at = datetime.utcnow()
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