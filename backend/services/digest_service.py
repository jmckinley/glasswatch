"""
Weekly Digest Service.

Builds and sends a weekly summary email to tenant users via Resend API,
falling back to SMTP if Resend is not configured.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession


async def send_weekly_digest(tenant_id: UUID, db: AsyncSession) -> dict:
    """
    Generate and send the weekly digest email for a tenant.

    Queries:
    - Total open vulnerabilities
    - New vulnerabilities this week
    - KEV-listed vulnerabilities
    - Bundles completed this week
    - Goals on track

    Returns a result dict with status and recipient info.
    """
    from backend.models.tenant import Tenant
    from backend.models.vulnerability import Vulnerability
    from backend.models.bundle import Bundle
    from backend.models.goal import Goal

    # Load tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return {"success": False, "error": "Tenant not found"}

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # ── Stats queries ────────────────────────────────────────────────────────

    # Total open vulns
    total_vulns_result = await db.execute(
        select(func.count(Vulnerability.id)).where(
            and_(
                Vulnerability.tenant_id == tenant_id,
                Vulnerability.status.not_in(["remediated", "accepted"]),
            )
        )
    )
    total_vulns = total_vulns_result.scalar() or 0

    # New this week
    new_vulns_result = await db.execute(
        select(func.count(Vulnerability.id)).where(
            and_(
                Vulnerability.tenant_id == tenant_id,
                Vulnerability.created_at >= week_ago,
            )
        )
    )
    new_vulns = new_vulns_result.scalar() or 0

    # KEV count
    kev_result = await db.execute(
        select(func.count(Vulnerability.id)).where(
            and_(
                Vulnerability.tenant_id == tenant_id,
                Vulnerability.kev_listed == True,  # noqa: E712
                Vulnerability.status.not_in(["remediated", "accepted"]),
            )
        )
    )
    kev_count = kev_result.scalar() or 0

    # Bundles completed this week
    bundles_result = await db.execute(
        select(func.count(Bundle.id)).where(
            and_(
                Bundle.tenant_id == tenant_id,
                Bundle.status == "completed",
                Bundle.completed_at >= week_ago,
            )
        )
    )
    bundles_completed = bundles_result.scalar() or 0

    # Goals on track (active goals not past their due date or target met)
    try:
        goals_result = await db.execute(
            select(func.count(Goal.id)).where(
                and_(
                    Goal.tenant_id == tenant_id,
                    Goal.status == "active",
                )
            )
        )
        goals_on_track = goals_result.scalar() or 0
    except Exception:
        goals_on_track = 0

    # ── Build HTML email ─────────────────────────────────────────────────────

    week_str = now.strftime("%B %d, %Y")
    kev_badge = (
        f'<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:12px;font-size:12px;">'
        f"{kev_count} KEV</span>"
        if kev_count
        else ""
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background:#f0f2f5; margin:0; padding:20px; }}
    .wrap {{ max-width:600px; margin:0 auto; }}
    .header {{ background:#111827; color:white; padding:24px 28px; border-radius:8px 8px 0 0; }}
    .header h1 {{ margin:0; font-size:22px; }}
    .header p {{ margin:4px 0 0; color:#9ca3af; font-size:14px; }}
    .body {{ background:#ffffff; padding:28px; border-radius:0 0 8px 8px; }}
    table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
    th {{ background:#f9fafb; text-align:left; padding:10px 12px;
          font-size:13px; color:#6b7280; border-bottom:1px solid #e5e7eb; }}
    td {{ padding:12px; font-size:15px; border-bottom:1px solid #f3f4f6; }}
    td.label {{ color:#374151; font-weight:500; }}
    td.value {{ color:#111827; font-weight:700; font-size:20px; }}
    td.delta {{ color:#6b7280; font-size:12px; }}
    .cta {{ display:inline-block; margin-top:16px; padding:12px 24px;
            background:#2563eb; color:white; border-radius:6px;
            text-decoration:none; font-weight:600; font-size:14px; }}
    .footer {{ color:#9ca3af; font-size:12px; margin-top:20px; text-align:center; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>⚡ Glasswatch Weekly Digest</h1>
    <p>Week ending {week_str}</p>
  </div>
  <div class="body">
    <p style="color:#374151;">Here's your patch management summary for the past 7 days.</p>

    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="label">Open Vulnerabilities</td>
          <td class="value">{total_vulns}</td>
          <td class="delta">+{new_vulns} new this week</td>
        </tr>
        <tr>
          <td class="label">KEV-Listed (open)</td>
          <td class="value">{kev_count}</td>
          <td class="delta">{kev_badge}</td>
        </tr>
        <tr>
          <td class="label">Bundles Completed</td>
          <td class="value">{bundles_completed}</td>
          <td class="delta">this week</td>
        </tr>
        <tr>
          <td class="label">Goals Active</td>
          <td class="value">{goals_on_track}</td>
          <td class="delta">being tracked</td>
        </tr>
      </tbody>
    </table>

    {"<p style='color:#dc3545;font-weight:600;'>⚠️ " + str(kev_count) + " KEV-listed vulnerabilities require immediate attention.</p>" if kev_count else ""}

    <a href="https://glasswatch-production.up.railway.app/vulnerabilities" class="cta">
      View Dashboard →
    </a>
  </div>
  <div class="footer">
    You're receiving this because digest emails are enabled for your Glasswatch workspace.<br />
    Generated {now.strftime('%Y-%m-%d %H:%M UTC')}
  </div>
</div>
</body>
</html>"""

    # ── Send email ────────────────────────────────────────────────────────────

    notif_settings = (tenant.settings or {}).get("notifications", {})
    email_config = (tenant.settings or {}).get("integrations", {}).get("email", {})

    import os
    api_key = (
        notif_settings.get("email_resend_api_key")
        or email_config.get("resend_api_key")
        or os.environ.get("RESEND_API_KEY")
    )

    recipients = email_config.get("recipients", [])
    if not recipients and hasattr(tenant, "email") and tenant.email:
        recipients = [tenant.email]

    if not recipients:
        return {"success": False, "error": "No email recipients configured for tenant"}

    from_address = email_config.get("from_address", "snapper@updates.mckinleylabsllc.com")
    subject = f"Glasswatch Weekly Digest — {week_str}"

    if api_key:
        return await _send_via_resend(api_key, from_address, recipients, subject, html_body)
    else:
        return await _send_via_smtp(from_address, recipients, subject, html_body)


async def _send_via_resend(
    api_key: str,
    from_address: str,
    recipients: list,
    subject: str,
    html_body: str,
) -> dict:
    """Send via Resend API (lazy import)."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_address,
                    "to": recipients,
                    "subject": subject,
                    "html": html_body,
                },
            )

        if resp.status_code in (200, 201):
            return {"success": True, "provider": "resend", "recipients": recipients, "id": resp.json().get("id")}
        else:
            raise Exception(f"Resend returned {resp.status_code}: {resp.text}")

    except Exception as e:
        # Fall back to SMTP
        return await _send_via_smtp(from_address, recipients, subject, html_body, resend_error=str(e))


async def _send_via_smtp(
    from_address: str,
    recipients: list,
    subject: str,
    html_body: str,
    resend_error: Optional[str] = None,
) -> dict:
    """Fall back SMTP delivery via smtplib (sync, run in executor)."""
    import os
    import asyncio
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        return {
            "success": False,
            "error": "No email transport configured (Resend API key or SMTP credentials required)",
            "resend_error": resend_error,
        }

    def _send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_address
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_address, recipients, msg.as_string())

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)
    return {"success": True, "provider": "smtp", "recipients": recipients}
