"""
Bundle model for patch scheduling.

Represents a collection of vulnerabilities to be patched together
in a maintenance window.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float,
    ForeignKey, JSON, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Bundle(Base):
    """
    A bundle groups vulnerabilities for patching in a maintenance window.
    
    This is the output of the optimization engine - an actionable
    collection of patches scheduled for a specific time.
    """
    __tablename__ = "bundles"

    # Identity
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    goal_id = Column(PGUUID(as_uuid=True), ForeignKey("goals.id"), nullable=True, index=True)
    
    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(
            "draft",
            "scheduled", 
            "approved",
            "in_progress",
            "completed",
            "failed",
            "cancelled",
            name="bundle_status_enum"
        ),
        nullable=False,
        default="draft",
        index=True
    )
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    maintenance_window_id = Column(PGUUID(as_uuid=True), ForeignKey("maintenance_windows.id"), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    
    # Risk and impact
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=True)  # CRITICAL, HIGH, MEDIUM, LOW
    assets_affected_count = Column(Integer, nullable=False, default=0)
    
    # Workflow
    approval_required = Column(Boolean, nullable=False, default=False)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    
    # Results
    success_count = Column(Integer, nullable=True)
    failure_count = Column(Integer, nullable=True)
    rollback_count = Column(Integer, nullable=True)
    
    # Metadata
    risk_assessment = Column(JSON, nullable=True)  # Detailed risk breakdown
    implementation_plan = Column(JSON, nullable=True)  # Step-by-step plan
    rollback_plan = Column(JSON, nullable=True)  # Recovery procedures
    execution_log = Column(JSON, nullable=True)  # What happened during execution
    tags = Column(JSON, nullable=True)  # Custom tags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="bundles")
    goal = relationship("Goal", back_populates="bundles")
    maintenance_window = relationship("MaintenanceWindow", back_populates="bundles")
    items = relationship("BundleItem", back_populates="bundle", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bundle(id={self.id}, name='{self.name}', status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "goal_id": str(self.goal_id) if self.goal_id else None,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "maintenance_window_id": str(self.maintenance_window_id) if self.maintenance_window_id else None,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "assets_affected_count": self.assets_affected_count,
            "approval_required": self.approval_required,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "actual_duration_minutes": self.actual_duration_minutes,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "rollback_count": self.rollback_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }