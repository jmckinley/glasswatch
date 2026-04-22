"""
Notifications API endpoints.

Handles in-app notification retrieval and management.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.notification import Notification
from backend.models.user import User
from backend.api.deps import get_current_user


router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str
    tenant_id: str
    user_id: Optional[str]
    title: str
    message: str
    data: Optional[dict]
    priority: str
    channel: Optional[str]
    read: bool
    read_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    """Unread notification count response."""
    count: int


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List notifications for current user.
    
    Returns notifications targeted at the user or broadcast to all users in the tenant.
    Ordered by unread first, then by creation date descending.
    """
    # Build query for user-specific and broadcast notifications
    query = select(Notification).where(
        Notification.tenant_id == current_user.tenant_id,
        (
            (Notification.user_id == current_user.id) | 
            (Notification.user_id == None)  # Broadcast notifications
        )
    )
    
    # Filter by read status if requested
    if unread_only:
        query = query.where(Notification.read == False)
    
    # Order by unread first, then by creation date descending
    query = query.order_by(
        Notification.read.asc(),
        Notification.created_at.desc()
    )
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # Convert to response models
    return [
        NotificationResponse(
            id=str(n.id),
            tenant_id=str(n.tenant_id),
            user_id=str(n.user_id) if n.user_id else None,
            title=n.title,
            message=n.message,
            data=n.data,
            priority=n.priority,
            channel=n.channel,
            read=n.read,
            read_at=n.read_at.isoformat() if n.read_at else None,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as read.
    
    Only the target user can mark their notification as read.
    """
    # Find the notification
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == current_user.tenant_id,
            (
                (Notification.user_id == current_user.id) |
                (Notification.user_id == None)  # Broadcast notifications
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Mark as read
    notification.read = True
    notification.read_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(notification)
    
    return NotificationResponse(
        id=str(notification.id),
        tenant_id=str(notification.tenant_id),
        user_id=str(notification.user_id) if notification.user_id else None,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        priority=notification.priority,
        channel=notification.channel,
        read=notification.read,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
    )


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all notifications as read for the current user.
    
    Marks both user-specific and broadcast notifications.
    """
    # Update all unread notifications for this user
    await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == current_user.tenant_id,
            (
                (Notification.user_id == current_user.id) |
                (Notification.user_id == None)  # Broadcast notifications
            ),
            Notification.read == False
        )
        .values(
            read=True,
            read_at=datetime.now(timezone.utc)
        )
    )
    
    await db.commit()
    
    return {"message": "All notifications marked as read"}


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get count of unread notifications for the current user.
    
    Includes both user-specific and broadcast notifications.
    """
    # Count unread notifications
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == current_user.tenant_id,
            (
                (Notification.user_id == current_user.id) |
                (Notification.user_id == None)  # Broadcast notifications
            ),
            Notification.read == False
        )
    )
    count = result.scalar()
    
    return UnreadCountResponse(count=count or 0)
