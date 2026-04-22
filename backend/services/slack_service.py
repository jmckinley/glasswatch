"""
Slack integration service.

Handles:
- OAuth install flow
- Message sending
- Interactive messages (buttons)
- Slash commands
"""
import hashlib
import hmac
import json
import time
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.tenant import Tenant


class SlackService:
    """
    Slack API integration service.
    
    Provides methods for OAuth, messaging, and interactive components.
    """
    
    SLACK_OAUTH_URL = "https://slack.com/oauth/v2/authorize"
    SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    SLACK_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
    SLACK_AUTH_TEST_URL = "https://slack.com/api/auth.test"
    
    def __init__(self):
        """Initialize Slack service."""
        self.client_id = getattr(settings, "SLACK_CLIENT_ID", None)
        self.client_secret = getattr(settings, "SLACK_CLIENT_SECRET", None)
        self.signing_secret = getattr(settings, "SLACK_SIGNING_SECRET", None)
        self.redirect_uri = getattr(settings, "SLACK_REDIRECT_URI", None)
    
    def is_configured(self) -> bool:
        """Check if Slack is configured."""
        return bool(self.client_id and self.client_secret and self.signing_secret)
    
    async def get_install_url(self, tenant_id: str, state: Optional[str] = None) -> str:
        """
        Generate Slack OAuth install URL.
        
        Args:
            tenant_id: Tenant ID to associate with installation
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Slack integration not configured. Set SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, and SLACK_SIGNING_SECRET."
            )
        
        # Build state with tenant_id
        state_value = state or f"tenant:{tenant_id}"
        
        # Scopes needed for Glasswatch
        scopes = [
            "chat:write",           # Send messages
            "chat:write.public",    # Send to channels without joining
            "commands",             # Slash commands
            "channels:read",        # List channels
            "groups:read",          # List private channels
            "im:read",              # List DMs
            "users:read",           # Read user info
        ]
        
        params = {
            "client_id": self.client_id,
            "scope": ",".join(scopes),
            "redirect_uri": self.redirect_uri or f"{settings.API_V1_STR}/slack/callback",
            "state": state_value,
        }
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.SLACK_OAUTH_URL}?{query_string}"
    
    async def handle_oauth_callback(
        self, code: str, tenant_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for token.
        
        Args:
            code: OAuth authorization code
            tenant_id: Tenant ID
            db: Database session
        
        Returns:
            Installation data
        """
        if not self.is_configured():
            raise HTTPException(status_code=503, detail="Slack not configured")
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.SLACK_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri or f"{settings.API_V1_STR}/slack/callback",
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to exchange OAuth code"
                )
            
            data = response.json()
            
            if not data.get("ok"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack OAuth error: {data.get('error', 'unknown')}"
                )
        
        # Store token in tenant settings
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Update tenant settings with Slack config
        slack_config = {
            "access_token": data["access_token"],
            "team_id": data["team"]["id"],
            "team_name": data["team"]["name"],
            "bot_user_id": data.get("bot_user_id"),
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if tenant.settings is None:
            tenant.settings = {}
        
        tenant.settings["slack"] = slack_config
        await db.commit()
        
        return {
            "team_name": data["team"]["name"],
            "team_id": data["team"]["id"],
            "installed": True,
        }
    
    async def get_slack_config(self, tenant_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Get Slack configuration for a tenant.
        
        Args:
            tenant_id: Tenant ID
            db: Database session
        
        Returns:
            Slack config or None
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.settings:
            return None
        
        return tenant.settings.get("slack")
    
    async def send_message(
        self,
        tenant_id: str,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            tenant_id: Tenant ID
            channel: Channel ID or name
            text: Message text (fallback if blocks not supported)
            blocks: Optional Block Kit blocks
            db: Database session
        
        Returns:
            Slack API response
        """
        if not db:
            raise ValueError("Database session required")
        
        slack_config = await self.get_slack_config(tenant_id, db)
        
        if not slack_config:
            raise HTTPException(
                status_code=404,
                detail="Slack not connected for this tenant"
            )
        
        access_token = slack_config["access_token"]
        
        payload = {
            "channel": channel,
            "text": text,
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.SLACK_MESSAGE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to send Slack message"
                )
            
            data = response.json()
            
            if not data.get("ok"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack API error: {data.get('error', 'unknown')}"
                )
            
            return data
    
    async def send_approval_request(
        self,
        tenant_id: str,
        bundle_id: str,
        channel: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Send a patch bundle approval request with interactive buttons.
        
        Args:
            tenant_id: Tenant ID
            bundle_id: Bundle ID
            channel: Channel to send to
            db: Database session
        
        Returns:
            Slack API response
        """
        # Build Block Kit message with buttons
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 Patch Bundle Approval Request"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"A new patch bundle is ready for review.\n*Bundle ID:* `{bundle_id}`"
                }
            },
            {
                "type": "actions",
                "block_id": f"approval_actions_{bundle_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "style": "primary",
                        "value": bundle_id,
                        "action_id": "approve_bundle"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject"
                        },
                        "style": "danger",
                        "value": bundle_id,
                        "action_id": "reject_bundle"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👀 View Details"
                        },
                        "value": bundle_id,
                        "action_id": "view_bundle",
                        "url": f"{settings.FRONTEND_URL or 'http://localhost:3000'}/bundles/{bundle_id}"
                    }
                ]
            }
        ]
        
        return await self.send_message(
            tenant_id=tenant_id,
            channel=channel,
            text=f"Patch bundle approval request: {bundle_id}",
            blocks=blocks,
            db=db,
        )
    
    async def handle_interaction(self, payload: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Handle interactive message (button click).
        
        Args:
            payload: Slack interaction payload
            db: Database session
        
        Returns:
            Response to send back to Slack
        """
        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id")
        bundle_id = action.get("value")
        user_id = payload.get("user", {}).get("id")
        user_name = payload.get("user", {}).get("name", "unknown")
        
        if action_id == "approve_bundle":
            # TODO: Call approval service to approve bundle
            return {
                "text": f"✅ Bundle `{bundle_id}` approved by @{user_name}",
                "replace_original": True,
            }
        
        elif action_id == "reject_bundle":
            # TODO: Call approval service to reject bundle
            return {
                "text": f"❌ Bundle `{bundle_id}` rejected by @{user_name}",
                "replace_original": True,
            }
        
        elif action_id == "view_bundle":
            # No action needed - button has URL
            return {"text": "Opening bundle details..."}
        
        return {"text": "Unknown action"}
    
    async def handle_slash_command(
        self, command: str, text: str, tenant_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Handle slash command.
        
        Args:
            command: Command name (e.g., "/glasswatch")
            text: Command text
            tenant_id: Tenant ID
            db: Database session
        
        Returns:
            Response to send back to Slack
        """
        # Parse command
        parts = text.strip().split()
        
        if not parts:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/glasswatch [help|status|bundles]`"
            }
        
        subcommand = parts[0].lower()
        
        if subcommand == "help":
            return {
                "response_type": "ephemeral",
                "text": (
                    "*Glasswatch Commands:*\n"
                    "• `/glasswatch status` - System health status\n"
                    "• `/glasswatch bundles` - List active patch bundles\n"
                    "• `/glasswatch help` - Show this help"
                )
            }
        
        elif subcommand == "status":
            # TODO: Get actual system status
            return {
                "response_type": "ephemeral",
                "text": "✅ Glasswatch is running. All systems operational."
            }
        
        elif subcommand == "bundles":
            # TODO: Fetch actual bundles
            return {
                "response_type": "ephemeral",
                "text": "📦 No active bundles at this time."
            }
        
        else:
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: `{subcommand}`. Type `/glasswatch help` for usage."
            }
    
    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """
        Verify Slack request signature.
        
        Args:
            timestamp: X-Slack-Request-Timestamp header
            body: Raw request body
            signature: X-Slack-Signature header
        
        Returns:
            True if signature is valid
        """
        if not self.signing_secret:
            return False
        
        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 60 * 5:
            # Request is older than 5 minutes
            return False
        
        # Compute signature
        sig_basestring = f"v0:{timestamp}:{body}"
        computed_signature = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(computed_signature, signature)


# Global service instance
slack_service = SlackService()
