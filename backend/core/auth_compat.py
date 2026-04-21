"""
Backward-compatible authentication dependencies.

Provides a smooth transition from MVP header-based auth to full WorkOS auth.
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.core.auth import DEMO_TENANT_ID
from backend.core.auth_workos import get_current_user_from_token, get_current_user_from_api_key
from backend.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Get current authenticated user (compat layer)."""
    user: Optional[User] = None

    if credentials:
        user = await get_current_user_from_token(credentials=credentials, db=db)

    if not user:
        api_key = request.headers.get("x-api-key")
        if api_key:
            user = await get_current_user_from_api_key(x_api_key=api_key, db=db)

    if not user:
        # Fallback: create/return demo user in MVP mode
        if not settings.WORKOS_API_KEY:
            result = await db.execute(
                select(User).where(User.email == "demo@patchguide.ai")
            )
            user = result.scalar_one_or_none()
            if not user:
                from backend.models.user import UserRole
                user = User(
                    email="demo@patchguide.ai",
                    name="Demo User",
                    tenant_id=UUID(DEMO_TENANT_ID),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            return user
        raise HTTPException(status_code=401, detail="Authentication required")

    return user


async def get_current_tenant_compat(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None, description="Tenant ID header for MVP mode"),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Tenant:
    """
    Get current tenant with backward compatibility.
    
    Priority:
    1. Authenticated user's tenant (from JWT or API key)
    2. X-Tenant-Id header (MVP mode)
    3. Demo tenant (for development)
    
    This allows existing routes to work with both MVP and production auth.
    """
    user: Optional[User] = None
    
    # Try JWT authentication
    if credentials:
        user = await get_current_user_from_token(credentials=credentials, db=db)
    
    # Try API key authentication
    if not user:
        api_key = request.headers.get("x-api-key")
        if api_key:
            user = await get_current_user_from_api_key(x_api_key=api_key, db=db)
    
    # If we have an authenticated user, use their tenant
    if user:
        result = await db.execute(
            select(Tenant).where(Tenant.id == user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=403,
                detail="Tenant is inactive"
            )
        
        return tenant
    
    # Fallback to MVP header-based auth (when WorkOS is not configured)
    if not settings.WORKOS_API_KEY:
        tenant_id = x_tenant_id or DEMO_TENANT_ID
        
        try:
            tenant_uuid = UUID(tenant_id)
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_uuid)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                # Create demo tenant if it doesn't exist
                if tenant_id == DEMO_TENANT_ID:
                    tenant = Tenant(
                        id=UUID(DEMO_TENANT_ID),
                        name="demo-tenant",
                        email="demo@patchguide.ai",
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
            
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid tenant ID format"
            )
    
    # If WorkOS is configured but user is not authenticated
    raise HTTPException(
        status_code=401,
        detail="Authentication required"
    )
