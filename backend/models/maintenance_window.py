"""
MaintenanceWindow model for scheduling patch deployments.

Defines when patches can be applied to systems.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float,
    ForeignKey, JSON, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class MaintenanceWindow(Base):
    """
    Approved time windows for performing maintenance activities.
    
    These are negotiated with the business and represent when
    systems can be taken offline for patching.
    """
    __tablename__ = "maintenance_windows"

    # Identity
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(
        SQLEnum(
            "scheduled",    # Regular, recurring window
            "emergency",    # Ad-hoc for critical patches
            "blackout",     # No maintenance allowed
            name="maintenance_window_type_enum"
        ),
        nullable=False,
        default="scheduled"
    )
    
    # Time window
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), nullable=True)  # IANA timezone
    
    # Capacity and constraints
    max_duration_hours = Column(Float, nullable=True)
    max_assets = Column(Integer, nullable=True)
    max_risk_score = Column(Float, nullable=True)
    
    # Scope
    environment = Column(String(50), nullable=True)  # production, staging, etc.
    asset_tags = Column(JSON, nullable=True)  # Which assets can use this window
    excluded_assets = Column(JSON, nullable=True)  # Specific exclusions
    
    # Status
    active = Column(Boolean, nullable=False, default=True)
    approved = Column(Boolean, nullable=False, default=False)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Activities allowed
    approved_activities = Column(JSON, nullable=True)  # ["patching", "updates", "restarts"]
    
    # Change control
    change_freeze = Column(Boolean, nullable=False, default=False)
    change_freeze_reason = Column(Text, nullable=True)
    
    # Metadata
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="maintenance_windows")
    bundles = relationship("Bundle", back_populates="maintenance_window")

    def __repr__(self):
        return f"<MaintenanceWindow(id={self.id}, name='{self.name}', start={self.start_time})>"
    
    @property
    def duration_hours(self) -> float:
        """Calculate window duration in hours."""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600
    
    @property
    def is_future(self) -> bool:
        """Check if window is in the future."""
        now = datetime.now(timezone.utc)
        start = self.start_time if self.start_time.tzinfo else self.start_time.replace(tzinfo=timezone.utc)
        return start > now
    
    @property
    def is_active_now(self) -> bool:
        """Check if window is currently active."""
        now = datetime.now(timezone.utc)
        start = self.start_time if self.start_time.tzinfo else self.start_time.replace(tzinfo=timezone.utc)
        end = self.end_time if self.end_time.tzinfo else self.end_time.replace(tzinfo=timezone.utc)
        return start <= now <= end
    
    def can_accommodate_bundle(self, bundle_duration_hours: float, asset_count: int) -> bool:
        """Check if bundle fits within window constraints."""
        if not self.active:
            return False
        
        if self.change_freeze:
            return False
        
        if self.max_duration_hours and bundle_duration_hours > self.max_duration_hours:
            return False
        
        if self.max_assets and asset_count > self.max_assets:
            return False
        
        # Check if window has enough time
        if bundle_duration_hours > self.duration_hours:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "timezone": self.timezone,
            "duration_hours": self.duration_hours,
            "max_duration_hours": self.max_duration_hours,
            "max_assets": self.max_assets,
            "max_risk_score": self.max_risk_score,
            "environment": self.environment,
            "active": self.active,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "is_future": self.is_future,
            "is_active_now": self.is_active_now,
            "change_freeze": self.change_freeze,
            "change_freeze_reason": self.change_freeze_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }