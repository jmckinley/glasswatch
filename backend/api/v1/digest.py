"""
Digest API endpoints.

Provides on-demand triggering of weekly digest emails for testing
and manual delivery.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.core.auth_workos import get_current_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/digest/send-weekly")
async def send_weekly_digest(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the weekly digest email for the current tenant.

    Useful for testing delivery and for manual sends outside the normal
    scheduled window.
    """
    try:
        from backend.services.digest_service import send_weekly_digest as _send

        result = await _send(tenant_id=tenant.id, db=db)

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to send digest"),
            )

        return {
            "success": True,
            "message": "Weekly digest sent successfully",
            "provider": result.get("provider"),
            "recipients": result.get("recipients", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Digest send error for tenant {tenant.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
