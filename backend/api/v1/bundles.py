"""
Bundle API endpoints.

Manages patch bundles created by the optimization engine.
"""
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant


router = APIRouter()


@router.get("")
async def list_bundles(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: Optional[str] = Query(None, description="Filter by status"),
    goal_id: Optional[UUID] = Query(None, description="Filter by goal"),
    scheduled_after: Optional[datetime] = Query(None, description="Scheduled after date"),
    scheduled_before: Optional[datetime] = Query(None, description="Scheduled before date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List patch bundles with filtering.
    
    Returns bundles with their associated vulnerability counts.
    """
    query = select(Bundle).where(Bundle.tenant_id == tenant.id)
    
    # Apply filters
    if status:
        query = query.where(Bundle.status == status)
    if goal_id:
        query = query.where(Bundle.goal_id == goal_id)
    if scheduled_after:
        query = query.where(Bundle.scheduled_for >= scheduled_after)
    if scheduled_before:
        query = query.where(Bundle.scheduled_for <= scheduled_before)
    
    # Order by scheduled date
    query = query.order_by(Bundle.scheduled_for.asc().nullslast(), Bundle.created_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results with items
    query = query.options(selectinload(Bundle.items)).offset(skip).limit(limit)
    result = await db.execute(query)
    bundles = result.scalars().all()
    
    # Format response
    items = []
    for bundle in bundles:
        bundle_dict = bundle.to_dict()
        bundle_dict["items_count"] = len(bundle.items)
        bundle_dict["total_risk_score"] = sum(item.risk_score for item in bundle.items)
        items.append(bundle_dict)
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }



@router.get("/stats")

@router.get("/{bundle_id}")
async def get_bundle(
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get detailed information about a bundle.
    
    Includes all bundle items with vulnerability and asset details.
    """
    result = await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.id == bundle_id,
                Bundle.tenant_id == tenant.id
            )
        )
        .options(
            selectinload(Bundle.items).selectinload(BundleItem.vulnerability),
            selectinload(Bundle.items).selectinload(BundleItem.asset),
        )
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(404, "Bundle not found")
    
    # Format response with detailed items
    bundle_dict = bundle.to_dict()
    bundle_dict["items"] = []
    
    for item in bundle.items:
        item_dict = item.to_dict()
        item_dict["vulnerability"] = {
            "id": str(item.vulnerability.id),
            "identifier": item.vulnerability.identifier,
            "severity": item.vulnerability.severity,
            "description": item.vulnerability.description,
        }
        item_dict["asset"] = {
            "id": str(item.asset.id),
            "name": item.asset.name,
            "identifier": item.asset.identifier,
            "type": item.asset.type,
            "criticality": item.asset.criticality,
        }
        bundle_dict["items"].append(item_dict)
    
    return bundle_dict


@router.patch("/{bundle_id}/status")
async def update_bundle_status(
    bundle_id: UUID,
    status_update: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Update bundle status (approve, start execution, complete, etc).
    """
    valid_statuses = ["draft", "scheduled", "approved", "in_progress", "completed", "failed", "cancelled"]
    new_status = status_update.get("status")
    
    if not new_status or new_status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.execute(
        select(Bundle).where(
            and_(
                Bundle.id == bundle_id,
                Bundle.tenant_id == tenant.id
            )
        )
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(404, "Bundle not found")
    
    # Update status and related fields
    bundle.status = new_status
    bundle.updated_at = datetime.now(timezone.utc)
    
    if new_status == "approved":
        bundle.approved_by = status_update.get("approved_by", "system")
        bundle.approved_at = datetime.now(timezone.utc)
    elif new_status == "in_progress":
        bundle.started_at = datetime.now(timezone.utc)
    elif new_status in ["completed", "failed"]:
        bundle.completed_at = datetime.now(timezone.utc)
        if bundle.started_at:
            duration = (bundle.completed_at - bundle.started_at).total_seconds() / 60
            bundle.actual_duration_minutes = int(duration)
    
    await db.commit()
    await db.refresh(bundle)
    
    return bundle.to_dict()


@router.post("/{bundle_id}/execute")
async def execute_bundle(
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Start execution of a bundle.
    
    This would integrate with patch deployment systems.
    """
    result = await db.execute(
        select(Bundle).where(
            and_(
                Bundle.id == bundle_id,
                Bundle.tenant_id == tenant.id
            )
        )
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(404, "Bundle not found")
    
    if bundle.status != "approved":
        raise HTTPException(400, "Bundle must be approved before execution")
    
    # Update bundle status
    bundle.status = "in_progress"
    bundle.started_at = datetime.now(timezone.utc)
    await db.commit()
    
    # TODO: Integrate with actual patch deployment systems
    # - Ansible
    # - SCCM
    # - AWS Systems Manager
    # - Custom scripts
    
    return {
        "message": f"Bundle '{bundle.name}' execution started",
        "bundle_id": str(bundle_id),
        "status": "in_progress",
    }

async def get_bundle_stats(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get bundle statistics for the dashboard.
    """
    # Count by status
    status_counts = await db.execute(
        select(
            Bundle.status,
            func.count(Bundle.id).label("count")
        )
        .where(Bundle.tenant_id == tenant.id)
        .group_by(Bundle.status)
    )
    
    by_status = {row.status: row.count for row in status_counts}
    
    # Get next scheduled bundle
    next_bundle_result = await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.tenant_id == tenant.id,
                Bundle.status.in_(["scheduled", "approved"]),
                Bundle.scheduled_for > datetime.now(timezone.utc)
            )
        )
        .order_by(Bundle.scheduled_for)
        .limit(1)
    )
    next_bundle = next_bundle_result.scalar_one_or_none()
    
    # Count pending approvals
    pending_approval = await db.execute(
        select(func.count(Bundle.id))
        .where(
            and_(
                Bundle.tenant_id == tenant.id,
                Bundle.status == "scheduled",
                Bundle.approval_required == True
            )
        )
    )
    pending_count = pending_approval.scalar()
    
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "pending_approval": pending_count,
        "next_scheduled": {
            "id": str(next_bundle.id),
            "name": next_bundle.name,
            "scheduled_for": next_bundle.scheduled_for.isoformat(),
        } if next_bundle else None,
    }