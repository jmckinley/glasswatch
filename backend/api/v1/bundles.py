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
from backend.models.user import User
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.services.deployment_service import deployment_service
from backend.services.rule_engine import rule_engine
from backend.services.notifications import notification_service


router = APIRouter()


@router.get("")
async def list_bundles(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: Optional[str] = Query(None, description="Filter by status"),
    goal_id: Optional[UUID] = Query(None, description="Filter by goal"),
    maintenance_window_id: Optional[str] = Query(None, description="Filter by window ID or 'unassigned'"),
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
    if maintenance_window_id:
        if maintenance_window_id == "unassigned":
            query = query.where(Bundle.maintenance_window_id.is_(None))
        else:
            query = query.where(Bundle.maintenance_window_id == UUID(maintenance_window_id))
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
        select(Bundle)
        .where(
            and_(
                Bundle.id == bundle_id,
                Bundle.tenant_id == tenant.id
            )
        )
        .options(selectinload(Bundle.items).selectinload(BundleItem.asset))
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(404, "Bundle not found")
    
    # Rule evaluation for scheduled/approved status changes
    rule_eval_result = None
    if new_status in ["scheduled", "approved"]:
        # Collect assets from bundle items
        assets = [item.asset for item in bundle.items if item.asset]
        asset_tags = set()
        environments = set()
        
        for asset in assets:
            if asset.tags:
                asset_tags.update(asset.tags)
            if asset.environment:
                environments.add(asset.environment)
        
        # Determine primary environment (most common)
        primary_env = max(environments, key=list(environments).count) if environments else None
        
        # Get maintenance window if assigned
        window = None
        if bundle.maintenance_window_id:
            from backend.models.maintenance_window import MaintenanceWindow
            window_result = await db.execute(
                select(MaintenanceWindow).where(MaintenanceWindow.id == bundle.maintenance_window_id)
            )
            window = window_result.scalar_one_or_none()
        
        # Evaluate deployment rules
        rule_eval_result = await rule_engine.evaluate_deployment(
            db=db,
            tenant_id=str(tenant.id),
            bundle=bundle,
            assets=assets,
            asset_tags=list(asset_tags),
            environment=primary_env,
            target_window=window
        )
        
        # Block if verdict is "block"
        if rule_eval_result.verdict == "block":
            blocking_rule = rule_eval_result.matches[0] if rule_eval_result.matches else None
            raise HTTPException(
                403,
                f"Deployment blocked by rule: {blocking_rule.message if blocking_rule else 'Unknown rule'}"
            )
    
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
    
    # Send notification for scheduled/approved bundles
    if new_status in ["scheduled", "approved"]:
        try:
            await notification_service.send_bundle_ready_notification(
                db=db,
                bundle=bundle,
                tenant_id=str(tenant.id)
            )
        except Exception as e:
            # Don't fail the request if notification fails
            import logging
            logging.warning(f"Failed to send bundle notification: {e}")
    
    # Include rule evaluation results in response if available
    response = bundle.to_dict()
    if rule_eval_result:
        response["rule_evaluation"] = {
            "verdict": rule_eval_result.verdict,
            "warnings": [
                {"rule": m.rule_name, "message": m.message}
                for m in rule_eval_result.matches
                if m.action_type == "warn"
            ],
            "evaluated_count": rule_eval_result.evaluated_count
        }
    
    return response


@router.post("/{bundle_id}/execute")
async def execute_bundle(
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    # TODO: Add current_user dependency when auth is fully integrated
    # current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start execution of a bundle.
    
    Executes the deployment workflow:
    1. Validates bundle is approved
    2. Checks deployment rules
    3. Executes each patch in the bundle
    4. Tracks progress and status
    5. Creates audit logs
    6. Sends notifications
    
    Returns execution results with success/failure counts.
    """
    # Execute bundle using deployment service
    result = await deployment_service.execute_bundle(
        db=db,
        bundle_id=bundle_id,
        tenant_id=tenant.id,
        # user_id=current_user.id if current_user else None
        user_id=None  # TODO: Pass actual user ID when auth integrated
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Bundle execution failed")
        )
    
    return result


@router.patch("/{bundle_id}/assign-window")
async def assign_bundle_to_window(
    bundle_id: UUID,
    assignment: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Assign or unassign a bundle to/from a maintenance window.
    
    Validates capacity, risk, and asset constraints before assignment.
    """
    from backend.models.maintenance_window import MaintenanceWindow
    
    # Get the bundle
    result = await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.id == bundle_id,
                Bundle.tenant_id == tenant.id
            )
        )
        .options(selectinload(Bundle.items).selectinload(BundleItem.asset))
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(404, "Bundle not found")
    
    window_id = assignment.get("maintenance_window_id")
    
    # Unassign case
    if window_id is None:
        bundle.maintenance_window_id = None
        if bundle.status == "scheduled":
            bundle.status = "draft"
        bundle.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(bundle)
        return bundle.to_dict()
    
    # Assign case - validate window exists
    window_uuid = UUID(window_id) if isinstance(window_id, str) else window_id
    window_result = await db.execute(
        select(MaintenanceWindow)
        .where(
            and_(
                MaintenanceWindow.id == window_uuid,
                MaintenanceWindow.tenant_id == tenant.id
            )
        )
        .options(selectinload(MaintenanceWindow.bundles).selectinload(Bundle.items))
    )
    window = window_result.scalar_one_or_none()
    
    if not window:
        raise HTTPException(404, "Maintenance window not found")
    
    # Calculate current window utilization (excluding this bundle if already assigned)
    current_bundles = [b for b in window.bundles if b.id != bundle_id]
    total_duration = sum(b.estimated_duration_minutes or 0 for b in current_bundles)
    total_assets = sum(b.assets_affected_count or 0 for b in current_bundles)
    max_risk = max((b.risk_score or 0 for b in current_bundles), default=0)
    
    # Check capacity constraints
    window_duration_minutes = window.duration_hours * 60
    new_total_duration = total_duration + (bundle.estimated_duration_minutes or 0)
    
    if new_total_duration > window_duration_minutes:
        raise HTTPException(
            400,
            f"Bundle duration ({bundle.estimated_duration_minutes} min) exceeds window capacity. "
            f"Available: {window_duration_minutes - total_duration} min of {window_duration_minutes} min total."
        )
    
    # Check risk constraints
    if window.max_risk_score and bundle.risk_score:
        if bundle.risk_score > window.max_risk_score:
            raise HTTPException(
                400,
                f"Bundle risk score ({bundle.risk_score:.1f}) exceeds window maximum ({window.max_risk_score:.1f})"
            )
    
    # Check asset constraints
    if window.max_assets:
        new_total_assets = total_assets + (bundle.assets_affected_count or 0)
        if new_total_assets > window.max_assets:
            raise HTTPException(
                400,
                f"Bundle affects {bundle.assets_affected_count} assets, which would exceed window limit. "
                f"Available: {window.max_assets - total_assets} of {window.max_assets} total."
            )
    
    # Evaluate deployment rules before assigning
    assets = [item.asset for item in bundle.items if item.asset]
    asset_tags = set()
    environments = set()
    
    for asset in assets:
        if asset.tags:
            asset_tags.update(asset.tags)
        if asset.environment:
            environments.add(asset.environment)
    
    # Determine primary environment
    primary_env = max(environments, key=list(environments).count) if environments else None
    
    # Evaluate rules
    rule_eval_result = await rule_engine.evaluate_deployment(
        db=db,
        tenant_id=str(tenant.id),
        bundle=bundle,
        assets=assets,
        asset_tags=list(asset_tags),
        environment=primary_env,
        target_window=window
    )
    
    # Block if verdict is "block"
    if rule_eval_result.verdict == "block":
        blocking_rule = rule_eval_result.matches[0] if rule_eval_result.matches else None
        raise HTTPException(
            403,
            f"Deployment blocked by rule: {blocking_rule.message if blocking_rule else 'Unknown rule'}"
        )
    
    # All checks passed - assign bundle
    bundle.maintenance_window_id = window_uuid
    bundle.status = "scheduled"
    bundle.scheduled_for = window.start_time
    bundle.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(bundle)
    
    # Send notification when bundle is scheduled
    try:
        await notification_service.send_bundle_ready_notification(
            db=db,
            bundle=bundle,
            tenant_id=str(tenant.id)
        )
    except Exception as e:
        # Don't fail the request if notification fails
        import logging
        logging.warning(f"Failed to send bundle notification: {e}")
    
    # Include rule evaluation results in response
    response = bundle.to_dict()
    response["rule_evaluation"] = {
        "verdict": rule_eval_result.verdict,
        "warnings": [
            {"rule": m.rule_name, "message": m.message}
            for m in rule_eval_result.matches
            if m.action_type == "warn"
        ],
        "evaluated_count": rule_eval_result.evaluated_count
    }
    
    return response

@router.get("/stats")
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