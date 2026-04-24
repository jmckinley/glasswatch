"""
MaintenanceWindow model for scheduling patch deployments.

Defines when patches can be applied to systems.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
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
    
    # Enhanced scoping (Sprint 13)
    priority = Column(Integer, nullable=False, default=0)  # Higher = more specific
    asset_group = Column(String(100), nullable=True)  # e.g., "web-servers", "databases"
    service_name = Column(String(100), nullable=True)  # Scope to specific app/service
    is_default = Column(Boolean, nullable=False, default=False)  # Fallback window
    
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
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
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
    
    @classmethod
    async def find_best_window(
        cls,
        db,
        tenant_id: UUID,
        asset=None,
        environment: Optional[str] = None
    ) -> Optional["MaintenanceWindow"]:
        """
        Find the most specific matching maintenance window.
        
        Priority order:
        1. Exact service_name + environment match (highest priority)
        2. Asset group + environment match
        3. Environment-only match
        4. Default window (is_default=True)
        """
        from sqlalchemy import select, and_
        
        now = datetime.now(timezone.utc)
        
        # Base query: active windows in the future for this tenant
        base_conditions = [
            cls.tenant_id == tenant_id,
            cls.active == True,
            cls.start_time > now,
        ]
        
        # Try to extract service name and asset group from asset if provided
        service_name = None
        asset_group = None
        if asset:
            # Assume asset has tags or metadata
            if hasattr(asset, 'tags') and asset.tags:
                service_name = asset.tags.get('service_name')
                asset_group = asset.tags.get('asset_group')
            if not environment and hasattr(asset, 'environment'):
                environment = asset.environment
        
        # Priority 1: service_name + environment match
        if service_name and environment:
            result = await db.execute(
                select(cls)
                .where(and_(*base_conditions, cls.service_name == service_name, cls.environment == environment))
                .order_by(cls.priority.desc(), cls.start_time.asc())
                .limit(1)
            )
            window = result.scalar_one_or_none()
            if window:
                return window
        
        # Priority 2: asset_group + environment match
        if asset_group and environment:
            result = await db.execute(
                select(cls)
                .where(and_(*base_conditions, cls.asset_group == asset_group, cls.environment == environment))
                .order_by(cls.priority.desc(), cls.start_time.asc())
                .limit(1)
            )
            window = result.scalar_one_or_none()
            if window:
                return window
        
        # Priority 3: environment-only match
        if environment:
            result = await db.execute(
                select(cls)
                .where(and_(*base_conditions, cls.environment == environment, cls.service_name.is_(None), cls.asset_group.is_(None)))
                .order_by(cls.priority.desc(), cls.start_time.asc())
                .limit(1)
            )
            window = result.scalar_one_or_none()
            if window:
                return window
        
        # Priority 4: default window
        result = await db.execute(
            select(cls)
            .where(and_(*base_conditions, cls.is_default == True))
            .order_by(cls.start_time.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
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
            "priority": self.priority,
            "asset_group": self.asset_group,
            "service_name": self.service_name,
            "is_default": self.is_default,
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