"""
Authentication and authorization utilities.

For MVP, we'll use a simple tenant-based auth.
Production will integrate with WorkOS for SSO/SCIM.
"""
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.tenant import Tenant


# For MVP - hardcoded demo tenant
DEMO_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
DEMO_TENANT_NAME = "Demo Company"


async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None),
) -> Tenant:
    """
    Get the current tenant from the request.
    
    For MVP, we'll use a header-based tenant ID.
    In production, this will use JWT tokens with WorkOS.
    """
    # For demo/MVP, use the demo tenant
    if not x_tenant_id:
        # Check if demo tenant exists
        result = await db.execute(
            select(Tenant).where(Tenant.id == DEMO_TENANT_ID)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            # Create demo tenant
            tenant = Tenant(
                id=DEMO_TENANT_ID,
                name=DEMO_TENANT_NAME,
                slug="demo",
                region="us-east-1",
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
        
        return tenant
    
    # Parse tenant ID
    try:
        tenant_id = UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")
    
    return tenant