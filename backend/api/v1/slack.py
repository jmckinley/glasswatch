"""
Slack integration API endpoints.

Handles:
- OAuth install flow
- Callback handling
- Event subscriptions
- Interactive messages
- Slash commands
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.core.auth_workos import get_current_user
from backend.models.user import User
from backend.services.slack_service import slack_service


router = APIRouter()


# Pydantic models
class SlackStatusResponse(BaseModel):
    connected: bool
    team_name: Optional[str] = None
    team_id: Optional[str] = None
    installed_at: Optional[str] = None


class SlackInstallResponse(BaseModel):
    authorization_url: str


class SlackCallbackResponse(BaseModel):
    success: bool
    team_name: str
    team_id: str
    message: str = "Slack successfully connected"


class SlackMessageRequest(BaseModel):
    channel: str
    text: str
    blocks: Optional[list] = None


@router.get("/install", response_model=SlackInstallResponse)
async def initiate_slack_install(
    current_user: User = Depends(get_current_user),
    state: Optional[str] = Query(None),
):
    """
    Initiate Slack OAuth install flow.
    
    Returns authorization URL to redirect user to.
    """
    if not slack_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Slack integration not configured on this instance"
        )
    
    # Generate install URL with tenant_id in state
    authorization_url = await slack_service.get_install_url(
        tenant_id=str(current_user.tenant_id),
        state=state,
    )
    
    return SlackInstallResponse(authorization_url=authorization_url)


@router.get("/callback", response_model=SlackCallbackResponse)
async def handle_slack_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Slack OAuth callback.
    
    Exchanges code for access token and stores in tenant settings.
    """
    # Extract tenant_id from state
    if not state or not state.startswith("tenant:"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    tenant_id = state.replace("tenant:", "")
    
    # Exchange code for token
    result = await slack_service.handle_oauth_callback(
        code=code,
        tenant_id=tenant_id,
        db=db,
    )
    
    return SlackCallbackResponse(
        success=True,
        team_name=result["team_name"],
        team_id=result["team_id"],
    )


@router.get("/status", response_model=SlackStatusResponse)
async def get_slack_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Slack connection status for current tenant.
    """
    slack_config = await slack_service.get_slack_config(
        tenant_id=str(current_user.tenant_id),
        db=db,
    )
    
    if not slack_config:
        return SlackStatusResponse(connected=False)
    
    return SlackStatusResponse(
        connected=True,
        team_name=slack_config.get("team_name"),
        team_id=slack_config.get("team_id"),
        installed_at=slack_config.get("installed_at"),
    )


@router.delete("/disconnect")
async def disconnect_slack(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect Slack integration.
    
    Removes Slack configuration from tenant settings.
    """
    from sqlalchemy import select
    from backend.models.tenant import Tenant
    
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Remove Slack config
    if tenant.settings and "slack" in tenant.settings:
        tenant.settings.pop("slack")
        await db.commit()
    
    return {"success": True, "message": "Slack disconnected"}


@router.post("/events")
async def handle_slack_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Slack Events API callbacks.
    
    Verifies request signature and processes events.
    """
    # Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    # Get raw body
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # Verify signature
    if not slack_service.verify_signature(timestamp, body_str, signature):
        raise HTTPException(status_code=403, detail="Invalid request signature")
    
    # Parse JSON
    try:
        data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Handle event
    event = data.get("event", {})
    event_type = event.get("type")
    
    # Process event (TODO: implement actual event handlers)
    print(f"Received Slack event: {event_type}")
    
    return {"ok": True}


@router.post("/commands")
async def handle_slack_commands(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Slack slash commands.
    """
    # Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    # Get raw body
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # Verify signature
    if not slack_service.verify_signature(timestamp, body_str, signature):
        raise HTTPException(status_code=403, detail="Invalid request signature")
    
    # Parse form data
    from urllib.parse import parse_qs
    data = parse_qs(body_str)
    
    command = data.get("command", [""])[0]
    text = data.get("text", [""])[0]
    team_id = data.get("team_id", [""])[0]
    
    # TODO: Map team_id to tenant_id
    tenant_id = "unknown"
    
    # Handle command
    response = await slack_service.handle_slash_command(
        command=command,
        text=text,
        tenant_id=tenant_id,
        db=db,
    )
    
    return response


@router.post("/interactions")
async def handle_slack_interactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Slack interactive messages (button clicks, etc.).
    """
    # Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    # Get raw body
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # Verify signature
    if not slack_service.verify_signature(timestamp, body_str, signature):
        raise HTTPException(status_code=403, detail="Invalid request signature")
    
    # Parse form data (Slack sends payload as form-encoded)
    from urllib.parse import parse_qs
    data = parse_qs(body_str)
    payload_str = data.get("payload", [""])[0]
    
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in payload")
    
    # Handle interaction
    response = await slack_service.handle_interaction(payload, db)
    
    return response


@router.post("/test-message")
async def send_test_message(
    message_data: SlackMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a test message to Slack (for testing integration).
    """
    result = await slack_service.send_message(
        tenant_id=str(current_user.tenant_id),
        channel=message_data.channel,
        text=message_data.text,
        blocks=message_data.blocks,
        db=db,
    )
    
    return {"success": True, "slack_response": result}
