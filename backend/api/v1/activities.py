"""
Activity API endpoints.

Manages activity feed and notifications.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.activity import ActivityType
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant, get_current_user
from backend.services.collaboration_service import CollaborationService


router = APIRouter()
collab_service = CollaborationService()


# Pydantic schemas
class MarkReadRequest(BaseModel):
    activity_ids: List[UUID] = Field(..., min_items=1)


@router.get("/")
async def get_activity_feed(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    activity_type: Optional[ActivityType] = Query(None, description="Filter by activity type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> Dict[str, Any]:
    """
    Get activity feed for the tenant.
    
    Shows recent activities across all entities.
    """
    activity_types = [activity_type] if activity_type else None
    
    feed = await collab_service.get_activity_feed(
        db=db,
        tenant_id=tenant.id,
        activity_types=activity_types,
        limit=limit,
        offset=skip
    )
    
    return feed


@router.get("/my")
async def get_my_activities(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> Dict[str, Any]:
    """
    Get activities for the current user.
    
    Shows:
    - Comments on your items
    - @mentions
    - Approval requests assigned to you
    - Other activities involving you
    """
    feed = await collab_service.get_activity_feed(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id,
        limit=limit,
        offset=skip
    )
    
    return feed


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get count of unread activities for current user.
    
    Used for notification badges.
    """
    count = await collab_service.get_unread_count(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    return {
        "unread_count": count
    }


@router.post("/mark-read")
async def mark_activities_as_read(
    request: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Mark activities as read.
    
    Only marks activities that belong to the current user.
    """
    marked = await collab_service.mark_as_read(
        db=db,
        activity_ids=request.activity_ids,
        user_id=user.id
    )
    
    return {
        "success": True,
        "marked_count": marked
    }
