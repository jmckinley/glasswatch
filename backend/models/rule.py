"""
Deployment Rule model - represents governance rules for patch deployments.

Enforces policies based on time windows, tags, risk scores, and other conditions.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class DeploymentRule(Base):
    """
    Rule for controlling when and how patch deployments can occur.
    
    Supports scope filtering (by tag, environment, asset), condition evaluation
    (time windows, risk thresholds), and various actions (block, warn, require approval).
    """
    __tablename__ = "deployment_rules"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Identity
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Scope — what this rule applies to
    scope_type = Column(String(50), nullable=False)  # "global", "tag", "environment", "asset_group", "asset"
    scope_value = Column(String(200), nullable=True)  # tag name, env name, asset_group, or asset_id. null for global.
    scope_tags = Column(JSON, nullable=True)  # For complex scope: ["system:financial", "compliance:pci-dss"]
    
    # Condition — when this rule triggers
    condition_type = Column(String(50), nullable=False)
    # Types: "time_window", "calendar", "risk_threshold", "change_velocity", "dependency", "always"
    condition_config = Column(JSON, nullable=False)
    # Examples:
    # time_window: {"type": "month_end", "days_before": 3}
    # time_window: {"type": "day_of_week", "days": ["friday"], "after_hour": 15}
    # time_window: {"type": "quarter_end", "days_before": 5}
    # calendar: {"type": "holiday", "calendars": ["US"]}
    # risk_threshold: {"min_score": 8.0}
    # change_velocity: {"max_changes_per_day": 3}
    # always: {} (rule always applies, used for permanent policies)
    
    # Action — what happens when condition is met
    action_type = Column(String(50), nullable=False)
    # Types: "block", "require_approval", "escalate_risk", "notify", "warn"
    action_config = Column(JSON, nullable=False)
    # Examples:
    # block: {"message": "No deployments during month-end close"}
    # require_approval: {"min_approvers": 2, "approval_roles": ["manager", "admin"]}
    # escalate_risk: {"score_multiplier": 1.2, "reason": "Financial system"}
    # notify: {"channels": ["slack", "email"], "message": "Deploying to financial system"}
    # warn: {"message": "This deployment window overlaps with quarter-end"}
    
    # Metadata
    priority = Column(Integer, default=0)  # Higher = evaluated first. Blocks override warns.
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Shipped with system
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="deployment_rules")
    
    def __repr__(self):
        return f"<DeploymentRule {self.name} ({self.scope_type}/{self.action_type})>"
