"""
Authentication API endpoints.

Handles:
- SSO login flow
- User profile management
- API key generation
- Logout
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from backend.db.session import get_db
from backend.models.user import User, UserRole
from backend.models.audit_log import AuditLog
from backend.core.auth_workos import (
    get_current_user,
    create_sso_authorization_url,
    handle_sso_callback,
    generate_api_key,
    create_access_token,
)
from backend.core.config import settings


router = APIRouter()


# Pydantic models for API
class LoginResponse(BaseModel):
    authorization_url: str


class CallbackResponse(BaseModel):
    access_token: str
    user: dict
    redirect_to: str = "/dashboard"


class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    avatar_url: Optional[str] = None
    tenant_id: str
    tenant_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    preferences: dict


class UpdatePreferences(BaseModel):
    preferences: dict


class APIKeyResponse(BaseModel):
    api_key: str
    message: str = "Store this key securely. It won't be shown again."


@router.post("/login", response_model=LoginResponse)
async def initiate_login(
    organization: Optional[str] = Query(None, description="Organization domain or ID"),
    redirect_uri: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Initiate SSO login flow.
    
    If WorkOS is not configured, returns a demo login URL.
    """
    if not settings.WORKOS_API_KEY:
        # Demo mode - create a demo token
        return LoginResponse(
            authorization_url="/api/v1/auth/demo-login"
        )
    
    if not organization:
        raise HTTPException(
            status_code=400,
            detail="Organization is required for SSO"
        )
    
    # Default redirect URI
    if not redirect_uri:
        redirect_uri = f"{request.base_url}api/v1/auth/callback"
    
    authorization_url = await create_sso_authorization_url(
        organization=organization,
        redirect_uri=redirect_uri,
    )
    
    return LoginResponse(authorization_url=authorization_url)


@router.get("/callback", response_model=CallbackResponse)
async def handle_callback(
    code: str = Query(..., description="Authorization code from WorkOS"),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle SSO callback from WorkOS."""
    try:
        user, access_token = await handle_sso_callback(code=code, db=db)
        
        # Get tenant name for response
        await db.refresh(user, ["tenant"])
        
        return CallbackResponse(
            access_token=access_token,
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "avatar_url": user.avatar_url,
            },
            redirect_to="/dashboard",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"SSO callback failed: {str(e)}"
        )


@router.get("/demo-login", response_model=CallbackResponse)
async def demo_login(
    db: AsyncSession = Depends(get_db),
):
    """
    Demo login for development/testing without WorkOS.
    
    Creates or retrieves a demo user.
    """
    from backend.models.tenant import Tenant
    from uuid import UUID
    from sqlalchemy import select
    
    # Get demo tenant
    demo_tenant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    result = await db.execute(
        select(Tenant).where(Tenant.id == demo_tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # Create demo tenant
        tenant = Tenant(
            id=demo_tenant_id,
            name="Demo Organization",
            email="demo@patchguide.ai",
            region="us-east-1",
            tier="trial",
            is_active=True,
            encryption_key_id="demo-key",
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
    
    # Get or create demo user
    result = await db.execute(
        select(User).where(
            User.email == "demo@patchguide.ai"
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            tenant_id=tenant.id,
            email="demo@patchguide.ai",
            name="Demo User",
            is_active=True,
            role=UserRole.ADMIN,  # Full access for demo
            permissions={},
            preferences={},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token = await create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
    )
    
    return CallbackResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
        redirect_to="/dashboard",
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's profile."""
    # Refresh to get tenant relationship
    await db.refresh(user, ["tenant"])
    
    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        tenant_id=str(user.tenant_id),
        tenant_name=user.tenant.name,
        created_at=user.created_at,
        last_login=user.last_login,
        preferences=user.preferences,
    )


@router.patch("/me/preferences", response_model=UserProfile)
async def update_preferences(
    update: UpdatePreferences,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences."""
    # Merge new preferences with existing
    user.preferences = {**user.preferences, **update.preferences}
    await db.commit()
    await db.refresh(user, ["tenant"])
    
    # Log the update
    await AuditLog.log_action(
        db_session=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.preferences_updated",
        resource_type="user",
        resource_id=str(user.id),
    )
    
    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        tenant_id=str(user.tenant_id),
        tenant_name=user.tenant.name,
        created_at=user.created_at,
        last_login=user.last_login,
        preferences=user.preferences,
    )


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_new_api_key(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new API key for programmatic access.
    
    Note: This invalidates any existing API key.
    """
    api_key = await generate_api_key(user, db)
    
    return APIKeyResponse(api_key=api_key)


@router.post("/logout")
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout user.
    
    For JWT auth, the client should discard the token.
    This endpoint logs the logout action.
    """
    # Log the logout
    await AuditLog.log_action(
        db_session=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.logout",
    )
    
    # Clear any cookies if used
    response.delete_cookie("access_token")
    
    return {"message": "Logged out successfully"}