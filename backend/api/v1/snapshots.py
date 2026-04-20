"""
Snapshot and rollback API endpoints.

Provides snapshot capture, comparison, and rollback capabilities.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.db.session import get_db
from backend.models.snapshot import PatchSnapshot, RollbackRecord, SnapshotType
from backend.models.tenant import Tenant
from backend.core.auth import get_current_tenant
from backend.services.snapshot_service import snapshot_service


router = APIRouter()


# Request/Response models
class CaptureSnapshotRequest(BaseModel):
    """Request to capture a snapshot."""
    bundle_id: UUID
    asset_id: UUID
    snapshot_type: str = Field(..., description="pre_patch, post_patch, or manual")


class InitiateRollbackRequest(BaseModel):
    """Request to initiate a rollback."""
    bundle_id: UUID
    asset_id: UUID
    trigger: str = Field(..., description="manual, health_check_failed, automated, or approval_rejected")
    reason: str = Field(..., min_length=1, max_length=1000)


@router.post("/capture")
async def capture_snapshot(
    request: CaptureSnapshotRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Capture a system snapshot.
    
    Creates a point-in-time snapshot of system state for rollback capability.
    """
    try:
        # Validate snapshot type
        snapshot_type = SnapshotType(request.snapshot_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid snapshot_type. Must be one of: {', '.join([t.value for t in SnapshotType])}"
        )
    
    try:
        snapshot = await snapshot_service.capture_snapshot(
            db=db,
            bundle_id=request.bundle_id,
            asset_id=request.asset_id,
            tenant_id=tenant.id,
            snapshot_type=snapshot_type
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture snapshot: {str(e)}")
    
    return {
        "id": str(snapshot.id),
        "bundle_id": str(snapshot.bundle_id),
        "asset_id": str(snapshot.asset_id),
        "snapshot_type": snapshot.snapshot_type.value,
        "size_bytes": snapshot.size_bytes,
        "checksum": snapshot.checksum,
        "created_at": snapshot.created_at.isoformat(),
        "expires_at": snapshot.expires_at.isoformat(),
        "metadata": snapshot.metadata
    }


@router.get("")
async def list_snapshots(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    bundle_id: Optional[UUID] = Query(None, description="Filter by bundle"),
    asset_id: Optional[UUID] = Query(None, description="Filter by asset"),
    snapshot_type: Optional[str] = Query(None, description="Filter by type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List snapshots with filtering.
    
    Returns paginated list of snapshots for the current tenant.
    """
    # Build query
    query = select(PatchSnapshot).where(PatchSnapshot.tenant_id == tenant.id)
    
    # Apply filters
    filters = []
    
    if bundle_id:
        filters.append(PatchSnapshot.bundle_id == bundle_id)
    
    if asset_id:
        filters.append(PatchSnapshot.asset_id == asset_id)
    
    if snapshot_type:
        try:
            st = SnapshotType(snapshot_type)
            filters.append(PatchSnapshot.snapshot_type == st)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid snapshot_type. Must be one of: {', '.join([t.value for t in SnapshotType])}"
            )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(PatchSnapshot.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    snapshots = result.scalars().all()
    
    return {
        "snapshots": [
            {
                "id": str(s.id),
                "bundle_id": str(s.bundle_id),
                "asset_id": str(s.asset_id),
                "snapshot_type": s.snapshot_type.value,
                "size_bytes": s.size_bytes,
                "checksum": s.checksum,
                "created_at": s.created_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
            }
            for s in snapshots
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{snapshot_id}")
async def get_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get snapshot detail.
    
    Returns full snapshot including system state.
    """
    result = await db.execute(
        select(PatchSnapshot).where(
            and_(
                PatchSnapshot.id == snapshot_id,
                PatchSnapshot.tenant_id == tenant.id
            )
        )
    )
    snapshot = result.scalar_one_or_none()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "id": str(snapshot.id),
        "bundle_id": str(snapshot.bundle_id),
        "asset_id": str(snapshot.asset_id),
        "tenant_id": str(snapshot.tenant_id),
        "snapshot_type": snapshot.snapshot_type.value,
        "system_state": snapshot.system_state,
        "metadata": snapshot.metadata,
        "checksum": snapshot.checksum,
        "size_bytes": snapshot.size_bytes,
        "created_at": snapshot.created_at.isoformat(),
        "expires_at": snapshot.expires_at.isoformat(),
        "is_valid": snapshot.validate_integrity()
    }


@router.post("/{pre_id}/compare/{post_id}")
async def compare_snapshots(
    pre_id: UUID,
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Compare two snapshots.
    
    Returns differences between pre and post snapshots.
    """
    # Verify both snapshots belong to tenant
    pre_result = await db.execute(
        select(PatchSnapshot).where(
            and_(
                PatchSnapshot.id == pre_id,
                PatchSnapshot.tenant_id == tenant.id
            )
        )
    )
    pre = pre_result.scalar_one_or_none()
    
    post_result = await db.execute(
        select(PatchSnapshot).where(
            and_(
                PatchSnapshot.id == post_id,
                PatchSnapshot.tenant_id == tenant.id
            )
        )
    )
    post = post_result.scalar_one_or_none()
    
    if not pre or not post:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")
    
    try:
        comparison = await snapshot_service.compare_snapshots(db, pre_id, post_id)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare snapshots: {str(e)}")


@router.post("/rollbacks")
async def initiate_rollback(
    request: InitiateRollbackRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Initiate a rollback operation.
    
    Creates a rollback record and prepares for execution.
    """
    try:
        rollback = await snapshot_service.initiate_rollback(
            db=db,
            bundle_id=request.bundle_id,
            asset_id=request.asset_id,
            tenant_id=tenant.id,
            trigger=request.trigger,
            reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate rollback: {str(e)}")
    
    return {
        "id": str(rollback.id),
        "bundle_id": str(rollback.bundle_id),
        "asset_id": str(rollback.asset_id),
        "snapshot_id": str(rollback.snapshot_id),
        "trigger": rollback.trigger,
        "status": rollback.status.value,
        "reason": rollback.reason,
        "started_at": rollback.started_at.isoformat()
    }


@router.get("/rollbacks")
async def list_rollbacks(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    bundle_id: Optional[UUID] = Query(None, description="Filter by bundle"),
    asset_id: Optional[UUID] = Query(None, description="Filter by asset"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List rollback records with filtering.
    
    Returns paginated list of rollbacks for the current tenant.
    """
    # Build query
    query = select(RollbackRecord).where(RollbackRecord.tenant_id == tenant.id)
    
    # Apply filters
    filters = []
    
    if bundle_id:
        filters.append(RollbackRecord.bundle_id == bundle_id)
    
    if asset_id:
        filters.append(RollbackRecord.asset_id == asset_id)
    
    if status:
        filters.append(RollbackRecord.status == status)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(RollbackRecord.started_at.desc())
    
    # Execute query
    result = await db.execute(query)
    rollbacks = result.scalars().all()
    
    return {
        "rollbacks": [
            {
                "id": str(r.id),
                "bundle_id": str(r.bundle_id),
                "asset_id": str(r.asset_id),
                "snapshot_id": str(r.snapshot_id),
                "trigger": r.trigger,
                "status": r.status.value,
                "reason": r.reason,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_seconds": r.duration_seconds if r.is_complete else None
            }
            for r in rollbacks
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/rollbacks/{rollback_id}")
async def get_rollback(
    rollback_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get rollback detail and status.
    
    Returns full rollback information including execution results.
    """
    result = await db.execute(
        select(RollbackRecord).where(
            and_(
                RollbackRecord.id == rollback_id,
                RollbackRecord.tenant_id == tenant.id
            )
        )
    )
    rollback = result.scalar_one_or_none()
    
    if not rollback:
        raise HTTPException(status_code=404, detail="Rollback not found")
    
    return {
        "id": str(rollback.id),
        "bundle_id": str(rollback.bundle_id),
        "asset_id": str(rollback.asset_id),
        "tenant_id": str(rollback.tenant_id),
        "snapshot_id": str(rollback.snapshot_id),
        "trigger": rollback.trigger,
        "status": rollback.status.value,
        "reason": rollback.reason,
        "started_at": rollback.started_at.isoformat(),
        "completed_at": rollback.completed_at.isoformat() if rollback.completed_at else None,
        "error_message": rollback.error_message,
        "rollback_details": rollback.rollback_details,
        "duration_seconds": rollback.duration_seconds if rollback.is_complete else None,
        "is_complete": rollback.is_complete
    }


@router.post("/rollbacks/{rollback_id}/execute")
async def execute_rollback(
    rollback_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Execute a rollback operation.
    
    Triggers the actual rollback process.
    """
    # Verify rollback belongs to tenant
    result = await db.execute(
        select(RollbackRecord).where(
            and_(
                RollbackRecord.id == rollback_id,
                RollbackRecord.tenant_id == tenant.id
            )
        )
    )
    rollback = result.scalar_one_or_none()
    
    if not rollback:
        raise HTTPException(status_code=404, detail="Rollback not found")
    
    try:
        rollback = await snapshot_service.execute_rollback(db, rollback_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute rollback: {str(e)}")
    
    return {
        "id": str(rollback.id),
        "status": rollback.status.value,
        "completed_at": rollback.completed_at.isoformat() if rollback.completed_at else None,
        "error_message": rollback.error_message,
        "rollback_details": rollback.rollback_details,
        "duration_seconds": rollback.duration_seconds if rollback.is_complete else None
    }
