"""
AI Agent endpoint for Glasswatch.

Handles natural language queries and takes real actions against the database.
Supports intent parsing with a pattern-match fallback and optional Anthropic
Claude integration for the free-form fallback.
"""
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.goal import Goal
from backend.models.maintenance_window import MaintenanceWindow
from backend.models.rule import DeploymentRule
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AgentChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    response: str
    actions_taken: List[str]
    suggested_actions: List[str]


# ---------------------------------------------------------------------------
# Intent detection helpers
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("attention", ["what needs my attention", "what needs attention", "needs attention", "urgent", "show critical", "critical kev", "priority", "what's urgent", "top issues"]),
    ("cve_lookup", ["find fixes for", "patch cve", "what fixes cve", "fixes for cve", "details for cve", "info on cve", "about cve"]),
    ("approve_bundle", ["approve bundle", "approve the bundle"]),
    ("show_bundles", ["show bundles", "pending approvals", "list bundles", "pending bundles", "what bundles"]),
    ("create_rule", ["create a rule", "create rule", "add rule", "new rule", "block deployments on", "block all deployments", "blocking friday", "blocking monday", "blocking tuesday", "blocking wednesday", "blocking thursday", "blocking saturday", "blocking sunday"]),
    ("show_windows", ["show maintenance windows", "maintenance windows", "what windows", "list windows", "scheduled windows"]),
    ("add_window", ["add maintenance window", "create window", "new window", "add window", "schedule window"]),
    ("show_goals", ["show goals", "goal status", "goals progress", "list goals", "goals"]),
    ("risk_score", ["risk score", "posture", "how are we doing", "security posture", "overall risk", "current risk"]),
]


def detect_intent(message: str) -> Optional[str]:
    lower = message.lower()
    for intent, patterns in _INTENT_PATTERNS:
        for p in patterns:
            if p in lower:
                return intent
    return None


def extract_cve(message: str) -> Optional[str]:
    m = re.search(r"(CVE-\d{4}-\d{4,})", message, re.IGNORECASE)
    return m.group(1).upper() if m else None


def extract_bundle_name(message: str) -> Optional[str]:
    """Pull text after 'approve bundle' as bundle name hint."""
    m = re.search(r"approve\s+(?:the\s+)?bundle\s+(.+)", message, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_window_spec(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse day and time from messages like:
      'add maintenance window on Saturday at 2am'
      'create window every Sunday at 22:00'
    Returns a dict with optional keys: day, hour, minute.
    """
    spec: Dict[str, Any] = {}
    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    lower = message.lower()
    for day_name, day_num in day_map.items():
        if day_name in lower:
            spec["day"] = day_name.capitalize()
            spec["day_num"] = day_num
            break

    # Match "at 2am", "at 22:00", "at 10:30pm"
    time_m = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
    if time_m:
        hour = int(time_m.group(1))
        minute = int(time_m.group(2) or 0)
        period = time_m.group(3)
        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        spec["hour"] = hour
        spec["minute"] = minute

    return spec if spec else None


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------


async def handle_attention(tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    """Show KEV vulns on internet-facing assets, overdue / failed bundles."""
    actions_taken = ["Queried vulnerability database", "Checked bundle status"]
    lines: List[str] = []
    suggested: List[str] = []

    # 1. KEV vulns on internet-facing assets
    kev_stmt = (
        select(Vulnerability, Asset)
        .join(AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id)
        .join(Asset, Asset.id == AssetVulnerability.asset_id)
        .where(
            and_(
                Asset.tenant_id == tenant.id,
                Vulnerability.kev_listed == True,  # noqa: E712
                Asset.exposure == "INTERNET",
            )
        )
        .limit(5)
    )
    kev_rows = (await db.execute(kev_stmt)).all()

    if kev_rows:
        lines.append(f"🔴 **{len(kev_rows)} KEV vulnerabilities on internet-facing assets** (showing up to 5):\n")
        for vuln, asset in kev_rows:
            lines.append(
                f"  • {vuln.identifier} ({vuln.severity or 'N/A'}) on {asset.hostname or asset.identifier}"
            )
        suggested.append("View critical KEV vulnerabilities")
    else:
        lines.append("✅ No KEV vulnerabilities found on internet-facing assets.")

    # 2. Overdue / failed bundles
    now = datetime.now(timezone.utc)
    bundle_stmt = select(Bundle).where(
        and_(
            Bundle.tenant_id == tenant.id,
            or_(
                Bundle.status == "failed",
                and_(
                    Bundle.status.in_(["scheduled", "approved"]),
                    Bundle.scheduled_for < now,
                ),
            ),
        )
    ).limit(5)
    problem_bundles = (await db.execute(bundle_stmt)).scalars().all()

    if problem_bundles:
        lines.append(f"\n⚠️ **{len(problem_bundles)} bundle(s) need attention**:\n")
        for b in problem_bundles:
            status_label = "FAILED" if b.status == "failed" else "OVERDUE"
            scheduled = b.scheduled_for.strftime("%Y-%m-%d") if b.scheduled_for else "unscheduled"
            lines.append(f"  • [{status_label}] {b.name} (scheduled: {scheduled})")
        suggested.append("Review overdue bundles")
    else:
        lines.append("\n✅ No overdue or failed bundles.")

    # 3. Pending approval bundles
    pending_stmt = select(func.count()).select_from(Bundle).where(
        and_(Bundle.tenant_id == tenant.id, Bundle.status == "draft")
    )
    pending_count = (await db.execute(pending_stmt)).scalar() or 0
    if pending_count:
        lines.append(f"\n📋 **{pending_count} bundle(s) in draft** awaiting review.")
        suggested.append("Approve pending bundles")

    return AgentChatResponse(
        response="\n".join(lines) or "Everything looks good — no urgent items found.",
        actions_taken=actions_taken,
        suggested_actions=suggested,
    )


async def handle_cve_lookup(message: str, tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    cve_id = extract_cve(message)
    if not cve_id:
        return AgentChatResponse(
            response="Please specify a CVE identifier, e.g. 'Find fixes for CVE-2021-44228'.",
            actions_taken=[],
            suggested_actions=["Show me critical KEV vulnerabilities"],
        )

    vuln_stmt = select(Vulnerability).where(
        Vulnerability.identifier.ilike(f"%{cve_id}%")
    ).limit(1)
    vuln = (await db.execute(vuln_stmt)).scalar_one_or_none()

    if not vuln:
        return AgentChatResponse(
            response=f"No data found for {cve_id}. Try importing it from a scanner or via the bulk import API.",
            actions_taken=["Queried vulnerability database"],
            suggested_actions=[],
        )

    # Affected assets
    asset_stmt = (
        select(Asset)
        .join(AssetVulnerability, AssetVulnerability.asset_id == Asset.id)
        .where(
            and_(
                AssetVulnerability.vulnerability_id == vuln.id,
                Asset.tenant_id == tenant.id,
            )
        )
        .limit(5)
    )
    affected_assets = (await db.execute(asset_stmt)).scalars().all()

    # Bundles containing this vuln
    bundle_stmt = (
        select(Bundle)
        .join(BundleItem, BundleItem.bundle_id == Bundle.id)
        .where(
            and_(
                Bundle.tenant_id == tenant.id,
                BundleItem.vulnerability_id == vuln.id,
            )
        )
        .limit(3)
    )
    bundles = (await db.execute(bundle_stmt)).scalars().all()

    lines = [
        f"**{vuln.identifier}** — {vuln.title or 'No title'}",
        f"• Severity: {vuln.severity or 'Unknown'} | CVSS: {vuln.cvss_score or 'N/A'}",
        f"• EPSS: {f'{vuln.epss_score:.3f}' if vuln.epss_score else 'N/A'} | KEV: {'Yes 🔴' if vuln.kev_listed else 'No'}",
        f"• Patch available: {'Yes ✅' if vuln.patch_available else 'No ❌'}",
    ]
    if vuln.vendor_advisory_url:
        lines.append(f"• Advisory: {vuln.vendor_advisory_url}")
    if affected_assets:
        asset_names = [a.hostname or a.identifier for a in affected_assets]
        lines.append(f"• Affected assets ({len(affected_assets)} shown): {', '.join(asset_names)}")
    if bundles:
        bundle_names = [b.name for b in bundles]
        lines.append(f"• In bundles: {', '.join(bundle_names)}")
    else:
        lines.append("• Not in any scheduled bundle yet.")

    suggested: List[str] = []
    if not bundles:
        suggested.append("Create a bundle for this vulnerability")
    if vuln.kev_listed:
        suggested.append("View all KEV vulnerabilities")

    return AgentChatResponse(
        response="\n".join(lines),
        actions_taken=["Queried vulnerability database", "Checked affected assets"],
        suggested_actions=suggested,
    )


async def handle_create_rule(message: str, tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    """Parse NLP and create the rule."""
    # Reuse the same parse logic from rules.py inline
    text = message.strip()

    result: Dict[str, Any] = {
        "name": text[:60],
        "description": text,
        "scope_type": "global",
        "scope_value": None,
        "scope_tags": None,
        "condition_type": "always",
        "condition_config": {},
        "action_type": "warn",
        "action_config": {},
        "priority": 50,
    }

    # Try Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic as _anthropic  # lazy import
            client = _anthropic.Anthropic(api_key=anthropic_key)
            system_prompt = (
                "You are a deployment rules parser for a patch management system. "
                "Parse the user's intent into a structured rule JSON.\n"
                "Available scope_type values: global, tag, environment, asset_group, asset\n"
                "Available condition_type values: time_window, calendar, risk_threshold, always\n"
                "Available action_type values: block, require_approval, escalate_risk, notify, warn\n"
                "For time_window conditions use condition_config with type=day_of_week|month_end|quarter_end.\n"
                'Respond ONLY with valid JSON matching this schema (no markdown):\n'
                '{"name":str,"description":str,"scope_type":str,"scope_value":str|null,'
                '"scope_tags":list|null,"condition_type":str,"condition_config":dict,'
                '"action_type":str,"action_config":dict,"priority":int}'
            )
            msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            import json as _json
            parsed = _json.loads(msg.content[0].text.strip())
            parsed.setdefault("scope_value", None)
            parsed.setdefault("scope_tags", None)
            parsed.setdefault("action_config", {})
            result = parsed
        except Exception:
            pass  # fall through to pattern match

    if result.get("condition_type") == "always":
        lower = text.lower()
        if "friday" in lower:
            result["condition_type"] = "time_window"
            result["condition_config"] = {"type": "day_of_week", "days": ["Friday"], "after_hour": 15}
            result["action_type"] = "block"
            result["name"] = "Block deployments on Fridays"
        elif "month" in lower and "end" in lower:
            result["condition_type"] = "time_window"
            result["condition_config"] = {"type": "month_end", "days_before": 3}
            result["action_type"] = "warn"
            result["name"] = "Warn at month-end"
        if "production" in lower or "prod" in lower:
            result["scope_type"] = "environment"
            result["scope_value"] = "production"

    rule = DeploymentRule(
        tenant_id=tenant.id,
        name=result.get("name", text[:60]),
        description=result.get("description", text),
        scope_type=result.get("scope_type", "global"),
        scope_value=result.get("scope_value"),
        scope_tags=result.get("scope_tags"),
        condition_type=result.get("condition_type", "always"),
        condition_config=result.get("condition_config", {}),
        action_type=result.get("action_type", "warn"),
        action_config=result.get("action_config", {}),
        priority=result.get("priority", 50),
        enabled=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return AgentChatResponse(
        response=f"✅ Created rule: **{rule.name}**\n"
                 f"• Action: {rule.action_type} | Scope: {rule.scope_type}\n"
                 f"• Condition: {rule.condition_type}",
        actions_taken=[f"Created deployment rule '{rule.name}'"],
        suggested_actions=["View all rules", "Test rule evaluation"],
    )


async def handle_show_windows(tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    stmt = select(MaintenanceWindow).where(
        MaintenanceWindow.tenant_id == tenant.id
    ).order_by(MaintenanceWindow.start_time).limit(10)
    windows = (await db.execute(stmt)).scalars().all()

    if not windows:
        return AgentChatResponse(
            response="No maintenance windows found. Create one to start scheduling bundles.",
            actions_taken=["Queried maintenance windows"],
            suggested_actions=["Create a maintenance window"],
        )

    now = datetime.now(timezone.utc)
    lines = [f"**{len(windows)} maintenance window(s):**\n"]
    for w in windows:
        upcoming = w.start_time > now
        label = "upcoming" if upcoming else "past"
        start = w.start_time.strftime("%Y-%m-%d %H:%M UTC")
        env = f" [{w.environment}]" if w.environment else ""
        lines.append(f"  • {w.name}{env} — {start} ({label})")

    return AgentChatResponse(
        response="\n".join(lines),
        actions_taken=["Queried maintenance windows"],
        suggested_actions=["Create a maintenance window", "View schedule"],
    )


async def handle_add_window(message: str, tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    spec = extract_window_spec(message)
    now = datetime.now(timezone.utc)

    if spec and "day_num" in spec:
        days_ahead = (spec["day_num"] - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        start = now.replace(hour=spec.get("hour", 2), minute=spec.get("minute", 0), second=0, microsecond=0)
        start = start + timedelta(days=days_ahead)
    else:
        # Default: next Saturday 2am
        days_ahead = (5 - now.weekday()) % 7 or 7
        start = now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)

    end = start + timedelta(hours=4)

    day_label = spec.get("day", "Saturday") if spec else "Saturday"
    hour_label = start.strftime("%H:%M")
    name = f"{day_label} {hour_label} Maintenance Window"

    window = MaintenanceWindow(
        tenant_id=tenant.id,
        name=name,
        type="scheduled",
        start_time=start,
        end_time=end,
        environment=None,
    )
    db.add(window)
    await db.commit()
    await db.refresh(window)

    return AgentChatResponse(
        response=f"✅ Created maintenance window: **{window.name}**\n"
                 f"• Starts: {start.strftime('%Y-%m-%d %H:%M UTC')}\n"
                 f"• Ends: {end.strftime('%Y-%m-%d %H:%M UTC')} (4h window)",
        actions_taken=[f"Created maintenance window '{window.name}'"],
        suggested_actions=["View maintenance windows", "Schedule a bundle"],
    )


async def handle_show_goals(tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    stmt = select(Goal).where(Goal.tenant_id == tenant.id).limit(10)
    goals = (await db.execute(stmt)).scalars().all()

    if not goals:
        return AgentChatResponse(
            response="No goals found. Create a goal to start optimizing your patch plan.",
            actions_taken=["Queried goals"],
            suggested_actions=["Create a goal"],
        )

    lines = [f"**{len(goals)} goal(s):**\n"]
    for g in goals:
        target = g.target_completion_date.strftime("%Y-%m-%d") if g.target_completion_date else "no deadline"
        status = g.status or "unknown"
        risk = f"risk target: {g.target_risk_score}" if g.target_risk_score else ""
        lines.append(f"  • {g.name} [{status}] — {target} {risk}")

    return AgentChatResponse(
        response="\n".join(lines),
        actions_taken=["Queried goals"],
        suggested_actions=["Create a goal", "Run optimizer"],
    )


async def handle_show_bundles(tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    stmt = select(Bundle).where(
        Bundle.tenant_id == tenant.id
    ).order_by(Bundle.scheduled_for.desc().nullslast()).limit(10)
    bundles = (await db.execute(stmt)).scalars().all()

    if not bundles:
        return AgentChatResponse(
            response="No bundles found. Create a goal and run the optimizer to generate bundles.",
            actions_taken=["Queried bundles"],
            suggested_actions=["Create a goal", "View goals"],
        )

    draft_count = sum(1 for b in bundles if b.status == "draft")
    lines = [f"**{len(bundles)} bundle(s)** ({draft_count} draft / pending review):\n"]
    for b in bundles:
        scheduled = b.scheduled_for.strftime("%Y-%m-%d") if b.scheduled_for else "unscheduled"
        lines.append(f"  • [{b.status.upper()}] {b.name} — {scheduled}")

    suggested: List[str] = []
    if draft_count:
        suggested.append("Approve pending bundles")

    return AgentChatResponse(
        response="\n".join(lines),
        actions_taken=["Queried bundles"],
        suggested_actions=suggested or ["View schedule"],
    )


async def handle_approve_bundle(message: str, tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    bundle_hint = extract_bundle_name(message)

    if bundle_hint:
        # Fuzzy: try ilike match
        stmt = select(Bundle).where(
            and_(
                Bundle.tenant_id == tenant.id,
                Bundle.status.in_(["draft", "scheduled"]),
                Bundle.name.ilike(f"%{bundle_hint}%"),
            )
        ).limit(1)
        bundle = (await db.execute(stmt)).scalar_one_or_none()
    else:
        # First pending bundle
        stmt = select(Bundle).where(
            and_(Bundle.tenant_id == tenant.id, Bundle.status.in_(["draft", "scheduled"]))
        ).order_by(Bundle.scheduled_for).limit(1)
        bundle = (await db.execute(stmt)).scalar_one_or_none()

    if not bundle:
        return AgentChatResponse(
            response="No pending bundles found to approve. All bundles may already be approved or there are none.",
            actions_taken=["Queried bundles"],
            suggested_actions=["View bundles"],
        )

    bundle.status = "approved"
    bundle.approved_by = "AI Agent"
    bundle.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return AgentChatResponse(
        response=f"✅ Approved bundle: **{bundle.name}**\nStatus updated to approved. Ready for deployment.",
        actions_taken=[f"Approved bundle '{bundle.name}'"],
        suggested_actions=["View all bundles", "Execute bundle"],
    )


async def handle_risk_score(tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    actions_taken = ["Aggregated vulnerability data", "Checked goal status"]

    total_stmt = select(func.count()).select_from(Vulnerability).join(
        AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id
    ).join(Asset, Asset.id == AssetVulnerability.asset_id).where(
        Asset.tenant_id == tenant.id
    )
    total = (await db.execute(total_stmt)).scalar() or 0

    kev_stmt = select(func.count()).select_from(Vulnerability).join(
        AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id
    ).join(Asset, Asset.id == AssetVulnerability.asset_id).where(
        and_(Asset.tenant_id == tenant.id, Vulnerability.kev_listed == True)  # noqa: E712
    )
    kev_count = (await db.execute(kev_stmt)).scalar() or 0

    critical_stmt = select(func.count()).select_from(Vulnerability).join(
        AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id
    ).join(Asset, Asset.id == AssetVulnerability.asset_id).where(
        and_(Asset.tenant_id == tenant.id, Vulnerability.severity == "CRITICAL")
    )
    critical_count = (await db.execute(critical_stmt)).scalar() or 0

    bundle_stmt = select(func.count()).select_from(Bundle).where(
        and_(Bundle.tenant_id == tenant.id, Bundle.status.in_(["approved", "scheduled"]))
    )
    bundles_scheduled = (await db.execute(bundle_stmt)).scalar() or 0

    goals_stmt = select(func.count()).select_from(Goal).where(
        and_(Goal.tenant_id == tenant.id, Goal.status.in_(["active", "ACTIVE"]))
    )
    goals_active = (await db.execute(goals_stmt)).scalar() or 0

    # Simple heuristic posture rating
    if kev_count == 0 and critical_count == 0:
        posture = "🟢 Strong"
    elif kev_count <= 5 and critical_count <= 10:
        posture = "🟡 Moderate"
    else:
        posture = "🔴 Needs attention"

    lines = [
        f"**Security Posture: {posture}**\n",
        f"• Total vulnerabilities tracked: {total}",
        f"• KEV (actively exploited): {kev_count}",
        f"• Critical severity: {critical_count}",
        f"• Bundles scheduled/approved: {bundles_scheduled}",
        f"• Active goals: {goals_active}",
    ]
    if kev_count:
        lines.append(f"\n⚠️ Priority: Address the {kev_count} KEV vulnerabilities first — they're actively exploited in the wild.")

    suggested: List[str] = []
    if kev_count:
        suggested.append("Show me critical KEV vulnerabilities")
    if bundles_scheduled == 0 and total > 0:
        suggested.append("Create a goal to start patching")

    return AgentChatResponse(
        response="\n".join(lines),
        actions_taken=actions_taken,
        suggested_actions=suggested,
    )


async def handle_fallback(message: str, tenant: Tenant, db: AsyncSession) -> AgentChatResponse:
    """Use Anthropic Claude if configured, otherwise return capability list."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        try:
            import anthropic as _anthropic  # lazy import

            # Gather live context
            vuln_count_stmt = select(func.count()).select_from(Vulnerability).join(
                AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id
            ).join(Asset, Asset.id == AssetVulnerability.asset_id).where(
                Asset.tenant_id == tenant.id
            )
            vuln_count = (await db.execute(vuln_count_stmt)).scalar() or 0

            kev_count_stmt = select(func.count()).select_from(Vulnerability).join(
                AssetVulnerability, AssetVulnerability.vulnerability_id == Vulnerability.id
            ).join(Asset, Asset.id == AssetVulnerability.asset_id).where(
                and_(Asset.tenant_id == tenant.id, Vulnerability.kev_listed == True)  # noqa: E712
            )
            kev_count = (await db.execute(kev_count_stmt)).scalar() or 0

            bundle_count_stmt = select(func.count()).select_from(Bundle).where(
                Bundle.tenant_id == tenant.id
            )
            bundle_count = (await db.execute(bundle_count_stmt)).scalar() or 0

            system_prompt = (
                "You are Glasswatch's AI security assistant. You help security teams manage patch operations.\n\n"
                f"Current environment context:\n"
                f"- Total tracked vulnerabilities: {vuln_count}\n"
                f"- KEV (actively exploited) vulnerabilities: {kev_count}\n"
                f"- Total patch bundles: {bundle_count}\n\n"
                "You can help with: vulnerability analysis, patch prioritization, goal setting, risk assessment, "
                "maintenance window planning, and compliance guidance. Be concise and actionable."
            )

            client = _anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
            )
            return AgentChatResponse(
                response=msg.content[0].text,
                actions_taken=["Consulted Claude with live context"],
                suggested_actions=[
                    "What needs my attention right now?",
                    "Show me critical KEV vulnerabilities",
                ],
            )
        except Exception:
            pass  # fall through to capability list

    capabilities = [
        '"What needs my attention right now?" — KEV + overdue bundle summary',
        '"Show me critical KEV vulnerabilities" — risk-sorted CVE list',
        '"Create a rule blocking Friday deployments" — creates the rule',
        '"Show maintenance windows" — list scheduled windows',
        '"Add maintenance window on Saturday at 2am" — creates a window',
        '"Show goals" — goal progress summary',
        '"Find fixes for CVE-XXXX-XXXXX" — CVE detail + affected assets',
        '"Show bundles" / "Pending approvals" — bundle list',
        '"Approve bundle [name]" — approves a draft bundle',
        '"How are we doing?" — executive risk posture summary',
    ]

    return AgentChatResponse(
        response="I can help with:\n\n" + "\n".join(f"• {c}" for c in capabilities),
        actions_taken=[],
        suggested_actions=[
            "What needs my attention right now?",
            "Show me critical KEV vulnerabilities",
            "How are we doing?",
        ],
    )


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """
    AI agent chat endpoint.

    Parses intent from the user message, pulls live data from the database,
    optionally takes actions, and returns a natural language response.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    intent = detect_intent(message)

    if intent == "attention":
        return await handle_attention(tenant, db)
    elif intent == "cve_lookup":
        return await handle_cve_lookup(message, tenant, db)
    elif intent == "create_rule":
        return await handle_create_rule(message, tenant, db)
    elif intent == "show_windows":
        return await handle_show_windows(tenant, db)
    elif intent == "add_window":
        return await handle_add_window(message, tenant, db)
    elif intent == "show_goals":
        return await handle_show_goals(tenant, db)
    elif intent == "show_bundles":
        return await handle_show_bundles(tenant, db)
    elif intent == "approve_bundle":
        return await handle_approve_bundle(message, tenant, db)
    elif intent == "risk_score":
        return await handle_risk_score(tenant, db)
    else:
        return await handle_fallback(message, tenant, db)
