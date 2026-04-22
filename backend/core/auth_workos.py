"""
WorkOS authentication integration for enterprise SSO.

Handles:
- SSO authentication flow
- User provisioning
- Session management
- API key authentication
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
from uuid import UUID
import secrets
import hashlib

from fastapi import Depends, HTTPException, Header, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from workos import WorkOS
    from workos.types import User as WorkOSUser
    from workos.types import Organization as WorkOSOrganization
    HAS_WORKOS = True
except (ImportError, AttributeError):
    # WorkOS SDK v4+ changed API; graceful fallback when not configured
    WorkOS = None
    WorkOSUser = None
    WorkOSOrganization = None
    HAS_WORKOS = False

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.user import User, UserRole
from backend.models.audit_log import AuditLog
from backend.core.config import settings


# Initialize WorkOS client
workos_client = None
if HAS_WORKOS and settings.WORKOS_API_KEY and settings.WORKOS_CLIENT_ID:
    workos_client = WorkOS(
        api_key=settings.WORKOS_API_KEY,
        client_id=settings.WORKOS_CLIENT_ID,
    )

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


async def create_access_token(user_id: str, tenant_id: str) -> str:
    """Create JWT access token for authenticated user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract user from JWT token."""
    if not credentials:
        return None
        
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        
        if not user_id or not tenant_id:
            return None
            
        # Get user from database
        result = await db.execute(
            select(User)
            .where(User.id == UUID(user_id))
            .where(User.tenant_id == UUID(tenant_id))
            .where(User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        # Update last login
        if user:
            user.last_login = datetime.now(timezone.utc)
            await db.commit()
            
        return user
        
    except JWTError:
        return None


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract user from API key."""
    if not x_api_key:
        return None
        
    # Hash the API key
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    # Find user with this API key
    result = await db.execute(
        select(User)
        .where(User.api_key_hash == key_hash)
        .where(User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update last used timestamp
        user.api_key_last_used = datetime.now(timezone.utc)
        await db.commit()
        
    return user


async def get_current_user(
    request: Request,
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from either JWT or API key.
    
    Priority:
    1. JWT token (for web users)
    2. API key (for programmatic access)
    """
    user = token_user or api_key_user
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    # Log the access
    await AuditLog.log_action(
        db_session=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="api.access",
        details={
            "path": str(request.url.path),
            "method": request.method,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Get tenant for the current user."""
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


def require_role(required_role: UserRole):
    """Dependency to require a specific role or higher."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        # Define role hierarchy
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.ENGINEER: 1,
            UserRole.APPROVER: 1,  # Same level as engineer, different permissions
            UserRole.ADMIN: 2,
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {required_role} role or higher"
            )
        
        return user
    
    return role_checker


def require_permission(permission: str):
    """Dependency to require a specific permission."""
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission}"
            )
        
        return user
    
    return permission_checker


# WorkOS SSO functions
async def create_sso_authorization_url(
    organization: str,
    redirect_uri: str,
    state: Optional[str] = None,
) -> str:
    """Create WorkOS SSO authorization URL."""
    if not workos_client:
        raise HTTPException(
            status_code=501,
            detail="WorkOS not configured"
        )
    
    authorization_url = workos_client.sso.get_authorization_url(
        organization=organization,
        redirect_uri=redirect_uri,
        state=state or secrets.token_urlsafe(32),
    )
    
    return authorization_url


async def handle_sso_callback(
    code: str,
    db: AsyncSession,
) -> Tuple[User, str]:
    """
    Handle WorkOS SSO callback.
    
    Returns user and access token.
    """
    if not workos_client:
        raise HTTPException(
            status_code=501,
            detail="WorkOS not configured"
        )
    
    # Exchange code for profile
    profile = workos_client.sso.get_profile_and_token(code)
    
    # Get or create tenant based on organization
    org_id = profile.organization_id
    org = workos_client.organizations.get_organization(org_id)
    
    # Find tenant by WorkOS org ID (stored in settings)
    result = await db.execute(
        select(Tenant).where(
            Tenant.settings["workos_org_id"].astext == org_id
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # Create new tenant for this organization
        tenant = Tenant(
            name=org.name,
            email=org.domains[0] if org.domains else f"{org.name}@patchguide.ai",
            region="us-east-1",
            tier="trial",
            is_active=True,
            encryption_key_id=f"kms-key-{org_id}",
            settings={
                "workos_org_id": org_id,
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
    
    # Get or create user
    result = await db.execute(
        select(User).where(
            User.workos_user_id == profile.id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            tenant_id=tenant.id,
            email=profile.email,
            name=f"{profile.first_name} {profile.last_name}".strip() or profile.email,
            workos_user_id=profile.id,
            is_active=True,
            role=UserRole.VIEWER,  # Default role, admin can upgrade
            permissions={},
            preferences={},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Log user creation
        await AuditLog.log_action(
            db_session=db,
            tenant_id=tenant.id,
            user_id=user.id,
            action="user.created",
            resource_type="user",
            resource_id=str(user.id),
            details={"source": "workos_sso"},
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    # Create access token
    access_token = await create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
    )
    
    # Log successful login
    await AuditLog.log_action(
        db_session=db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="user.login",
        details={"method": "workos_sso"},
    )
    
    return user, access_token


async def generate_api_key(
    user: User,
    db: AsyncSession,
) -> str:
    """Generate a new API key for a user."""
    # Generate secure random key
    api_key = secrets.token_urlsafe(32)
    
    # Hash it for storage
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Update user
    user.api_key_hash = key_hash
    user.api_key_last_used = None
    await db.commit()
    
    # Log API key generation
    await AuditLog.log_action(
        db_session=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="api_key.generated",
        resource_type="user",
        resource_id=str(user.id),
    )
    
    return api_key