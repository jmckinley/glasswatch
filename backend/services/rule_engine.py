"""
Rule Engine Service - Evaluates deployment rules and enforces governance policies.

Handles time-based rules, tag-based scope matching, and action determination.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import calendar

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.rule import DeploymentRule
from backend.models.asset import Asset


@dataclass
class RuleMatch:
    """A rule that matched the evaluation criteria."""
    rule_id: str
    rule_name: str
    action_type: str  # block, warn, require_approval, etc.
    action_config: dict
    message: str
    priority: int


@dataclass
class RuleEvaluationResult:
    """Result of evaluating deployment rules."""
    verdict: str  # "allow", "warn", "block"
    matches: List[RuleMatch]
    evaluated_count: int
    timestamp: datetime


class RuleEngine:
    """
    Deployment rule evaluation engine.
    
    Evaluates rules based on scope, conditions, and actions to determine
    whether deployments should be allowed, warned, or blocked.
    """
    
    async def evaluate_deployment(
        self,
        db: AsyncSession,
        tenant_id: str,
        bundle=None,
        assets: Optional[List[Asset]] = None,
        asset_tags: Optional[List[str]] = None,
        environment: Optional[str] = None,
        target_window=None,
    ) -> RuleEvaluationResult:
        """
        Evaluate all applicable rules for a proposed deployment.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            bundle: Optional bundle being deployed
            assets: Optional list of assets involved
            asset_tags: Optional list of tags from assets
            environment: Optional environment (production, staging, etc.)
            target_window: Optional maintenance window
            
        Returns:
            RuleEvaluationResult with verdict and matched rules
        """
        # Load all enabled rules for tenant, ordered by priority desc
        stmt = select(DeploymentRule).where(
            and_(
                DeploymentRule.tenant_id == tenant_id,
                DeploymentRule.enabled == True,
            )
        ).order_by(DeploymentRule.priority.desc())
        
        result = await db.execute(stmt)
        rules = result.scalars().all()
        
        # Evaluate each rule
        matches = []
        for rule in rules:
            if self._matches_scope(rule, assets, asset_tags, environment):
                if self._matches_condition(rule):
                    message = self._get_action_message(rule)
                    matches.append(RuleMatch(
                        rule_id=str(rule.id),
                        rule_name=rule.name,
                        action_type=rule.action_type,
                        action_config=rule.action_config,
                        message=message,
                        priority=rule.priority,
                    ))
        
        # Determine overall verdict
        verdict = self._determine_verdict(matches)
        
        return RuleEvaluationResult(
            verdict=verdict,
            matches=matches,
            evaluated_count=len(rules),
            timestamp=datetime.now(timezone.utc),
        )
    
    def _matches_scope(
        self,
        rule: DeploymentRule,
        assets: Optional[List[Asset]],
        asset_tags: Optional[List[str]],
        environment: Optional[str],
    ) -> bool:
        """Check if rule scope matches the given context."""
        if rule.scope_type == "global":
            return True
        
        if rule.scope_type == "environment" and environment:
            return rule.scope_value == environment
        
        if rule.scope_type == "tag" and asset_tags:
            # Check if any asset has the target tag
            if rule.scope_tags:
                # Complex scope: must match all tags in scope_tags
                return all(tag in asset_tags for tag in rule.scope_tags)
            elif rule.scope_value:
                # Simple scope: match single tag
                return rule.scope_value in asset_tags
        
        if rule.scope_type == "asset" and assets:
            # Check if any asset ID matches
            asset_ids = [str(a.id) for a in assets]
            return rule.scope_value in asset_ids
        
        return False
    
    def _matches_condition(self, rule: DeploymentRule) -> bool:
        """Evaluate rule condition against current context."""
        if rule.condition_type == "always":
            return True
        
        if rule.condition_type == "time_window":
            return self._check_time_window(rule.condition_config)
        
        if rule.condition_type == "calendar":
            return self._check_calendar(rule.condition_config)
        
        # Other condition types can be added here (risk_threshold, change_velocity, etc.)
        return False
    
    def _check_time_window(self, config: Dict[str, Any]) -> bool:
        """Check if current time matches the configured window."""
        now = datetime.now(timezone.utc)
        window_type = config.get("type")
        
        if window_type == "month_end":
            return self._is_near_month_end(now, config.get("days_before", 3))
        
        if window_type == "quarter_end":
            return self._is_near_quarter_end(now, config.get("days_before", 5))
        
        if window_type == "day_of_week":
            return self._matches_day_of_week(now, config)
        
        return False
    
    def _check_calendar(self, config: Dict[str, Any]) -> bool:
        """Check if current date matches calendar condition (e.g., holidays)."""
        # This is a simplified implementation
        # In production, you'd integrate with a holiday calendar API
        calendar_type = config.get("type")
        
        if calendar_type == "holiday":
            # Placeholder: would check against actual holiday calendar
            # For now, return False (not a holiday)
            return False
        
        return False
    
    def _is_near_month_end(self, dt: datetime, days_before: int) -> bool:
        """Check if date is within N days of month end."""
        # Get last day of month
        last_day = calendar.monthrange(dt.year, dt.month)[1]
        days_until_end = last_day - dt.day
        return days_until_end < days_before
    
    def _is_near_quarter_end(self, dt: datetime, days_before: int) -> bool:
        """Check if date is within N days of quarter end."""
        # Quarter ends: March 31, June 30, September 30, December 31
        quarter_end_months = [3, 6, 9, 12]
        
        if dt.month not in quarter_end_months:
            return False
        
        # Check if we're in the last N days of the quarter end month
        last_day = calendar.monthrange(dt.year, dt.month)[1]
        days_until_end = last_day - dt.day
        return days_until_end < days_before
    
    def _matches_day_of_week(self, dt: datetime, config: Dict[str, Any]) -> bool:
        """Check if current day/time matches the configured pattern."""
        days = config.get("days", [])
        after_hour = config.get("after_hour")
        
        # Map day names to weekday numbers (0=Monday, 6=Sunday)
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        current_day = dt.weekday()
        day_names_lower = [d.lower() for d in days]
        target_days = [day_map.get(d, -1) for d in day_names_lower if d in day_map]
        
        if current_day not in target_days:
            return False
        
        if after_hour is not None:
            return dt.hour >= after_hour
        
        return True
    
    def _get_action_message(self, rule: DeploymentRule) -> str:
        """Extract or construct the message for the action."""
        return rule.action_config.get("message", f"Rule {rule.name} triggered")
    
    def _determine_verdict(self, matches: List[RuleMatch]) -> str:
        """Determine overall verdict from matched rules."""
        if not matches:
            return "allow"
        
        # Blocks override everything
        if any(m.action_type == "block" for m in matches):
            return "block"
        
        # Warnings if present
        if any(m.action_type in ("warn", "require_approval", "escalate_risk", "notify") for m in matches):
            return "warn"
        
        return "allow"


# Singleton instance
rule_engine = RuleEngine()
