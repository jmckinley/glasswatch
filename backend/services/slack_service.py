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
            # Approve the bundle
            from backend.models.patch_bundle import PatchBundle
            from backend.models.approval import ApprovalAction, ApprovalStatus
            from sqlalchemy import select
            from datetime import datetime, timezone
            from uuid import UUID
            
            try:
                # Parse bundle_id
                bundle_uuid = UUID(bundle_id)
                
                # Get the bundle
                result = await db.execute(
                    select(PatchBundle).where(PatchBundle.id == bundle_uuid)
                )
                bundle = result.scalar_one_or_none()
                
                if not bundle:
                    return {
                        "text": f"❌ Bundle `{bundle_id}` not found",
                        "replace_original": False,
                    }
                
                # Update bundle status
                bundle.status = "approved"
                bundle.approved_by = user_name
                bundle.approved_at = datetime.now(timezone.utc)
                
                # Create approval decision record
                approval_action = ApprovalAction(
                    bundle_id=bundle.id,
                    tenant_id=bundle.tenant_id,
                    status=ApprovalStatus.APPROVED,
                    comment=f"Approved via Slack by {user_name}",
                    acted_at=datetime.now(timezone.utc),
                )
                
                db.add(approval_action)
                await db.commit()
                
                # Post confirmation to channel
                return {
                    "text": f"✅ Bundle `{bundle.name}` approved by @{user_name}",
                    "replace_original": True,
                }
            except Exception as e:
                return {
                    "text": f"❌ Error approving bundle: {str(e)}",
                    "replace_original": False,
                }
        
        elif action_id == "reject_bundle":
            # Reject the bundle
            from backend.models.patch_bundle import PatchBundle
            from backend.models.approval import ApprovalAction, ApprovalStatus
            from sqlalchemy import select
            from datetime import datetime, timezone
            from uuid import UUID
            
            try:
                # Parse bundle_id
                bundle_uuid = UUID(bundle_id)
                
                # Get the bundle
                result = await db.execute(
                    select(PatchBundle).where(PatchBundle.id == bundle_uuid)
                )
                bundle = result.scalar_one_or_none()
                
                if not bundle:
                    return {
                        "text": f"❌ Bundle `{bundle_id}` not found",
                        "replace_original": False,
                    }
                
                # Update bundle status
                bundle.status = "cancelled"
                
                # Create approval decision record
                approval_action = ApprovalAction(
                    bundle_id=bundle.id,
                    tenant_id=bundle.tenant_id,
                    status=ApprovalStatus.REJECTED,
                    comment=f"Rejected via Slack by {user_name}",
                    acted_at=datetime.now(timezone.utc),
                )
                
                db.add(approval_action)
                await db.commit()
                
                # Post confirmation to channel
                return {
                    "text": f"❌ Bundle `{bundle.name}` rejected by @{user_name}",
                    "replace_original": True,
                }
            except Exception as e:
                return {
                    "text": f"❌ Error rejecting bundle: {str(e)}",
                    "replace_original": False,
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
            # Get actual system status
            from backend.models.vulnerability import Vulnerability
            from backend.models.patch_bundle import PatchBundle
            from backend.models.snapshot import Snapshot
            from sqlalchemy import select, func
            from datetime import datetime, timezone, timedelta
            
            try:
                # Get tenant
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                if not tenant:
                    return {
                        "response_type": "ephemeral",
                        "text": "❌ Tenant not found"
                    }
                
                # Count active vulnerabilities
                vuln_result = await db.execute(
                    select(func.count(Vulnerability.id))
                    .select_from(Vulnerability)
                    .join(Vulnerability.asset_vulnerabilities)
                    .where(Vulnerability.asset_vulnerabilities.any())
                )
                total_vulns = vuln_result.scalar() or 0
                
                # Count critical vulnerabilities
                critical_result = await db.execute(
                    select(func.count(Vulnerability.id))
                    .select_from(Vulnerability)
                    .join(Vulnerability.asset_vulnerabilities)
                    .where(
                        Vulnerability.asset_vulnerabilities.any(),
                        Vulnerability.severity == "CRITICAL"
                    )
                )
                critical_vulns = critical_result.scalar() or 0
                
                # Count pending bundles
                pending_result = await db.execute(
                    select(func.count(PatchBundle.id)).where(
                        PatchBundle.tenant_id == tenant_id,
                        PatchBundle.status.in_(["pending_approval", "approved"])
                    )
                )
                pending_bundles = pending_result.scalar() or 0
                
                # Count overdue bundles (scheduled in the past but not completed)
                now = datetime.now(timezone.utc)
                overdue_result = await db.execute(
                    select(func.count(PatchBundle.id)).where(
                        PatchBundle.tenant_id == tenant_id,
                        PatchBundle.scheduled_for < now,
                        PatchBundle.status.in_(["scheduled", "approved", "in_progress"])
                    )
                )
                overdue_bundles = overdue_result.scalar() or 0
                
                # Get last scan timestamp
                last_scan_result = await db.execute(
                    select(Snapshot.created_at)
                    .where(Snapshot.tenant_id == tenant_id)
                    .order_by(Snapshot.created_at.desc())
                    .limit(1)
                )
                last_scan = last_scan_result.scalar_one_or_none()
                last_scan_str = last_scan.strftime("%Y-%m-%d %H:%M UTC") if last_scan else "Never"
                
                # Build status message
                text = f"""📊 *Glasswatch System Status*

*Vulnerabilities:*
• Total Active: {total_vulns}
• Critical: {critical_vulns}

*Patch Bundles:*
• Pending: {pending_bundles}
• Overdue: {overdue_bundles}

*Last Scan:* {last_scan_str}
"""
                
                return {
                    "response_type": "ephemeral",
                    "text": text
                }
            except Exception as e:
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ Error fetching status: {str(e)}"
                }
        
        elif subcommand == "bundles":
            # Fetch actual bundles
            from backend.models.patch_bundle import PatchBundle
            from sqlalchemy import select
            
            try:
                # Get tenant
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                if not tenant:
                    return {
                        "response_type": "ephemeral",
                        "text": "❌ Tenant not found"
                    }
                
                # Query active bundles
                bundles_result = await db.execute(
                    select(PatchBundle)
                    .where(
                        PatchBundle.tenant_id == tenant_id,
                        PatchBundle.status.in_(["pending_approval", "approved", "in_progress"])
                    )
                    .order_by(PatchBundle.created_at.desc())
                    .limit(5)
                )
                bundles = bundles_result.scalars().all()
                
                if not bundles:
                    return {
                        "response_type": "ephemeral",
                        "text": "📦 No active bundles at this time."
                    }
                
                # Build Slack blocks
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "📦 Active Patch Bundles"
                        }
                    }
                ]
                
                for bundle in bundles:
                    # Status emoji
                    status_emoji = {
                        "pending_approval": "⏳",
                        "approved": "✅",
                        "in_progress": "⏳",
                    }.get(bundle.status, "📦")
                    
                    # Format created date
                    created_str = bundle.created_at.strftime("%Y-%m-%d") if bundle.created_at else "Unknown"
                    
                    # Count items (from items relationship or assets_affected_count)
                    item_count = bundle.assets_affected_count or 0
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{status_emoji} *{bundle.name}*\nStatus: {bundle.status}\nItems: {item_count}\nCreated: {created_str}"
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View"
                            },
                            "url": f"{settings.FRONTEND_URL or 'http://localhost:3000'}/bundles/{bundle.id}"
                        }
                    })
                    blocks.append({"type": "divider"})
                
                # Remove last divider
                if blocks[-1]["type"] == "divider":
                    blocks.pop()
                
                return {
                    "response_type": "ephemeral",
                    "blocks": blocks,
                    "text": f"Found {len(bundles)} active bundle(s)"
                }
            except Exception as e:
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ Error fetching bundles: {str(e)}"
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
