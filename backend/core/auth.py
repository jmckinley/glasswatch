"""
Authentication and authorization utilities.

For MVP: Simple header-based tenant identification.
For Production: WorkOS integration for enterprise SSO.
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.tenant import Tenant


# Demo tenant for MVP
DEMO_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
DEMO_TENANT_NAME = "demo-tenant"


async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, description="Tenant ID header"),
) -> Tenant:
    """
    Get the current tenant from the request.
    
    MVP: Use header-based tenant ID or default to demo tenant.
    Production: Extract from JWT token after WorkOS authentication.
    """
    # For MVP, always use demo tenant or header value
    tenant_id = x_tenant_id or DEMO_TENANT_ID
    
    # Try to get tenant from database
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(tenant_id))
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # Create demo tenant if it doesn't exist
        if tenant_id == DEMO_TENANT_ID:
            tenant = Tenant(
                id=UUID(DEMO_TENANT_ID),
                name=DEMO_TENANT_NAME,
                email="demo@glasswatch.io",
                region="us-east-1",
                tier="trial",
                is_active=True,
                encryption_key_id="demo-key-id",
                settings={
                    "features": {
                        "patch_weather": True,
                        "ai_assistant": True,
                        "webhooks": True,
                    }
                }
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
        else:
            raise HTTPException(
                status_code=404,
                detail="Tenant not found"
            )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tenant is inactive"
        )
    
    return tenant


# Future WorkOS integration placeholder
"""
from workos import WorkOS

workos = WorkOS(
    api_key=settings.WORKOS_API_KEY,
    client_id=settings.WORKOS_CLIENT_ID,
)

async def get_current_user_workos(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    # Verify JWT token with WorkOS
    # Extract organization_id from token
    # Map to tenant in our database
    pass
"""