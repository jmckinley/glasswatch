"""
Settings API endpoints.

Handles tenant settings management with deep merge support.
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.core.auth_workos import get_current_user


router = APIRouter()


# Default settings schema
DEFAULT_SETTINGS = {
    "notifications": {
        "email_enabled": True,
        "slack_enabled": False,
        "slack_channel": None,
        "digest_frequency": "daily",
        "critical_alerts": True,
    },
    "security": {
        "auto_approve_low_risk": False,
        "require_2_approvers": True,
        "max_bundle_size": 50,
    },
    "display": {
        "timezone": "America/New_York",
        "date_format": "MM/DD/YYYY",
        "theme": "system",
    },
}


# Pydantic models
class SettingsResponse(BaseModel):
    settings: Dict[str, Any]
    tenant_id: str
    tenant_name: str


class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]


class SettingsUpdateResponse(BaseModel):
    success: bool
    message: str
    settings: Dict[str, Any]


class DefaultSettingsResponse(BaseModel):
    defaults: Dict[str, Any]


def deep_merge(base: dict, update: dict) -> dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        update: Dictionary with updates
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_merged_settings(tenant_settings: dict | None) -> dict:
    """
    Merge tenant settings with defaults.
    
    Args:
        tenant_settings: Tenant-specific settings (may be None or partial)
        
    Returns:
        Complete settings dictionary merged with defaults
    """
    if not tenant_settings:
        return DEFAULT_SETTINGS.copy()
    
    return deep_merge(DEFAULT_SETTINGS, tenant_settings)


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tenant settings merged with defaults.
    
    Returns:
        SettingsResponse with complete settings
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Merge with defaults
    merged_settings = get_merged_settings(tenant.settings)
    
    return SettingsResponse(
        settings=merged_settings,
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
    )


@router.patch("", response_model=SettingsUpdateResponse)
async def update_settings(
    settings_update: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update tenant settings with deep merge.
    
    Only provided fields are updated; others remain unchanged.
    
    Args:
        settings_update: Partial settings to update
        
    Returns:
        SettingsUpdateResponse with updated settings
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get current settings or empty dict
    current_settings = tenant.settings or {}
    
    # Deep merge the update into current settings
    updated_settings = deep_merge(current_settings, settings_update.settings)
    
    # Save to database
    tenant.settings = updated_settings
    
    await db.commit()
    await db.refresh(tenant)
    
    # Return merged with defaults for completeness
    final_settings = get_merged_settings(tenant.settings)
    
    return SettingsUpdateResponse(
        success=True,
        message="Settings updated successfully",
        settings=final_settings,
    )


@router.get("/defaults", response_model=DefaultSettingsResponse)
async def get_default_settings():
    """
    Get default settings schema.
    
    Useful for resetting or understanding available options.
    
    Returns:
        DefaultSettingsResponse with schema
    """
    return DefaultSettingsResponse(defaults=DEFAULT_SETTINGS)


@router.post("/reset", response_model=SettingsUpdateResponse)
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset settings to defaults.
    
    Returns:
        SettingsUpdateResponse with default settings
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Reset to empty dict (will use defaults on read)
    tenant.settings = {}
    
    await db.commit()
    
    return SettingsUpdateResponse(
        success=True,
        message="Settings reset to defaults",
        settings=DEFAULT_SETTINGS.copy(),
    )
