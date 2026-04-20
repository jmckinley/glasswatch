"""
Role-Based Access Control (RBAC) middleware and dependencies.

Provides FastAPI dependencies for checking roles and permissions.
"""
from typing import Callable

from fastapi import Depends, HTTPException, Request

from backend.models.user import User, UserRole
from backend.core.auth_workos import get_current_user


def require_role(role: UserRole) -> Callable:
    """
    FastAPI dependency factory to require a specific role or higher.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    
    Args:
        role: The minimum required role
    
    Returns:
        Dependency function that validates user role
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        # Define role hierarchy
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.ENGINEER: 1,
            UserRole.APPROVER: 1,  # Same level as engineer, different permissions
            UserRole.ADMIN: 2,
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {role.value} role or higher. Your role: {user.role.value}"
            )
        
        return user
    
    return role_checker


def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory to require a specific permission.
    
    Usage:
        @router.post("/bundles")
        async def create_bundle(
            user: User = Depends(require_permission("bundles:write"))
        ):
            ...
    
    Args:
        permission: The required permission string (e.g., "bundles:write")
    
    Returns:
        Dependency function that validates user permission
    """
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission}"
            )
        
        return user
    
    return permission_checker


def require_any_role(*roles: UserRole) -> Callable:
    """
    FastAPI dependency factory to require any of the specified roles.
    
    Usage:
        @router.post("/approve")
        async def approve_bundle(
            user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.APPROVER))
        ):
            ...
    
    Args:
        *roles: One or more acceptable roles
    
    Returns:
        Dependency function that validates user has one of the roles
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            roles_str = ", ".join(r.value for r in roles)
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of these roles: {roles_str}. Your role: {user.role.value}"
            )
        
        return user
    
    return role_checker


def require_any_permission(*permissions: str) -> Callable:
    """
    FastAPI dependency factory to require any of the specified permissions.
    
    Usage:
        @router.get("/resource")
        async def get_resource(
            user: User = Depends(require_any_permission("read:admin", "read:user"))
        ):
            ...
    
    Args:
        *permissions: One or more acceptable permissions
    
    Returns:
        Dependency function that validates user has at least one permission
    """
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        has_any = any(user.has_permission(perm) for perm in permissions)
        if not has_any:
            perms_str = ", ".join(permissions)
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permissions. Need one of: {perms_str}"
            )
        
        return user
    
    return permission_checker


def require_same_tenant(resource_tenant_id: str) -> Callable:
    """
    Dependency factory to ensure user is accessing resources in their own tenant.
    
    Usage:
        @router.get("/bundles/{bundle_id}")
        async def get_bundle(
            bundle_id: UUID,
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            bundle = await get_bundle_by_id(bundle_id, db)
            # Validate tenant
            validate = require_same_tenant(str(bundle.tenant_id))
            await validate(user)
            ...
    """
    async def tenant_checker(user: User = Depends(get_current_user)) -> User:
        if str(user.tenant_id) != resource_tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: resource belongs to a different tenant"
            )
        return user
    
    return tenant_checker
