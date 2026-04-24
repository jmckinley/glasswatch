"""
Audit service for creating and querying audit log entries.

This is the primary interface for recording security-relevant actions in
Glasswatch.  All route handlers should call AuditService.log() instead of
directly constructing AuditLog objects so that behaviour is consistent and
easy to test.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.audit_log import AuditLog


class AuditService:
    """Static-method service for audit log operations."""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @staticmethod
    async def log(
        db: AsyncSession,
        tenant_id,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        user_id=None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry and flush it to the session.

        Parameters
        ----------
        db            : AsyncSession — active DB session (will be flushed, not committed)
        tenant_id     : UUID or str — owning tenant
        action        : dot-separated action token e.g. "bundle.approved"
        resource_type : noun e.g. "bundle", "user", "maintenance_window"
        resource_id   : str ID of the affected object (optional)
        resource_name : human-readable label (optional)
        user_id       : UUID of acting user; None for system-triggered actions
        details       : extra structured context dict
        ip_address    : client IP (pass request.client.host)
        user_agent    : client UA (pass request.headers.get("user-agent"))
        success       : True when the action succeeded (default)
        error_message : set on failure to record what went wrong
        """
        # Normalise to UUID objects when string values are passed in
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )
        db.add(entry)
        await db.flush()
        return entry

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        tenant_id,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id=None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """
        Query audit logs with filters.

        Returns
        -------
        (logs, total_count) — logs is the paginated slice; total_count is the
        unfiltered count for pagination UI.
        """
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        filters = [AuditLog.tenant_id == tenant_id]

        if action:
            filters.append(AuditLog.action == action)
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if since:
            filters.append(AuditLog.created_at >= since)
        if until:
            filters.append(AuditLog.created_at <= until)

        where_clause = and_(*filters)

        # Total count (for pagination)
        count_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(where_clause)
        )
        total = count_result.scalar() or 0

        # Paginated rows with user relationship eager-loaded
        rows_result = await db.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(where_clause)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        logs = list(rows_result.scalars().all())

        return logs, total
