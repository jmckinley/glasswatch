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
from backend.core.auth_workos import get_current_user


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


class NotificationsListResponse(BaseModel):
    """Paginated notifications list response."""
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Unread notification count response."""
    count: int


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
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


def _base_query(current_user: User):
    """Base query for notifications visible to this user."""
    from sqlalchemy import or_
    return (
        select(Notification)
        .where(
            Notification.tenant_id == current_user.tenant_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.user_id == None,  # noqa: E711
            ),
        )
    )


@router.get("/notifications", response_model=NotificationsListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread: Optional[bool] = Query(None),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List notifications for current user.

    Returns notifications targeted at the user or broadcast to all users in the tenant.
    Ordered by unread first, then by creation date descending.
    Accepts ``unread=true`` (frontend-friendly) or legacy ``unread_only=true``.
    """
    base = _base_query(current_user)

    # Support both ?unread=true and legacy ?unread_only=true
    filter_unread = unread is True or unread_only

    # Count total & unread before pagination
    count_q = select(func.count(Notification.id)).where(
        Notification.tenant_id == current_user.tenant_id,
    )
    from sqlalchemy import or_
    count_q = count_q.where(
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id == None,  # noqa: E711
        )
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    unread_q = count_q.where(Notification.read == False)  # noqa: E712
    unread_result = await db.execute(unread_q)
    unread_count = unread_result.scalar() or 0

    # Apply unread filter on main query
    if filter_unread:
        base = base.where(Notification.read == False)  # noqa: E712

    # Order: unread first, then newest
    base = base.order_by(
        Notification.read.asc(),
        Notification.created_at.desc(),
    ).offset(skip).limit(limit)

    result = await db.execute(base)
    notifications = result.scalars().all()

    return NotificationsListResponse(
        items=[_to_response(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get count of unread notifications for the current user.

    Includes both user-specific and broadcast notifications.
    """
    from sqlalchemy import or_
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == current_user.tenant_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.user_id == None,  # noqa: E711
            ),
            Notification.read == False,  # noqa: E712
        )
    )
    count = result.scalar()
    return UnreadCountResponse(count=count or 0)


# ── Mark single notification read (POST + PATCH both supported) ───────────────

async def _mark_one_read(
    notification_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> NotificationResponse:
    from sqlalchemy import or_
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == current_user.tenant_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.user_id == None,  # noqa: E711
            ),
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read = True
    notification.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notification)
    return _to_response(notification)


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read_post(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read (POST)."""
    return await _mark_one_read(notification_id, current_user, db)


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read_patch(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read (PATCH — legacy alias)."""
    return await _mark_one_read(notification_id, current_user, db)


# ── Mark all read (POST /mark-all-read + legacy /read-all) ───────────────────

async def _mark_all_read(current_user: User, db: AsyncSession):
    from sqlalchemy import or_
    await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == current_user.tenant_id,
            or_(
                Notification.user_id == current_user.id,
                Notification.user_id == None,  # noqa: E711
            ),
            Notification.read == False,  # noqa: E712
        )
        .values(read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    return await _mark_all_read(current_user, db)


@router.post("/notifications/read-all")
async def mark_all_notifications_read_legacy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read (legacy endpoint alias)."""
    return await _mark_all_read(current_user, db)
