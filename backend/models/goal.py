"""
Goal models - the secret sauce of Glasswatch.

Goals allow users to express objectives like "Be Glasswing-ready by July 1"
and the system optimizes a patch plan to achieve it.
"""
from datetime import datetime, timezone
from typing import Optional, Dict
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Index, 
    JSON, Text, Integer, Numeric, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from backend.db.base_class import Base


class Goal(Base):
    """
    Basic patch goal - defines what the user wants to achieve.
    
    Examples:
    - "Patch all KEV vulnerabilities within 30 days"
    - "Minimize risk score to below 200 by end of quarter"
    - "Be ready for Glasswing disclosure by July 1"
    """
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goal_tenant_id", "tenant_id"),
        Index("ix_goal_status", "status"),
        Index("ix_goal_target_date", "target_completion_date"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Goal definition
    name = Column(String(255), nullable=False)  # "Q2 Security Hardening"
    description = Column(Text)  # Detailed description
    goal_type = Column(String(50), nullable=False)  # TIME_BASED, RISK_REDUCTION, KEV_ELIMINATION, COMPLIANCE
    
    # Target state
    target_completion_date = Column(DateTime(timezone=True))  # When to achieve by
    target_risk_score = Column(Integer)  # Target total risk score
    target_vulnerability_count = Column(Integer)  # Target number of open vulns
    
    # Scope and filters
    asset_scope = Column(JSON)  # {"environments": ["production"], "types": ["server"]}
    vulnerability_scope = Column(JSON)  # {"severity": ["CRITICAL", "HIGH"], "kev_only": true}
    excluded_assets = Column(ARRAY(UUID))  # Specific assets to exclude
    excluded_vulnerabilities = Column(ARRAY(String))  # Specific CVEs to exclude
    
    # Constraints
    risk_tolerance = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH
    max_patches_per_window = Column(Integer)  # Max patches in single maintenance
    max_downtime_minutes = Column(Integer)  # Max allowed downtime per window
    required_testing_hours = Column(Integer, default=24)  # Hours between test and prod
    
    # Maintenance windows
    maintenance_windows = Column(JSON)  # [{"day": "tuesday", "start": "02:00", "duration": 240}]
    blackout_dates = Column(JSON)  # ["2024-12-24", "2024-12-25"] - no patching
    
    # Status tracking
    status = Column(String(50), default="DRAFT")  # DRAFT, ACTIVE, PAUSED, COMPLETED, FAILED
    
    # Planning metadata
    last_plan_generated_at = Column(DateTime(timezone=True))
    plan_version = Column(Integer, default=0)
    optimization_runtime_ms = Column(Integer)  # How long planning took
    
    # Results
    current_risk_score = Column(Integer)  # Current total risk
    current_vulnerability_count = Column(Integer)  # Current open vulns
    patches_completed = Column(Integer, default=0)
    patches_remaining = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    activated_at = Column(DateTime(timezone=True))  # When goal was activated
    completed_at = Column(DateTime(timezone=True))  # When goal was achieved
    
    # Relationships
    tenant = relationship("Tenant", back_populates="goals")
    bundles = relationship("Bundle", back_populates="goal")
    
    # ── API compatibility properties ────────────────────────────────
    # The API layer references attribute names that differ from the DB columns.

    @property
    def type(self):
        return self.goal_type

    @property
    def target_date(self):
        return self.target_completion_date

    @property
    def estimated_completion_date(self):
        return self.target_completion_date

    @property
    def target_metric(self):
        return self.goal_type

    @property
    def target_value(self):
        if self.target_risk_score is not None:
            return self.target_risk_score
        if self.target_vulnerability_count is not None:
            return self.target_vulnerability_count
        return 0

    @property
    def risk_score_current(self):
        return self.current_risk_score or 0

    @property
    def risk_score_initial(self):
        return (self.current_risk_score or 0) + (self.patches_completed or 0) * 3

    @property
    def vulnerabilities_total(self):
        return self.current_vulnerability_count or 0

    @property
    def vulnerabilities_addressed(self):
        return self.patches_completed or 0

    @property
    def max_downtime_hours(self):
        if self.max_downtime_minutes:
            return self.max_downtime_minutes / 60
        return None

    @property
    def max_vulns_per_window(self):
        return self.max_patches_per_window

    @property
    def min_patch_weather_score(self):
        return 0.0

    @property
    def require_vendor_approval(self):
        return False

    @hybrid_property
    def active(self):
        """Whether the goal is currently active."""
        return self.status in ("active", "ACTIVE")

    @active.expression
    def active(cls):
        return cls.status.in_(["active", "ACTIVE"])

    def __repr__(self):
        return f"<Goal {self.name}: {self.goal_type}>"
    
    @property
    def is_time_constrained(self) -> bool:
        """Check if goal has a deadline."""
        return self.target_completion_date is not None
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days until target completion."""
        if self.target_completion_date:
            return (self.target_completion_date - datetime.now(timezone.utc)).days
        return None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.patches_remaining and self.patches_completed:
            total = self.patches_completed + self.patches_remaining
            return (self.patches_completed / total) * 100
        return 0.0


class EnhancedGoal(Base):
    """
    Enhanced goal with business impact modeling and advanced constraints.
    
    This is where Glasswatch really shines - incorporating business context
    into technical patch decisions.
    """
    __tablename__ = "enhanced_goals"
    __table_args__ = (
        Index("ix_enhanced_goal_goal_id", "goal_id"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    
    # Business impact modeling
    business_impact_per_hour = Column(Numeric(12, 2))  # $ per hour of downtime
    regulatory_deadline = Column(DateTime(timezone=True))  # Compliance deadline
    compliance_frameworks = Column(ARRAY(String))  # ["PCI-DSS", "HIPAA", "SOX"]
    
    # Asset tiering for granular control
    tier_0_assets = Column(ARRAY(UUID))  # Mission critical - 24h SLA
    tier_1_assets = Column(ARRAY(UUID))  # Business critical - 7d SLA  
    tier_2_assets = Column(ARRAY(UUID))  # Standard - 30d SLA
    tier_3_assets = Column(ARRAY(UUID))  # Non-critical - 90d SLA
    
    # Risk profiles (our special sauce)
    risk_profile = Column(String(50), default="BALANCED")  # CONSERVATIVE, BALANCED, AGGRESSIVE
    
    # Advanced scheduling preferences
    prefer_automated_deployment = Column(Boolean, default=False)
    require_change_approval = Column(Boolean, default=True)
    batch_similar_systems = Column(Boolean, default=True)
    
    # Canary deployment settings
    enable_canary_deployment = Column(Boolean, default=False)
    canary_percentage = Column(Integer, default=10)  # Deploy to 10% first
    canary_success_hours = Column(Integer, default=24)  # Wait 24h before full deploy
    auto_rollback_on_failure = Column(Boolean, default=True)
    
    # Resource constraints
    max_concurrent_patches = Column(Integer)  # Max systems patching at once
    team_capacity_hours_per_week = Column(Integer, default=40)
    
    # Success criteria
    acceptable_failure_rate = Column(Numeric(5, 2), default=5.0)  # 5% failure ok
    min_success_rate_for_auto_proceed = Column(Numeric(5, 2), default=95.0)
    
    # AI-assisted planning
    use_ai_reasoning = Column(Boolean, default=True)
    ai_model_version = Column(String(50), default="claude-opus-4")
    ai_reasoning_prompt = Column(Text)  # Custom prompt for planning
    
    # Notification preferences
    notify_on_bundle_ready = Column(Boolean, default=True)
    notify_on_patch_complete = Column(Boolean, default=True)
    notification_channels = Column(JSON)  # {"email": ["ops@company.com"], "slack": ["#patches"]}
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    goal = relationship("Goal", backref="enhanced_settings")
    
    def __repr__(self):
        return f"<EnhancedGoal for {self.goal_id}: {self.risk_profile}>"
    
    def get_risk_profile_rules(self) -> Dict:
        """Get rules for the selected risk profile."""
        profiles = {
            "CONSERVATIVE": {
                "max_vulns_per_window": 5,
                "min_patch_weather": 70,
                "require_successful_test": True,
                "min_days_since_release": 7,
                "allow_emergency_patches": False
            },
            "BALANCED": {
                "max_vulns_per_window": 15,
                "min_patch_weather": 40,
                "require_successful_test": True,
                "min_days_since_release": 3,
                "allow_emergency_patches": True
            },
            "AGGRESSIVE": {
                "max_vulns_per_window": 50,
                "min_patch_weather": 20,
                "require_successful_test": False,
                "min_days_since_release": 0,
                "allow_emergency_patches": True
            }
        }
        return profiles.get(self.risk_profile, profiles["BALANCED"])
    
    def get_tier_sla(self, tier: int) -> int:
        """Get SLA hours for a given tier."""
        slas = {
            0: 24,    # 24 hours
            1: 168,   # 7 days
            2: 720,   # 30 days
            3: 2160   # 90 days
        }
        return slas.get(tier, 720)  # Default 30 days