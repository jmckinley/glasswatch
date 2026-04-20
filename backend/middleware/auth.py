"""
Authentication middleware for FastAPI.

Handles:
- JWT Bearer token authentication
- API key authentication via X-API-Key header
- Fallback to MVP header-based tenant authentication (X-Tenant-Id)
- Attaches user/tenant to request.state
"""
from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.core.config import settings
from backend.core.auth_workos import get_current_user_from_token, get_current_user_from_api_key
from backend.core.auth import DEMO_TENANT_ID, get_current_tenant as get_current_tenant_mvp


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that checks for:
    1. Bearer token (JWT) - when WorkOS is configured
    2. X-API-Key header - for programmatic access
    3. X-Tenant-Id header (MVP mode) - when WorkOS is not configured
    
    Attaches user and tenant to request.state for downstream use.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and attach authentication context."""
        # Skip auth for certain paths
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/api/v1/auth/demo-login",
            "/health",
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get database session
        db_generator = get_db()
        db: AsyncSession = await anext(db_generator)
        
        try:
            user = None
            tenant = None
            
            # Try JWT authentication
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                bearer_creds = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=token
                )
                user = await get_current_user_from_token(
                    credentials=bearer_creds,
                    db=db
                )
            
            # Try API key authentication if JWT didn't work
            if not user:
                api_key = request.headers.get("x-api-key")
                if api_key:
                    user = await get_current_user_from_api_key(
                        x_api_key=api_key,
                        db=db
                    )
            
            # If we have a user, get their tenant
            if user:
                result = await db.execute(
                    select(Tenant).where(Tenant.id == user.tenant_id)
                )
                tenant = result.scalar_one_or_none()
            
            # Fallback to MVP header-based auth if WorkOS is not configured
            elif not settings.WORKOS_API_KEY:
                tenant_id_header = request.headers.get("x-tenant-id")
                if tenant_id_header:
                    try:
                        tenant_uuid = UUID(tenant_id_header)
                        result = await db.execute(
                            select(Tenant).where(Tenant.id == tenant_uuid)
                        )
                        tenant = result.scalar_one_or_none()
                    except ValueError:
                        pass
                
                # Use demo tenant if nothing specified
                if not tenant:
                    result = await db.execute(
                        select(Tenant).where(Tenant.id == UUID(DEMO_TENANT_ID))
                    )
                    tenant = result.scalar_one_or_none()
            
            # When WorkOS is configured, require authentication
            # (except for endpoints that explicitly allow it)
            if settings.WORKOS_API_KEY and not user:
                # Some endpoints might want optional auth - they'll handle it
                pass
            
            # Attach to request state
            request.state.user = user
            request.state.tenant = tenant
            
            # Continue processing
            response = await call_next(request)
            return response
            
        finally:
            # Close database session
            await db.close()


async def get_optional_auth(request: Request) -> tuple[Optional[User], Optional[Tenant]]:
    """
    Dependency that provides optional authentication.
    
    Returns (user, tenant) tuple, where either can be None.
    Use this for endpoints that support both authenticated and MVP modes.
    """
    user = getattr(request.state, "user", None)
    tenant = getattr(request.state, "tenant", None)
    return user, tenant


async def get_current_user_optional(request: Request) -> Optional[User]:
    """Get current user from request state, if available."""
    return getattr(request.state, "user", None)


async def get_current_tenant_optional(request: Request) -> Optional[Tenant]:
    """Get current tenant from request state, if available."""
    return getattr(request.state, "tenant", None)


async def get_tenant_with_fallback(request: Request, db: AsyncSession) -> Tenant:
    """Get tenant with fallback to MVP header-based auth.
    
    This maintains backward compatibility with existing routes that expect a tenant.
    Priority:
    1. Authenticated user's tenant (from JWT or API key)
    2. X-Tenant-Id header (MVP mode)
    3. Demo tenant
    """
    # Try to get from request state (set by middleware)
    tenant = getattr(request.state, "tenant", None)
    if tenant:
        return tenant
    
    # Fallback to header-based lookup
    tenant_id_header = request.headers.get("x-tenant-id")
    if tenant_id_header:
        try:
            tenant_uuid = UUID(tenant_id_header)
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_uuid)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant
        except ValueError:
            pass
    
    # Ultimate fallback: demo tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(DEMO_TENANT_ID))
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
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
