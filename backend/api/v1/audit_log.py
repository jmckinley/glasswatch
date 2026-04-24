"""
Audit Log API — /api/v1/audit-log

Read-only access to the full audit trail for compliance and security
investigations.  Admin-only.  Supports rich filtering and CSV export.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.user import User, UserRole
from backend.core.auth_workos import get_current_user
from backend.services.audit_service import AuditService

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AuditUserSummary(BaseModel):
    id: str
    email: str
    name: str


class AuditLogEntry(BaseModel):
    id: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    user: Optional[AuditUserSummary]

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_audit_log(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
    action: Optional[str] = Query(None, description="Filter by action e.g. bundle.approved"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[str] = Query(None, description="Filter by user UUID"),
    since: Optional[datetime] = Query(None, description="Start of date range (ISO 8601)"),
    until: Optional[datetime] = Query(None, description="End of date range (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AuditLogListResponse:
    """
    List audit log entries with optional filters.

    Returns paginated results newest-first.  Admin only.
    """
    logs, total = await AuditService.get_logs(
        db=db,
        tenant_id=user.tenant_id,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )

    entries = [_to_entry(log) for log in logs]
    return AuditLogListResponse(logs=entries, total=total, limit=limit, offset=offset)


@router.get("/audit-log/export")
async def export_audit_log_csv(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(5000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
) -> StreamingResponse:
    """
    Export audit log as CSV download.  Same filters as GET /audit-log.
    Useful for compliance submissions and SIEM ingestion.
    """
    logs, _ = await AuditService.get_logs(
        db=db,
        tenant_id=user.tenant_id,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "timestamp", "user_email", "user_name",
        "action", "resource_type", "resource_id", "resource_name",
        "success", "error_message", "ip_address", "details",
    ])
    for log in logs:
        writer.writerow([
            str(log.id),
            log.created_at.isoformat() if log.created_at else "",
            log.user.email if log.user else "",
            log.user.name if log.user else "System",
            log.action,
            log.resource_type or "",
            log.resource_id or "",
            log.resource_name or "",
            "true" if log.success else "false",
            log.error_message or "",
            log.ip_address or "",
            str(log.details) if log.details else "{}",
        ])

    buf.seek(0)
    filename = f"glasswatch-audit-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _to_entry(log) -> AuditLogEntry:
    user_summary = None
    if log.user:
        user_summary = AuditUserSummary(
            id=str(log.user.id),
            email=log.user.email,
            name=log.user.name,
        )
    return AuditLogEntry(
        id=str(log.id),
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_name=log.resource_name,
        details=log.details or {},
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        success=log.success,
        error_message=log.error_message,
        created_at=log.created_at,
        user=user_summary,
    )
