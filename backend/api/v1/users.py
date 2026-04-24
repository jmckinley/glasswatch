"""
User management API endpoints.

Provides user CRUD and role management for tenant admins.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.user import User, UserRole
from backend.models.audit_log import AuditLog
from backend.core.auth_workos import get_current_user


router = APIRouter()


# Pydantic models for API
class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    name: str
    avatar_url: Optional[str]
    workos_user_id: Optional[str]
    is_active: bool
    role: UserRole
    permissions: Dict[str, Any]
    preferences: Dict[str, Any]
    api_key_last_used: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int
    limit: int


class UpdateUserRole(BaseModel):
    role: UserRole


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin role required"
        )
    return user


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> UserListResponse:
    """
    List users in the tenant.
    
    Admin only. Returns paginated list of users.
    """
    # Build base query for admin's tenant
    query = select(User).where(User.tenant_id == admin.tenant_id)
    
    # Apply filters
    filters = []
    
    if is_active is not None:
        filters.append(User.is_active == is_active)
    
    if role:
        filters.append(User.role == role)
    
    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        filters.append(search_filter)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.scalar(count_query)
    
    # Apply ordering, pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Convert to response models
    items = [
        UserResponse(
            id=str(u.id),
            tenant_id=str(u.tenant_id),
            email=u.email,
            name=u.name,
            avatar_url=u.avatar_url,
            workos_user_id=u.workos_user_id,
            is_active=u.is_active,
            role=u.role,
            permissions=u.permissions,
            preferences=u.preferences,
            api_key_last_used=u.api_key_last_used,
            created_at=u.created_at,
            updated_at=u.updated_at,
            last_login=u.last_login,
        )
        for u in users
    ]
    
    return UserListResponse(
        items=items,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """
    Get a specific user by ID.
    
    Admin only. User must be in the same tenant.
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        workos_user_id=user.workos_user_id,
        is_active=user.is_active,
        role=user.role,
        permissions=user.permissions,
        preferences=user.preferences,
        api_key_last_used=user.api_key_last_used,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    update: UpdateUserRole,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """
    Update a user's role.
    
    Admin only. Cannot change your own role.
    """
    # Prevent self-role-change
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role"
        )
    
    # Get user
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    old_role = user.role
    user.role = update.role
    await db.commit()
    await db.refresh(user)
    
    # Log the role change
    await AuditLog.log_action(
        db_session=db,
        tenant_id=admin.tenant_id,
        user_id=admin.id,
        action="user.role_updated",
        resource_type="user",
        resource_id=str(user.id),
        details={
            "old_role": old_role,
            "new_role": update.role,
            "target_user_email": user.email,
        }
    )
    await db.commit()
    
    return UserResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        workos_user_id=user.workos_user_id,
        is_active=user.is_active,
        role=user.role,
        permissions=user.permissions,
        preferences=user.preferences,
        api_key_last_used=user.api_key_last_used,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )


@router.delete("/users/{user_id}", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """
    Deactivate a user (soft delete).
    
    Admin only. Cannot deactivate yourself.
    """
    # Prevent self-deactivation
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself"
        )
    
    # Get user
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="User is already deactivated"
        )
    
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    
    # Log the deactivation
    await AuditLog.log_action(
        db_session=db,
        tenant_id=admin.tenant_id,
        user_id=admin.id,
        action="user.deactivated",
        resource_type="user",
        resource_id=str(user.id),
        details={
            "target_user_email": user.email,
        }
    )
    await db.commit()
    
    return UserResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        workos_user_id=user.workos_user_id,
        is_active=user.is_active,
        role=user.role,
        permissions=user.permissions,
        preferences=user.preferences,
        api_key_last_used=user.api_key_last_used,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )
