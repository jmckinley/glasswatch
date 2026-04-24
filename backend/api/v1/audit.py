"""
Audit log API endpoints.

Provides read-only access to audit logs for compliance and security investigations.
Admin-only access.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.audit_log import AuditLog
from backend.models.user import User, UserRole
from backend.core.auth_workos import get_current_user


router = APIRouter()


# Pydantic models for responses
class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    skip: int
    limit: int


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin role required"
        )
    return user


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
    action: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="End date (inclusive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> AuditLogListResponse:
    """
    List audit logs with filtering.
    
    Admin only. Returns paginated list of audit log entries.
    """
    # Build base query for user's tenant
    query = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id)
    
    # Apply filters
    filters = []
    
    if action:
        filters.append(AuditLog.action == action)
    
    if user_id:
        filters.append(AuditLog.user_id == UUID(user_id))
    
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    
    if resource_id:
        filters.append(AuditLog.resource_id == resource_id)
    
    if start_date:
        filters.append(AuditLog.created_at >= start_date)

    if end_date:
        filters.append(AuditLog.created_at <= end_date)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.scalar(count_query)
    
    # Apply ordering, pagination
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute
    result = await db.execute(query)
    audit_logs = result.scalars().all()
    
    # Convert to response models
    items = [
        AuditLogResponse(
            id=str(log.id),
            tenant_id=str(log.tenant_id),
            user_id=str(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            timestamp=log.created_at,
        )
        for log in audit_logs
    ]
    
    return AuditLogListResponse(
        items=items,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/audit-logs/{audit_log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_log_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> AuditLogResponse:
    """
    Get a specific audit log entry by ID.
    
    Admin only.
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.id == audit_log_id)
        .where(AuditLog.tenant_id == user.tenant_id)
    )
    audit_log = result.scalar_one_or_none()
    
    if not audit_log:
        raise HTTPException(
            status_code=404,
            detail="Audit log entry not found"
        )
    
    return AuditLogResponse(
        id=str(audit_log.id),
        tenant_id=str(audit_log.tenant_id),
        user_id=str(audit_log.user_id) if audit_log.user_id else None,
        action=audit_log.action,
        resource_type=audit_log.resource_type,
        resource_id=audit_log.resource_id,
        details=audit_log.details,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        timestamp=audit_log.created_at,
    )
