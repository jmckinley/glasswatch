"""
Connections API endpoints.

Manages external service integrations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.db.session import get_db
from backend.core.auth_workos import get_current_user
from backend.models.user import User
from backend.models.connection import Connection
from backend.services.connection_health import connection_health_service


router = APIRouter()


# Pydantic models
class ConnectionBase(BaseModel):
    provider: str = Field(..., description="Provider type (aws, azure, gcp, slack, jira, servicenow, webhook)")
    name: str = Field(..., description="User-friendly name")
    config: Dict[str, Any] = Field(..., description="Provider-specific configuration")


class ConnectionCreate(ConnectionBase):
    pass


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    provider: str
    name: str
    config: Dict[str, Any]  # Will be masked
    status: str
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class ProviderInfo(BaseModel):
    name: str
    display_name: str
    description: str
    required_fields: List[str]
    optional_fields: List[str]


class ProvidersResponse(BaseModel):
    providers: List[ProviderInfo]


class HealthCheckResponse(BaseModel):
    success: bool
    message: str
    checked_at: datetime


# Provider metadata
PROVIDER_METADATA = {
    "aws": {
        "display_name": "Amazon Web Services (AWS)",
        "description": "Connect to AWS for cloud resource discovery and management",
        "required_fields": ["access_key_id", "secret_access_key", "region"],
        "optional_fields": ["session_token"],
    },
    "azure": {
        "display_name": "Microsoft Azure",
        "description": "Connect to Azure for cloud resource discovery and management",
        "required_fields": ["tenant_id", "client_id", "client_secret"],
        "optional_fields": ["subscription_id"],
    },
    "gcp": {
        "display_name": "Google Cloud Platform (GCP)",
        "description": "Connect to GCP for cloud resource discovery and management",
        "required_fields": ["service_account_json"],
        "optional_fields": ["project_id"],
    },
    "slack": {
        "display_name": "Slack",
        "description": "Connect to Slack for notifications and collaboration",
        "required_fields": ["access_token"],
        "optional_fields": ["channel"],
    },
    "jira": {
        "display_name": "Atlassian Jira",
        "description": "Connect to Jira for issue tracking and project management",
        "required_fields": ["url", "email", "api_token"],
        "optional_fields": ["project_key"],
    },
    "servicenow": {
        "display_name": "ServiceNow",
        "description": "Connect to ServiceNow for ITSM and incident management",
        "required_fields": ["instance_url", "username", "password"],
        "optional_fields": [],
    },
    "webhook": {
        "display_name": "Generic Webhook",
        "description": "Connect to any HTTP webhook endpoint",
        "required_fields": ["url"],
        "optional_fields": ["headers", "method"],
    },
    "tenable": {
        "display_name": "Tenable.io",
        "description": "Connect to Tenable.io for vulnerability scanning and asset discovery",
        "required_fields": ["access_key", "secret_key"],
        "optional_fields": [],
    },
    "qualys": {
        "display_name": "Qualys VMDR",
        "description": "Connect to Qualys for vulnerability management and reporting",
        "required_fields": ["username", "password"],
        "optional_fields": ["platform_url"],
    },
    "rapid7": {
        "display_name": "Rapid7 InsightVM",
        "description": "Connect to Rapid7 InsightVM for vulnerability scanning",
        "required_fields": ["host", "api_key"],
        "optional_fields": [],
    },
}


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """
    List available connection provider types.
    
    Returns metadata about each provider including required configuration fields.
    """
    providers = [
        ProviderInfo(
            name=name,
            display_name=meta["display_name"],
            description=meta["description"],
            required_fields=meta["required_fields"],
            optional_fields=meta["optional_fields"],
        )
        for name, meta in PROVIDER_METADATA.items()
    ]
    
    return ProvidersResponse(providers=providers)


@router.get("", response_model=List[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider: Optional[str] = Query(None, description="Filter by provider type"),
):
    """
    List all connections for the current tenant.
    
    Secrets in config are masked.
    """
    query = select(Connection).where(Connection.tenant_id == current_user.tenant_id)
    
    if provider:
        query = query.where(Connection.provider == provider)
    
    result = await db.execute(query)
    connections = result.scalars().all()
    
    # Mask secrets in config
    return [
        ConnectionResponse(
            id=str(conn.id),
            tenant_id=str(conn.tenant_id),
            provider=conn.provider,
            name=conn.name,
            config=conn.mask_secrets(),  # Use the mask_secrets method
            status=conn.status,
            last_health_check=conn.last_health_check,
            last_error=conn.last_error,
            created_at=conn.created_at,
            updated_at=conn.updated_at,
        )
        for conn in connections
    ]


@router.post("", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    connection_data: ConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new connection.
    
    Config will be encrypted at rest (TODO: implement encryption).
    """
    # Validate provider
    if connection_data.provider not in PROVIDER_METADATA:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {connection_data.provider}. Valid providers: {', '.join(PROVIDER_METADATA.keys())}"
        )
    
    # Validate required fields
    required_fields = PROVIDER_METADATA[connection_data.provider]["required_fields"]
    missing_fields = [f for f in required_fields if f not in connection_data.config]
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for {connection_data.provider}: {', '.join(missing_fields)}"
        )
    
    # Create connection
    connection = Connection(
        tenant_id=current_user.tenant_id,
        provider=connection_data.provider,
        name=connection_data.name,
        config=connection_data.config,
        status="pending",
    )
    
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    
    # Return with masked secrets
    return ConnectionResponse(
        id=str(connection.id),
        tenant_id=str(connection.tenant_id),
        provider=connection.provider,
        name=connection.name,
        config=connection.mask_secrets(),
        status=connection.status,
        last_health_check=connection.last_health_check,
        last_error=connection.last_error,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific connection.
    
    Secrets are masked in the response.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.tenant_id == current_user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return ConnectionResponse(
        id=str(connection.id),
        tenant_id=str(connection.tenant_id),
        provider=connection.provider,
        name=connection.name,
        config=connection.mask_secrets(),
        status=connection.status,
        last_health_check=connection.last_health_check,
        last_error=connection.last_error,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: UUID,
    connection_data: ConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a connection.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.tenant_id == current_user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Update fields
    if connection_data.name is not None:
        connection.name = connection_data.name
    
    if connection_data.config is not None:
        connection.config = connection_data.config
    
    if connection_data.status is not None:
        connection.status = connection_data.status
    
    connection.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(connection)
    
    return ConnectionResponse(
        id=str(connection.id),
        tenant_id=str(connection.tenant_id),
        provider=connection.provider,
        name=connection.name,
        config=connection.mask_secrets(),
        status=connection.status,
        last_health_check=connection.last_health_check,
        last_error=connection.last_error,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a connection.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.tenant_id == current_user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    await db.delete(connection)
    await db.commit()
    
    return {"success": True, "message": "Connection deleted"}


@router.post("/{connection_id}/test", response_model=HealthCheckResponse)
async def test_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a connection's health.
    
    Runs a provider-specific health check and updates the connection status.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.tenant_id == current_user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Run health check
    success, message = await connection_health_service.check_health(
        provider=connection.provider,
        config=connection.config,
    )
    
    # Update connection status
    now = datetime.now(timezone.utc)
    
    if success:
        connection.status = "active"
        connection.last_health_check = now
        connection.last_error = None
    else:
        connection.status = "error"
        connection.last_error = message
    
    connection.updated_at = now
    
    await db.commit()
    
    return HealthCheckResponse(
        success=success,
        message=message,
        checked_at=now,
    )
