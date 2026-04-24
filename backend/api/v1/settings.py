"""
Settings API endpoints.

Handles tenant settings management with deep merge support.
Includes sensitive field masking and integration test-connection.
"""
import os
from typing import Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.core.auth_workos import get_current_user


router = APIRouter()

# Sensitive keys that should be masked in GET responses
SENSITIVE_KEYS = {
    "vulncheck_api_key",
    "snapper_webhook_secret",
    "jira_api_token",
    "servicenow_password",
    "anthropic_api_key",
    "email_smtp_password",
    "slack_webhook_url",
    "teams_webhook_url",
}

# Default settings schema
DEFAULT_SETTINGS = {
    "notifications": {
        "email_enabled": False,
        "email_smtp_host": None,
        "email_smtp_port": 587,
        "email_smtp_user": None,
        "email_smtp_password": None,
        "email_from": None,
        "slack_enabled": False,
        "slack_webhook_url": None,
        "slack_channel": "#security-alerts",
        "teams_enabled": False,
        "teams_webhook_url": None,
        "digest_frequency": "daily",
        "critical_alerts": True,
    },
    "security": {
        "auto_approve_low_risk": False,
        "require_2_approvers": True,
        "max_bundle_size": 50,
        "min_patch_age_days": 3,
        "patch_weather_threshold": "YELLOW",
    },
    "integrations": {
        "vulncheck_api_key": None,
        "vulncheck_api_key_configured": False,
        "snapper_webhook_secret": None,
        "snapper_webhook_secret_configured": False,
        "jira_url": None,
        "jira_email": None,
        "jira_api_token": None,
        "jira_api_token_configured": False,
        "jira_project_key": None,
        "servicenow_url": None,
        "servicenow_username": None,
        "servicenow_password": None,
        "servicenow_password_configured": False,
    },
    "ai": {
        "anthropic_api_key": None,
        "anthropic_api_key_configured": False,
        "ai_assistant_enabled": True,
        "nlp_rules_enabled": True,
    },
    "display": {
        "timezone": "America/New_York",
        "date_format": "MM/DD/YYYY",
        "theme": "dark",
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


class TestConnectionRequest(BaseModel):
    integration: str
    config: Dict[str, str]


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


def mask_sensitive(settings: dict) -> dict:
    """Return settings with sensitive values masked."""
    result = {}
    for key, value in settings.items():
        if isinstance(value, dict):
            result[key] = mask_sensitive(value)
        elif key in SENSITIVE_KEYS and value and isinstance(value, str):
            # Show last 4 chars only
            tail = value[-4:] if len(value) >= 4 else value
            result[key] = f"***...{tail}"
        else:
            result[key] = value
    return result


def mark_configured(settings: dict) -> dict:
    """
    When a sensitive field is set to a non-empty value, also mark
    its _configured sibling as True.
    """
    result = {}
    for key, value in settings.items():
        if isinstance(value, dict):
            result[key] = mark_configured(value)
        else:
            result[key] = value
            # If this is a sensitive key with a real value, set _configured
            if key in SENSITIVE_KEYS and value and isinstance(value, str):
                configured_key = f"{key}_configured"
                result[configured_key] = True
    return result


def deep_merge(base: dict, update: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_merged_settings(tenant_settings: dict | None) -> dict:
    """Merge tenant settings with defaults."""
    if not tenant_settings:
        return DEFAULT_SETTINGS.copy()
    return deep_merge(DEFAULT_SETTINGS, tenant_settings)


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tenant settings merged with defaults. Sensitive values are masked."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    merged = get_merged_settings(tenant.settings)
    masked = mask_sensitive(merged)

    return SettingsResponse(
        settings=masked,
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
    )


@router.patch("", response_model=SettingsUpdateResponse)
async def update_settings(
    settings_update: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant settings with deep merge. Marks sensitive fields as configured."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    current_settings = tenant.settings or {}
    # First mark configured flags in the incoming update
    update_with_flags = mark_configured(settings_update.settings)
    # Then deep-merge into existing
    updated_settings = deep_merge(current_settings, update_with_flags)
    tenant.settings = updated_settings

    await db.commit()
    await db.refresh(tenant)

    final = get_merged_settings(tenant.settings)
    masked = mask_sensitive(final)

    return SettingsUpdateResponse(
        success=True,
        message="Settings updated successfully",
        settings=masked,
    )


@router.get("/defaults", response_model=DefaultSettingsResponse)
async def get_default_settings():
    """Get default settings schema."""
    return DefaultSettingsResponse(defaults=DEFAULT_SETTINGS)


@router.post("/reset", response_model=SettingsUpdateResponse)
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset settings to defaults."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.settings = {}
    await db.commit()

    return SettingsUpdateResponse(
        success=True,
        message="Settings reset to defaults",
        settings=DEFAULT_SETTINGS.copy(),
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test an integration connection.
    
    Supported integrations: slack, teams, jira, servicenow, email
    """
    integration = request.integration.lower()
    config = request.config

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if integration == "slack":
                webhook_url = config.get("webhook_url", "")
                if not webhook_url:
                    return TestConnectionResponse(success=False, message="webhook_url is required")
                resp = await client.post(
                    webhook_url,
                    json={"text": "✅ Glasswatch test connection — this integration is working!"},
                )
                if resp.status_code == 200:
                    return TestConnectionResponse(success=True, message="Slack message sent successfully")
                else:
                    return TestConnectionResponse(success=False, message=f"Slack returned HTTP {resp.status_code}: {resp.text[:200]}")

            elif integration == "teams":
                webhook_url = config.get("webhook_url", "")
                if not webhook_url:
                    return TestConnectionResponse(success=False, message="webhook_url is required")
                resp = await client.post(
                    webhook_url,
                    json={
                        "@type": "MessageCard",
                        "@context": "http://schema.org/extensions",
                        "summary": "Glasswatch test",
                        "text": "✅ Glasswatch test connection — this integration is working!",
                    },
                )
                if resp.status_code in (200, 202):
                    return TestConnectionResponse(success=True, message="Teams message sent successfully")
                else:
                    return TestConnectionResponse(success=False, message=f"Teams returned HTTP {resp.status_code}")

            elif integration == "jira":
                jira_url = config.get("jira_url", "").rstrip("/")
                email = config.get("jira_email", "")
                token = config.get("jira_api_token", "")
                if not all([jira_url, email, token]):
                    return TestConnectionResponse(success=False, message="jira_url, jira_email, and jira_api_token are required")
                resp = await client.get(
                    f"{jira_url}/rest/api/3/myself",
                    auth=(email, token),
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    display = data.get("displayName", "user")
                    return TestConnectionResponse(success=True, message=f"Connected to Jira as {display}")
                else:
                    return TestConnectionResponse(success=False, message=f"Jira returned HTTP {resp.status_code}: invalid credentials or URL")

            elif integration == "servicenow":
                snow_url = config.get("servicenow_url", "").rstrip("/")
                username = config.get("servicenow_username", "")
                password = config.get("servicenow_password", "")
                if not all([snow_url, username, password]):
                    return TestConnectionResponse(success=False, message="servicenow_url, servicenow_username, and servicenow_password are required")
                resp = await client.get(
                    f"{snow_url}/api/now/table/sys_user?sysparm_limit=1",
                    auth=(username, password),
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    return TestConnectionResponse(success=True, message="Connected to ServiceNow successfully")
                else:
                    return TestConnectionResponse(success=False, message=f"ServiceNow returned HTTP {resp.status_code}")

            elif integration == "email":
                # Basic SMTP connectivity test (just check we can reach the host/port)
                smtp_host = config.get("smtp_host", "")
                smtp_port = int(config.get("smtp_port", "587"))
                if not smtp_host:
                    return TestConnectionResponse(success=False, message="smtp_host is required")
                import asyncio, socket
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(
                        None,
                        lambda: socket.create_connection((smtp_host, smtp_port), timeout=5)
                    )
                    return TestConnectionResponse(success=True, message=f"Reachable: {smtp_host}:{smtp_port}")
                except (OSError, TimeoutError) as e:
                    return TestConnectionResponse(success=False, message=f"Cannot reach {smtp_host}:{smtp_port} — {e}")

            elif integration == "tenable":
                access_key = config.get("access_key", "")
                secret_key = config.get("secret_key", "")
                if not access_key or not secret_key:
                    return TestConnectionResponse(success=False, message="access_key and secret_key are required")
                resp = await client.get(
                    "https://cloud.tenable.com/api/v1/health",
                    headers={"X-ApiKeys": f"accessKey={access_key};secretKey={secret_key}"},
                )
                if resp.status_code == 200:
                    return TestConnectionResponse(success=True, message="Tenable connection healthy")
                elif resp.status_code == 401:
                    return TestConnectionResponse(success=False, message="Tenable: invalid access/secret keys")
                else:
                    return TestConnectionResponse(success=False, message=f"Tenable returned HTTP {resp.status_code}")

            elif integration == "qualys":
                username = config.get("username", "")
                password = config.get("password", "")
                platform_url = config.get("platform_url", "https://qualysapi.qualys.com")
                if not username or not password:
                    return TestConnectionResponse(success=False, message="username and password are required")
                resp = await client.get(
                    f"{platform_url.rstrip('/')}/msp/about.php",
                    auth=(username, password),
                    headers={"X-Requested-With": "Glasswatch"},
                )
                if resp.status_code == 200:
                    return TestConnectionResponse(success=True, message="Qualys connection healthy")
                elif resp.status_code == 401:
                    return TestConnectionResponse(success=False, message="Qualys: invalid credentials")
                else:
                    return TestConnectionResponse(success=False, message=f"Qualys returned HTTP {resp.status_code}")

            elif integration == "rapid7":
                host = config.get("host", "").rstrip("/")
                api_key = config.get("api_key", "")
                if not host or not api_key:
                    return TestConnectionResponse(success=False, message="host and api_key are required")
                resp = await client.get(
                    f"{host}/api/3/health",
                    headers={"X-Api-Key": api_key},
                )
                if resp.status_code == 200:
                    return TestConnectionResponse(success=True, message="Rapid7 InsightVM connection healthy")
                elif resp.status_code == 401:
                    return TestConnectionResponse(success=False, message="Rapid7: invalid API key")
                else:
                    return TestConnectionResponse(success=False, message=f"Rapid7 returned HTTP {resp.status_code}")

            else:
                return TestConnectionResponse(success=False, message=f"Unknown integration: {integration}")

    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Connection timed out after 10s")
    except Exception as e:
        return TestConnectionResponse(success=False, message=f"Connection failed: {str(e)[:200]}")
