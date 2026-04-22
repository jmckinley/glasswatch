"""
Maintenance Window API endpoints.

Manages approved time windows for patching activities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.maintenance_window import MaintenanceWindow
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant


router = APIRouter()


class WindowCreate(BaseModel):
    """Request model for creating a maintenance window."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = Field("scheduled", pattern="^(scheduled|emergency|blackout)$")
    start_time: datetime
    end_time: datetime
    timezone: Optional[str] = Field(None, max_length=50)
    environment: Optional[str] = Field(None, max_length=50)
    max_duration_hours: Optional[float] = Field(None, ge=0.5, le=24)
    max_assets: Optional[int] = Field(None, ge=1)
    approved_activities: List[str] = Field(default_factory=lambda: ["patching"])
    # Sprint 13 additions
    priority: int = Field(default=0, ge=0, le=100)
    asset_group: Optional[str] = Field(None, max_length=100)
    service_name: Optional[str] = Field(None, max_length=100)
    is_default: bool = Field(default=False)
    

class WindowUpdate(BaseModel):
    """Request model for updating a maintenance window."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    active: Optional[bool] = None
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    max_duration_hours: Optional[float] = Field(None, ge=0.5, le=24)
    max_assets: Optional[int] = Field(None, ge=1)
    change_freeze: Optional[bool] = None
    change_freeze_reason: Optional[str] = None
    # Sprint 13 additions
    priority: Optional[int] = Field(None, ge=0, le=100)
    asset_group: Optional[str] = Field(None, max_length=100)
    service_name: Optional[str] = Field(None, max_length=100)
    is_default: Optional[bool] = None


@router.get("")
async def list_maintenance_windows(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    type: Optional[str] = Query(None, description="Filter by type"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    asset_group: Optional[str] = Query(None, description="Filter by asset group"),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    active_only: bool = Query(True, description="Only show active windows"),
    future_only: bool = Query(True, description="Only show future windows"),
    approved_only: bool = Query(False, description="Only show approved windows"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List maintenance windows with filtering.
    
    Returns windows with their scheduled bundle counts.
    """
    query = select(MaintenanceWindow).where(MaintenanceWindow.tenant_id == tenant.id)
    
    # Apply filters
    if type:
        query = query.where(MaintenanceWindow.type == type)
    if environment:
        query = query.where(MaintenanceWindow.environment == environment)
    if asset_group:
        query = query.where(MaintenanceWindow.asset_group == asset_group)
    if service_name:
        query = query.where(MaintenanceWindow.service_name == service_name)
    if active_only:
        query = query.where(MaintenanceWindow.active == True)
    if future_only:
        query = query.where(MaintenanceWindow.start_time > datetime.now(timezone.utc))
    if approved_only:
        query = query.where(MaintenanceWindow.approved == True)
    
    # Order by start time
    query = query.order_by(MaintenanceWindow.start_time.asc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results with bundles and their items with vulnerability data
    query = query.options(
        selectinload(MaintenanceWindow.bundles)
        .selectinload(Bundle.items)
        .selectinload(BundleItem.vulnerability)
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    windows = result.scalars().all()
    
    # Format response
    items = []
    for window in windows:
        window_dict = window.to_dict()
        window_dict["bundles_count"] = len(window.bundles)
        window_dict["scheduled_bundles"] = [
            {
                "id": str(bundle.id),
                "name": bundle.name,
                "status": bundle.status,
                "risk_score": bundle.risk_score,
                "estimated_duration_minutes": bundle.estimated_duration_minutes,
                "assets_affected_count": bundle.assets_affected_count,
                "items_count": len(bundle.items),
                "items": [
                    {
                        "id": str(item.id),
                        "vulnerability": {
                            "identifier": item.vulnerability.identifier,
                            "title": item.vulnerability.title,
                            "severity": item.vulnerability.severity,
                        } if item.vulnerability else None,
                    }
                    for item in bundle.items
                ],
            }
            for bundle in window.bundles
            if bundle.status in ["scheduled", "approved"]
        ]
        items.append(window_dict)
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("")
async def create_maintenance_window(
    window_data: WindowCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Create a new maintenance window.
    
    Emergency windows can overlap with existing windows.
    Scheduled windows should not overlap unless explicitly allowed.
    """
    # Validate time range
    if window_data.end_time <= window_data.start_time:
        raise HTTPException(400, "End time must be after start time")
    
    if window_data.start_time < datetime.now(timezone.utc):
        if window_data.type != "emergency":
            raise HTTPException(400, "Only emergency windows can be created in the past")
    
    # Check for overlapping windows (warning only for now)
    if window_data.type == "scheduled":
        overlap_query = select(MaintenanceWindow).where(
            and_(
                MaintenanceWindow.tenant_id == tenant.id,
                MaintenanceWindow.active == True,
                MaintenanceWindow.type != "blackout",
                or_(
                    and_(
                        MaintenanceWindow.start_time <= window_data.start_time,
                        MaintenanceWindow.end_time > window_data.start_time
                    ),
                    and_(
                        MaintenanceWindow.start_time < window_data.end_time,
                        MaintenanceWindow.end_time >= window_data.end_time
                    )
                )
            )
        )
        overlap_result = await db.execute(overlap_query)
        overlapping = overlap_result.scalars().all()
        
        if overlapping:
            # Just a warning for now - in production might want to block
            print(f"Warning: New window overlaps with {len(overlapping)} existing windows")
    
    # Create window
    window = MaintenanceWindow(
        tenant_id=tenant.id,
        name=window_data.name,
        description=window_data.description,
        type=window_data.type,
        start_time=window_data.start_time,
        end_time=window_data.end_time,
        timezone=window_data.timezone,
        environment=window_data.environment,
        max_duration_hours=window_data.max_duration_hours,
        max_assets=window_data.max_assets,
        approved_activities=window_data.approved_activities,
        priority=window_data.priority,
        asset_group=window_data.asset_group,
        service_name=window_data.service_name,
        is_default=window_data.is_default,
        active=True,
        approved=window_data.type == "emergency",  # Auto-approve emergency windows
        approved_at=datetime.now(timezone.utc) if window_data.type == "emergency" else None,
        approved_by="system" if window_data.type == "emergency" else None,
    )
    
    db.add(window)
    await db.commit()
    await db.refresh(window)
    
    return window.to_dict()


@router.get("/{window_id}")
async def get_maintenance_window(
    window_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Get detailed information about a maintenance window."""
    result = await db.execute(
        select(MaintenanceWindow)
        .where(
            and_(
                MaintenanceWindow.id == window_id,
                MaintenanceWindow.tenant_id == tenant.id
            )
        )
        .options(selectinload(MaintenanceWindow.bundles))
    )
    window = result.scalar_one_or_none()
    
    if not window:
        raise HTTPException(404, "Maintenance window not found")
    
    window_dict = window.to_dict()
    window_dict["bundles"] = [bundle.to_dict() for bundle in window.bundles]
    
    # Calculate utilization
    total_bundle_duration = sum(
        bundle.estimated_duration_minutes or 0
        for bundle in window.bundles
        if bundle.status in ["scheduled", "approved", "in_progress"]
    )
    window_duration_minutes = window.duration_hours * 60
    window_dict["utilization_percentage"] = (
        (total_bundle_duration / window_duration_minutes * 100)
        if window_duration_minutes > 0 else 0
    )
    
    return window_dict


@router.patch("/{window_id}")
async def update_maintenance_window(
    window_id: UUID,
    updates: WindowUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Update a maintenance window."""
    result = await db.execute(
        select(MaintenanceWindow).where(
            and_(
                MaintenanceWindow.id == window_id,
                MaintenanceWindow.tenant_id == tenant.id
            )
        )
    )
    window = result.scalar_one_or_none()
    
    if not window:
        raise HTTPException(404, "Maintenance window not found")
    
    # Don't allow changes to past windows
    if window.end_time < datetime.now(timezone.utc):
        raise HTTPException(400, "Cannot modify past maintenance windows")
    
    # Apply updates
    update_data = updates.dict(exclude_unset=True)
    
    # Handle approval specially
    if "approved" in update_data and update_data["approved"]:
        window.approved = True
        window.approved_at = datetime.now(timezone.utc)
        window.approved_by = update_data.get("approved_by", "system")
        update_data.pop("approved")
        update_data.pop("approved_by", None)
    
    for field, value in update_data.items():
        setattr(window, field, value)
    
    window.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(window)
    
    return window.to_dict()


@router.delete("/{window_id}")
async def delete_maintenance_window(
    window_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Delete a maintenance window.
    
    Can only delete future windows with no scheduled bundles.
    """
    result = await db.execute(
        select(MaintenanceWindow)
        .where(
            and_(
                MaintenanceWindow.id == window_id,
                MaintenanceWindow.tenant_id == tenant.id
            )
        )
        .options(selectinload(MaintenanceWindow.bundles))
    )
    window = result.scalar_one_or_none()
    
    if not window:
        raise HTTPException(404, "Maintenance window not found")
    
    if window.start_time < datetime.now(timezone.utc):
        raise HTTPException(400, "Cannot delete past or active maintenance windows")
    
    scheduled_bundles = [b for b in window.bundles if b.status in ["scheduled", "approved"]]
    if scheduled_bundles:
        raise HTTPException(
            400, 
            f"Cannot delete window with {len(scheduled_bundles)} scheduled bundles. "
            "Reschedule or cancel bundles first."
        )
    
    await db.delete(window)
    await db.commit()
    
    return {"message": f"Maintenance window '{window.name}' deleted successfully"}


@router.post("/create-recurring")
async def create_recurring_windows(
    recurrence_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Create recurring maintenance windows (e.g., weekly, monthly).
    
    This is a convenience endpoint for creating multiple windows at once.
    """
    pattern = recurrence_data.get("pattern", "weekly")  # weekly, biweekly, monthly
    count = recurrence_data.get("count", 4)  # Number of windows to create
    duration_hours = recurrence_data.get("duration_hours", 4)
    start_hour = recurrence_data.get("start_hour", 2)  # 2 AM default
    day_of_week = recurrence_data.get("day_of_week", 6)  # Sunday = 6
    environment = recurrence_data.get("environment", "production")
    
    # Find next occurrence
    current = datetime.now(timezone.utc)
    while current.weekday() != day_of_week:
        current += timedelta(days=1)
    current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    # If the first window would be in the past, skip to next week
    if current < datetime.now(timezone.utc):
        current += timedelta(weeks=1)
    
    created_windows = []
    for i in range(count):
        window = MaintenanceWindow(
            tenant_id=tenant.id,
            name=f"{pattern.title()} Maintenance - {current.strftime('%Y-%m-%d')}",
            type="scheduled",
            start_time=current,
            end_time=current + timedelta(hours=duration_hours),
            environment=environment,
            max_duration_hours=duration_hours,
            approved_activities=["patching", "updates", "restarts"],
            active=True,
            approved=False,
        )
        db.add(window)
        created_windows.append(window)
        
        # Move to next occurrence
        if pattern == "weekly":
            current += timedelta(weeks=1)
        elif pattern == "biweekly":
            current += timedelta(weeks=2)
        elif pattern == "monthly":
            # Simple monthly - same day of month (might need adjustment for month boundaries)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    await db.commit()
    
    return {
        "message": f"Created {len(created_windows)} recurring maintenance windows",
        "windows": [w.to_dict() for w in created_windows],
    }


@router.get("/resolve")
async def resolve_maintenance_window(
    asset_id: Optional[UUID] = Query(None, description="Asset ID to resolve window for"),
    environment: Optional[str] = Query(None, description="Environment override"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Resolve the best matching maintenance window for a given asset.
    
    Uses priority/specificity rules to find the most appropriate window.
    """
    from backend.models.asset import Asset
    
    asset = None
    if asset_id:
        result = await db.execute(
            select(Asset).where(
                and_(
                    Asset.id == asset_id,
                    Asset.tenant_id == tenant.id
                )
            )
        )
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise HTTPException(404, "Asset not found")
    
    # Find best matching window
    window = await MaintenanceWindow.find_best_window(
        db=db,
        tenant_id=tenant.id,
        asset=asset,
        environment=environment,
    )
    
    if not window:
        return {
            "window": None,
            "message": "No matching maintenance window found",
        }
    
    return {
        "window": window.to_dict(),
        "match_reason": _get_match_reason(window, asset, environment),
    }


def _get_match_reason(window: MaintenanceWindow, asset, environment: Optional[str]) -> str:
    """Helper to explain why this window was selected."""
    if window.service_name and window.environment:
        return f"Exact match: service '{window.service_name}' in environment '{window.environment}'"
    elif window.asset_group and window.environment:
        return f"Asset group match: '{window.asset_group}' in environment '{window.environment}'"
    elif window.environment:
        return f"Environment match: '{window.environment}'"
    elif window.is_default:
        return "Default fallback window"
    else:
        return "Generic window"


@router.get("/environments")
async def list_environments(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    List distinct environments across all maintenance windows.
    """
    result = await db.execute(
        select(MaintenanceWindow.environment)
        .where(
            and_(
                MaintenanceWindow.tenant_id == tenant.id,
                MaintenanceWindow.environment.isnot(None),
            )
        )
        .distinct()
    )
    environments = [row[0] for row in result.fetchall()]
    
    return {"environments": sorted(environments)}


@router.get("/asset-groups")
async def list_asset_groups(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    List distinct asset groups across all maintenance windows.
    """
    result = await db.execute(
        select(MaintenanceWindow.asset_group)
        .where(
            and_(
                MaintenanceWindow.tenant_id == tenant.id,
                MaintenanceWindow.asset_group.isnot(None),
            )
        )
        .distinct()
    )
    asset_groups = [row[0] for row in result.fetchall()]
    
    return {"asset_groups": sorted(asset_groups)}