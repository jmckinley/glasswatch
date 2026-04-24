"""
PatchBundle model - represents a collection of patches scheduled together.

Bundles are the output of the goal optimizer - they group patches that can
be safely deployed together during a maintenance window.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    Index, JSON, Text, Boolean, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class PatchBundle(Base):
    """
    A collection of patches scheduled to be deployed together.
    
    Created by the goal optimizer based on constraints like maintenance windows,
    dependencies, risk tolerance, and team capacity.
    """
    __tablename__ = "patch_bundles"
    __table_args__ = (
        Index("ix_bundle_goal_id", "goal_id"),
        Index("ix_bundle_scheduled", "scheduled_for"),
        Index("ix_bundle_status", "status"),
        Index("ix_bundle_risk", "total_risk_score"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    
    # Bundle metadata
    name = Column(String(255), nullable=False)  # "Production Web Servers - Week 15"
    description = Column(Text)
    bundle_type = Column(String(50))  # STANDARD, EMERGENCY, ZERO_DAY
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    duration_estimate_minutes = Column(Integer, default=240)  # 4 hours default
    maintenance_window_id = Column(String(100))  # Reference to which window
    
    # Risk assessment
    total_risk_score = Column(Integer)  # Sum of all vulnerability scores
    highest_risk_score = Column(Integer)  # Highest individual score
    risk_assessment = Column(Text)  # Human-readable risk summary
    
    # Patch Weather score (aggregate)
    patch_weather_score = Column(Integer)  # 0-100, 100 = sunny
    weather_forecast = Column(String(20))  # SUNNY, CLOUDY, STORMY
    weather_confidence = Column(Numeric(5, 2))  # Confidence percentage
    
    # Bundle composition
    asset_count = Column(Integer, default=0)  # Number of assets
    vulnerability_count = Column(Integer, default=0)  # Number of vulns
    total_patch_size_mb = Column(Integer)  # Total download size
    
    # Affected assets summary
    affected_environments = Column(ARRAY(String))  # ["production", "staging"]
    affected_asset_types = Column(ARRAY(String))  # ["server", "container"]
    affected_teams = Column(ARRAY(String))  # ["web-team", "api-team"]
    
    # Dependencies
    depends_on_bundles = Column(ARRAY(UUID))  # Must be completed first
    blocks_bundles = Column(ARRAY(UUID))  # Cannot start until this completes
    
    # Implementation details
    implementation_steps = Column(JSON)  # Step-by-step procedure
    verification_steps = Column(JSON)  # How to verify success
    rollback_plan = Column(Text)  # How to undo if needed
    
    # Testing requirements
    requires_testing = Column(Boolean, default=True)
    test_environment = Column(String(100))  # Which env to test in
    test_duration_hours = Column(Integer, default=24)
    test_success_criteria = Column(JSON)
    
    # Change management
    change_ticket_id = Column(String(255))  # ServiceNow CHG0012345
    change_ticket_url = Column(String(500))
    approval_required = Column(Boolean, default=True)
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    # Execution tracking
    status = Column(String(50), default="PLANNED")  # PLANNED, APPROVED, IN_PROGRESS, COMPLETED, FAILED, ROLLED_BACK
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    actual_duration_minutes = Column(Integer)
    
    # Results
    patches_attempted = Column(Integer, default=0)
    patches_successful = Column(Integer, default=0)
    patches_failed = Column(Integer, default=0)
    failure_details = Column(JSON)  # Details of any failures
    
    # Rollback tracking
    rollback_initiated_at = Column(DateTime(timezone=True))
    rollback_completed_at = Column(DateTime(timezone=True))
    rollback_reason = Column(Text)
    
    # AI reasoning (why these patches together)
    ai_reasoning = Column(Text)
    optimization_factors = Column(JSON)  # What the optimizer considered
    
    # Notifications
    notifications_sent = Column(JSON)  # Track what notifications went out
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    goal = relationship("Goal")  # no back_populates — Goal.bundles points to Bundle
    bundle_patches = relationship("BundlePatch", back_populates="bundle")
    
    def __repr__(self):
        return f"<PatchBundle {self.name}: {self.status}>"
    
    @property
    def is_high_risk(self) -> bool:
        """Check if bundle contains high-risk patches."""
        return self.highest_risk_score >= 70
    
    @property
    def success_rate(self) -> float:
        """Calculate patch success rate."""
        if self.patches_attempted > 0:
            return (self.patches_successful / self.patches_attempted) * 100
        return 0.0
    
    @property
    def is_ready_to_execute(self) -> bool:
        """Check if bundle is ready for execution."""
        return (
            self.status == "APPROVED" and
            self.scheduled_for <= datetime.now(timezone.utc) and
            not self.depends_on_bundles  # No unmet dependencies
        )
    
    @property
    def estimated_downtime_hours(self) -> float:
        """Get estimated downtime in hours."""
        return self.duration_estimate_minutes / 60.0


class BundlePatch(Base):
    """
    Junction table linking bundles to specific asset-vulnerability pairs.
    
    Each record represents one patch to be applied to one asset.
    """
    __tablename__ = "bundle_patches"
    __table_args__ = (
        Index("ix_bundle_patch_bundle", "bundle_id"),
        Index("ix_bundle_patch_asset", "asset_id"),
        Index("ix_bundle_patch_order", "bundle_id", "execution_order"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("patch_bundles.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False)
    
    # Execution planning
    execution_order = Column(Integer, default=0)  # Order within bundle
    depends_on = Column(ARRAY(UUID))  # Other patches that must complete first
    
    # Patch details
    patch_id = Column(String(255))  # KB5021233, RHSA-2024:1234
    patch_size_mb = Column(Integer)
    estimated_install_time_minutes = Column(Integer, default=10)
    requires_reboot = Column(Boolean, default=False)
    
    # Risk for this specific patch
    risk_score = Column(Integer)  # From asset_vulnerability
    risk_rationale = Column(Text)  # Why this score
    
    # Execution tracking
    status = Column(String(50), default="PENDING")  # PENDING, INSTALLING, COMPLETED, FAILED, ROLLED_BACK
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    exit_code = Column(Integer)
    output_log = Column(Text)
    error_message = Column(Text)
    
    # Verification
    verified = Column(Boolean, default=False)
    verification_method = Column(String(100))  # VERSION_CHECK, VULNERABILITY_SCAN, FUNCTIONAL_TEST
    verified_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    bundle = relationship("PatchBundle", back_populates="bundle_patches")
    
    def __repr__(self):
        return f"<BundlePatch {self.bundle_id} -> {self.asset_id}/{self.vulnerability_id}>"