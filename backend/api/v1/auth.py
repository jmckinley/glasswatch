"""
Authentication API endpoints.

Handles:
- SSO login flow
- User profile management
- API key generation
- Logout
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth_workos import (
    create_access_token,
    create_github_auth_url,
    create_google_auth_url,
    create_sso_authorization_url,
    generate_api_key,
    get_current_user,
    handle_github_callback,
    handle_google_callback,
    handle_sso_callback,
)
from backend.core.config import settings
from backend.db.session import get_db
from backend.models.audit_log import AuditLog
from backend.services.audit_service import AuditService
from backend.models.user import User, UserRole
from backend.services.rate_limiter import get_rate_limiter


router = APIRouter()


async def _check_auth_rate_limit(request: Request, action: str = "auth") -> None:
    """
    Enforce per-IP rate limit on authentication endpoints.
    Allows 10 attempts per 5-minute window; rejects with 429 when exceeded.
    Falls back to allow-all when Redis is unavailable.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"ip:{client_ip}:{action}"
    limiter = get_rate_limiter()
    allowed, remaining = await limiter.check_rate_limit(key, limit=10, window_seconds=300)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "300"},
        )


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


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=200)


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


@router.post("/register", response_model=CallbackResponse)
async def register_with_email(
    request: Request,
    body: EmailRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth_rate_limit(request, action="register")
    """
    Register a new user with email/password.
    Creates a new Tenant and admin User.
    """
    from passlib.context import CryptContext
    from backend.models.tenant import Tenant
    from sqlalchemy import select

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create tenant
    import uuid
    tenant = Tenant(
        name=body.company_name,
        email=body.email,
        region="us-east-1",
        tier="trial",
        is_active=True,
        encryption_key_id=f"key-{uuid.uuid4().hex[:8]}",
        settings={},
    )
    db.add(tenant)
    await db.flush()  # Get tenant.id

    # Create user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        name=body.name,
        is_active=True,
        role=UserRole.ADMIN,
        password_hash=pwd_context.hash(body.password),
        permissions={},
        preferences={},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

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
        redirect_to="/onboarding",
    )


@router.post("/email-login", response_model=CallbackResponse)
async def login_with_email(
    request: Request,
    body: EmailLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth_rate_limit(request, action="email-login")
    """
    Login with email/password credentials.
    """
    from passlib.context import CryptContext
    from sqlalchemy import select

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not pwd_context.verify(body.password, user.password_hash):
        # Log failed login — we have a tenant_id from the found user
        try:
            await AuditService.log(
                db=db,
                tenant_id=user.tenant_id,
                user_id=user.id,
                action="user.login_failed",
                resource_type="user",
                resource_id=str(user.id),
                resource_name=user.email,
                details={"reason": "invalid_password"},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False,
                error_message="Invalid password",
            )
            await db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    user.last_login = datetime.now(timezone.utc)
    # Log successful login
    await AuditService.log(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    access_token = await create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
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
@router.post("/demo-login", response_model=CallbackResponse)
async def demo_login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth_rate_limit(request, action="demo-login")
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
    user.last_login = datetime.now(timezone.utc)
    await AuditService.log(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.email,
        details={"provider": "demo"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
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


@router.get("/providers")
async def get_auth_providers():
    """
    List available authentication providers based on configuration.
    """
    providers = {
        "demo": True,  # Always available for development
    }
    
    if settings.WORKOS_API_KEY and settings.WORKOS_CLIENT_ID:
        providers["workos"] = True
    
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        providers["google"] = True
    
    if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
        providers["github"] = True
    
    return {"providers": providers}


@router.get("/google", response_model=LoginResponse)
async def initiate_google_login(
    redirect_uri: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Initiate Google OAuth flow.
    """
    if not redirect_uri:
        redirect_uri = f"{request.base_url}api/v1/auth/google/callback"
    
    authorization_url = await create_google_auth_url(redirect_uri=redirect_uri)
    
    return LoginResponse(authorization_url=authorization_url)


@router.get("/google/callback", response_model=CallbackResponse)
async def handle_google_callback_endpoint(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    """
    redirect_uri = f"{request.base_url}api/v1/auth/google/callback"
    
    try:
        user, access_token = await handle_google_callback(
            code=code,
            redirect_uri=redirect_uri,
            db=db,
        )
        
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
            detail=f"Google OAuth callback failed: {str(e)}"
        )


@router.get("/github", response_model=LoginResponse)
async def initiate_github_login(
    redirect_uri: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Initiate GitHub OAuth flow.
    """
    if not redirect_uri:
        redirect_uri = f"{request.base_url}api/v1/auth/github/callback"
    
    authorization_url = await create_github_auth_url(redirect_uri=redirect_uri)
    
    return LoginResponse(authorization_url=authorization_url)


@router.get("/github/callback", response_model=CallbackResponse)
async def handle_github_callback_endpoint(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle GitHub OAuth callback.
    """
    redirect_uri = f"{request.base_url}api/v1/auth/github/callback"
    
    try:
        user, access_token = await handle_github_callback(
            code=code,
            redirect_uri=redirect_uri,
            db=db,
        )
        
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
            detail=f"GitHub OAuth callback failed: {str(e)}"
        )