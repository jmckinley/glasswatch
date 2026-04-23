"""
Deployment Rules API endpoints.

Provides CRUD operations for deployment rules and rule evaluation.
"""
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from uuid import UUID

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.rule import DeploymentRule
from backend.models.asset import Asset
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.services.rule_engine import rule_engine, RuleMatch as RuleMatchDataclass


router = APIRouter()


# Pydantic schemas
class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scope_type: str  # "global", "tag", "environment", "asset_group", "asset"
    scope_value: Optional[str] = None
    scope_tags: Optional[List[str]] = None
    condition_type: str  # "time_window", "calendar", "risk_threshold", "always"
    condition_config: Dict[str, Any]
    action_type: str  # "block", "require_approval", "escalate_risk", "notify", "warn"
    action_config: Dict[str, Any]
    priority: int = 0
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope_type: Optional[str] = None
    scope_value: Optional[str] = None
    scope_tags: Optional[List[str]] = None
    condition_type: Optional[str] = None
    condition_config: Optional[Dict[str, Any]] = None
    action_type: Optional[str] = None
    action_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class RuleEvaluateRequest(BaseModel):
    asset_ids: Optional[List[UUID]] = None
    asset_tags: Optional[List[str]] = None
    environment: Optional[str] = None
    window_id: Optional[UUID] = None
    bundle_id: Optional[UUID] = None


class RuleMatch(BaseModel):
    rule_id: str
    rule_name: str
    action_type: str
    action_config: Dict[str, Any]
    message: str
    priority: int


class RuleEvaluationResult(BaseModel):
    verdict: str  # "allow", "warn", "block"
    matches: List[RuleMatch]
    evaluated_count: int
    timestamp: datetime


class RuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    scope_type: str
    scope_value: Optional[str]
    scope_tags: Optional[List[str]]
    condition_type: str
    condition_config: Dict[str, Any]
    action_type: str
    action_config: Dict[str, Any]
    priority: int
    enabled: bool
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=Dict[str, Any])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List deployment rules for tenant.
    
    Returns rules with filtering capabilities.
    """
    # Build base query
    conditions = [DeploymentRule.tenant_id == tenant.id]
    
    if scope_type:
        conditions.append(DeploymentRule.scope_type == scope_type)
    
    if enabled is not None:
        conditions.append(DeploymentRule.enabled == enabled)
    
    stmt = (
        select(DeploymentRule)
        .where(and_(*conditions))
        .order_by(DeploymentRule.priority.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    # Get total count
    count_stmt = select(func.count(DeploymentRule.id)).where(and_(*conditions))
    total = await db.scalar(count_stmt)
    
    return {
        "rules": [RuleResponse.model_validate(rule) for rule in rules],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/defaults", response_model=List[RuleResponse])
async def list_default_rules(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> List[RuleResponse]:
    """
    List all default rules (for documentation/reference).
    
    Returns rules marked as is_default=True.
    """
    stmt = (
        select(DeploymentRule)
        .where(
            and_(
                DeploymentRule.tenant_id == tenant.id,
                DeploymentRule.is_default == True,
            )
        )
        .order_by(DeploymentRule.priority.desc())
    )
    
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    return [RuleResponse.model_validate(rule) for rule in rules]


@router.post("", response_model=RuleResponse)
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleResponse:
    """
    Create a new deployment rule.
    """
    rule = DeploymentRule(
        tenant_id=tenant.id,
        name=rule_data.name,
        description=rule_data.description,
        scope_type=rule_data.scope_type,
        scope_value=rule_data.scope_value,
        scope_tags=rule_data.scope_tags,
        condition_type=rule_data.condition_type,
        condition_config=rule_data.condition_config,
        action_type=rule_data.action_type,
        action_config=rule_data.action_config,
        priority=rule_data.priority,
        enabled=rule_data.enabled,
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return RuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleResponse:
    """Get rule detail."""
    stmt = select(DeploymentRule).where(
        and_(
            DeploymentRule.id == rule_id,
            DeploymentRule.tenant_id == tenant.id,
        )
    )
    rule = await db.scalar(stmt)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return RuleResponse.model_validate(rule)


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleResponse:
    """
    Update an existing rule.
    """
    stmt = select(DeploymentRule).where(
        and_(
            DeploymentRule.id == rule_id,
            DeploymentRule.tenant_id == tenant.id,
        )
    )
    rule = await db.scalar(stmt)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update fields
    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(rule)
    
    return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Delete a rule.
    
    Cannot delete default rules (use disable instead).
    """
    stmt = select(DeploymentRule).where(
        and_(
            DeploymentRule.id == rule_id,
            DeploymentRule.tenant_id == tenant.id,
        )
    )
    rule = await db.scalar(stmt)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if rule.is_default:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default rules. Use PATCH to disable instead."
        )
    
    await db.delete(rule)
    await db.commit()
    
    return {"status": "deleted", "id": str(rule_id)}


@router.post("/parse-nlp")
async def parse_rule_from_natural_language(
    request: dict,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Parse a natural language description into a structured rule.

    Tries Anthropic API first if ANTHROPIC_API_KEY is set,
    falls back to pattern matching.
    """
    text: str = (request.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text field is required")

    # Default / fallback result
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
        "confidence": 0.5,
        "source": "pattern",
    }

    # --- Try Anthropic API first ---
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            anthropic_module = None
            try:
                import anthropic as _anthropic
                anthropic_module = _anthropic
            except ImportError:
                pass

            if anthropic_module is not None:
                client = anthropic_module.Anthropic(api_key=anthropic_key)
                system_prompt = (
                    "You parse natural-language deployment rule descriptions into JSON.\n"
                    "Available scope_type values: global, tag, environment, asset_group, asset\n"
                    "Available condition_type values: time_window, calendar, risk_threshold, always\n"
                    "Available action_type values: block, require_approval, escalate_risk, notify, warn\n"
                    "For time_window conditions use condition_config with type=day_of_week|month_end|quarter_end.\n"
                    "Respond ONLY with valid JSON matching this schema (no markdown):\n"
                    '{"name":str,"description":str,"scope_type":str,"scope_value":str|null,'
                    '"scope_tags":list|null,"condition_type":str,"condition_config":dict,'
                    '"action_type":str,"action_config":dict,"priority":int,"confidence":float}'
                )
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": text}],
                )
                import json as _json
                raw = message.content[0].text.strip()
                parsed = _json.loads(raw)
                parsed["source"] = "ai"
                parsed.setdefault("scope_value", None)
                parsed.setdefault("scope_tags", None)
                parsed.setdefault("action_config", {})
                return parsed
        except Exception:
            pass  # Fall through to pattern matching

    # --- Pattern matching fallback ---
    lower = text.lower()

    # Scope
    if "production" in lower or "prod" in lower:
        result["scope_type"] = "environment"
        result["scope_value"] = "production"

    # Condition
    if "friday" in lower:
        result["condition_type"] = "time_window"
        result["condition_config"] = {"type": "day_of_week", "days": ["Friday"], "after_hour": 15}
        result["action_type"] = "block"
        result["confidence"] = 0.85
        result["name"] = "Block deployments on Fridays"
    elif "month" in lower and "end" in lower:
        result["condition_type"] = "time_window"
        result["condition_config"] = {"type": "month_end", "days_before": 3}
        result["action_type"] = "warn"
        result["confidence"] = 0.85
        result["name"] = "Warn at month-end"

    return result


@router.post("/evaluate", response_model=RuleEvaluationResult)
async def evaluate_rules(
    request: RuleEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleEvaluationResult:
    """
    Dry-run evaluation of deployment rules.
    
    Returns which rules would trigger for the given assets/tags/environment.
    """
    # Load assets if IDs provided
    assets = None
    if request.asset_ids:
        stmt = select(Asset).where(
            and_(
                Asset.id.in_(request.asset_ids),
                Asset.tenant_id == tenant.id,
            )
        )
        result = await db.execute(stmt)
        assets = result.scalars().all()
    
    # Evaluate rules
    result = await rule_engine.evaluate_deployment(
        db=db,
        tenant_id=str(tenant.id),
        assets=assets,
        asset_tags=request.asset_tags,
        environment=request.environment,
    )
    
    # Convert to response model
    return RuleEvaluationResult(
        verdict=result.verdict,
        matches=[
            RuleMatch(
                rule_id=m.rule_id,
                rule_name=m.rule_name,
                action_type=m.action_type,
                action_config=m.action_config,
                message=m.message,
                priority=m.priority,
            )
            for m in result.matches
        ],
        evaluated_count=result.evaluated_count,
        timestamp=result.timestamp,
    )
