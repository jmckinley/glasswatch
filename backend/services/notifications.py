"""
Notification service for alerts and updates.

Supports Slack, Microsoft Teams, Email, and in-app notifications.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
import httpx
import json

from backend.core.config import settings
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability
from backend.models.bundle import Bundle


class NotificationChannel(str, Enum):
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationType(str, Enum):
    CRITICAL_VULN = "critical_vulnerability"
    KEV_ADDED = "kev_added"
    BUNDLE_READY = "bundle_ready"
    APPROVAL_NEEDED = "approval_needed"
    PATCH_SUCCESS = "patch_success"
    PATCH_FAILED = "patch_failed"
    SLA_BREACH = "sla_breach"
    WEEKLY_DIGEST = "weekly_digest"


class NotificationService:
    """
    Central notification service for PatchAI.
    
    Handles routing notifications to configured channels based on
    tenant preferences and notification type.
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient()
    
    async def send_notification(
        self,
        tenant: Tenant,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        priority: Literal["low", "normal", "high", "critical"] = "normal",
    ) -> Dict[str, Any]:
        """
        Send a notification to configured channels.
        
        If channels not specified, uses tenant's default channels for the notification type.
        """
        # Get channels from tenant config if not specified
        if not channels:
            channels = self._get_channels_for_type(tenant, notification_type)
        
        results = {}
        for channel in channels:
            try:
                if channel == NotificationChannel.SLACK:
                    result = await self._send_slack(tenant, title, message, data, priority)
                elif channel == NotificationChannel.TEAMS:
                    result = await self._send_teams(tenant, title, message, data, priority)
                elif channel == NotificationChannel.EMAIL:
                    result = await self._send_email(tenant, title, message, data, priority)
                elif channel == NotificationChannel.WEBHOOK:
                    result = await self._send_webhook(tenant, title, message, data, priority)
                elif channel == NotificationChannel.IN_APP:
                    result = await self._send_in_app(tenant, title, message, data, priority)
                
                results[channel.value] = {"success": True, "result": result}
            except Exception as e:
                results[channel.value] = {"success": False, "error": str(e)}
        
        return results
    
    def _get_channels_for_type(
        self,
        tenant: Tenant,
        notification_type: NotificationType
    ) -> List[NotificationChannel]:
        """Get configured channels for a notification type."""
        # Get from tenant settings
        notification_config = tenant.settings.get("notifications", {})
        type_config = notification_config.get(notification_type.value, {})
        
        # Default channels if not configured
        default_channels = {
            NotificationType.CRITICAL_VULN: [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            NotificationType.KEV_ADDED: [NotificationChannel.SLACK],
            NotificationType.BUNDLE_READY: [NotificationChannel.EMAIL],
            NotificationType.APPROVAL_NEEDED: [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            NotificationType.PATCH_FAILED: [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            NotificationType.SLA_BREACH: [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            NotificationType.WEEKLY_DIGEST: [NotificationChannel.EMAIL],
        }
        
        channel_names = type_config.get("channels", default_channels.get(notification_type, []))
        return [NotificationChannel(name) for name in channel_names]
    
    async def _send_slack(
        self,
        tenant: Tenant,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Send Slack notification using webhook or API."""
        slack_config = tenant.settings.get("integrations", {}).get("slack", {})
        webhook_url = slack_config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        
        # Build Slack message with blocks for rich formatting
        color = {
            "low": "#36a64f",      # green
            "normal": "#2eb886",   # teal
            "high": "#ff9f00",     # orange
            "critical": "#dc3545", # red
        }.get(priority, "#2eb886")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "fallback": f"{title}: {message}",
                "footer": "PatchAI",
                "footer_icon": "https://patchai.io/icon.png",
                "ts": int(datetime.utcnow().timestamp()),
            }]
        }
        
        # Add action buttons for certain types
        if data and data.get("action_url"):
            payload["attachments"][0]["actions"] = [{
                "type": "button",
                "text": data.get("action_text", "View Details"),
                "url": data["action_url"],
                "style": "primary" if priority in ["high", "critical"] else "default",
            }]
        
        response = await self.client.post(webhook_url, json=payload)
        response.raise_for_status()
        
        return {"message_sent": True, "channel": "slack"}
    
    async def _send_teams(
        self,
        tenant: Tenant,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Send Microsoft Teams notification using webhook."""
        teams_config = tenant.settings.get("integrations", {}).get("teams", {})
        webhook_url = teams_config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Teams webhook URL not configured")
        
        # Build Teams adaptive card
        theme_color = {
            "low": "good",
            "normal": "default",
            "high": "warning",
            "critical": "attention",
        }.get(priority, "default")
        
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": theme_color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": "PatchAI Notification",
                "text": message,
                "markdown": True,
            }],
        }
        
        # Add action buttons
        if data and data.get("action_url"):
            card["potentialAction"] = [{
                "@type": "OpenUri",
                "name": data.get("action_text", "View Details"),
                "targets": [{
                    "os": "default",
                    "uri": data["action_url"]
                }]
            }]
        
        response = await self.client.post(webhook_url, json=card)
        response.raise_for_status()
        
        return {"message_sent": True, "channel": "teams"}
    
    async def _send_email(
        self,
        tenant: Tenant,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Send email notification."""
        # Get email config and recipients
        email_config = tenant.settings.get("integrations", {}).get("email", {})
        recipients = email_config.get("recipients", [tenant.email])
        
        # Format HTML email
        priority_badge = {
            "low": '<span style="color: #36a64f;">●</span>',
            "normal": '<span style="color: #2eb886;">●</span>',
            "high": '<span style="color: #ff9f00;">●</span>',
            "critical": '<span style="color: #dc3545;">●</span>',
        }.get(priority, "")
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a1a1a; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 10px 20px; background: #2dd4bf; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{priority_badge} {title}</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                    {"<a href='" + data['action_url'] + "' class='button'>" + data.get('action_text', 'View Details') + "</a>" if data and data.get('action_url') else ""}
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sent by PatchAI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # TODO: Integrate with email service (SendGrid, SES, etc.)
        # For now, just log that we would send an email
        return {
            "message_sent": True,
            "channel": "email",
            "recipients": recipients,
        }
    
    async def _send_webhook(
        self,
        tenant: Tenant,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Send generic webhook notification."""
        webhook_config = tenant.settings.get("integrations", {}).get("webhook", {})
        webhook_url = webhook_config.get("url")
        
        if not webhook_url:
            raise ValueError("Webhook URL not configured")
        
        # Standard webhook payload
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": str(tenant.id),
            "priority": priority,
            "title": title,
            "message": message,
            "data": data or {},
        }
        
        # Add auth if configured
        headers = {}
        if webhook_config.get("auth_header"):
            headers[webhook_config["auth_header"]] = webhook_config.get("auth_value", "")
        
        response = await self.client.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        
        return {"message_sent": True, "channel": "webhook"}
    
    async def _send_in_app(
        self,
        tenant: Tenant,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Store in-app notification for display in UI."""
        # TODO: Store in database for UI to fetch
        # For now, just return success
        return {
            "message_sent": True,
            "channel": "in_app",
            "notification_id": "demo-" + str(datetime.utcnow().timestamp()),
        }
    
    async def send_critical_vulnerability_alert(
        self,
        tenant: Tenant,
        vulnerability: Vulnerability,
        affected_assets: List[Asset],
    ):
        """Send alert for new critical vulnerability."""
        title = f"🚨 New Critical Vulnerability: {vulnerability.identifier}"
        
        message = f"""
A new critical vulnerability has been detected in your environment.

**CVE:** {vulnerability.identifier}
**CVSS Score:** {vulnerability.cvss_score}
**Affected Assets:** {len(affected_assets)}
**KEV Listed:** {'Yes' if vulnerability.kev_listed else 'No'}

{vulnerability.description[:200]}...
"""
        
        data = {
            "vulnerability_id": str(vulnerability.id),
            "action_url": f"{settings.APP_URL}/vulnerabilities/{vulnerability.id}",
            "action_text": "View Vulnerability",
        }
        
        await self.send_notification(
            tenant=tenant,
            notification_type=NotificationType.CRITICAL_VULN,
            title=title,
            message=message.strip(),
            data=data,
            priority="critical",
        )
    
    async def send_bundle_ready_notification(
        self,
        tenant: Tenant,
        bundle: Bundle,
    ):
        """Send notification that a bundle is ready for review."""
        title = f"📦 Patch Bundle Ready: {bundle.name}"
        
        message = f"""
A new patch bundle has been created and is ready for review.

**Bundle:** {bundle.name}
**Scheduled:** {bundle.scheduled_for.strftime('%Y-%m-%d %H:%M UTC') if bundle.scheduled_for else 'Not scheduled'}
**Vulnerabilities:** {bundle.assets_affected_count}
**Risk Score:** {bundle.risk_score}
**Approval Required:** {'Yes' if bundle.approval_required else 'No'}
"""
        
        data = {
            "bundle_id": str(bundle.id),
            "action_url": f"{settings.APP_URL}/bundles/{bundle.id}",
            "action_text": "Review Bundle",
        }
        
        priority = "high" if bundle.approval_required else "normal"
        
        await self.send_notification(
            tenant=tenant,
            notification_type=NotificationType.BUNDLE_READY,
            title=title,
            message=message.strip(),
            data=data,
            priority=priority,
        )


# Global instance
notification_service = NotificationService()