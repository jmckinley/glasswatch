"""
Activity model - Activity feed and notifications
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from backend.db.base import Base


class ActivityType(str, enum.Enum):
    """Types of activities tracked in the system"""
    COMMENT_ADDED = "comment_added"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    BUNDLE_CREATED = "bundle_created"
    BUNDLE_EXECUTED = "bundle_executed"
    ASSET_DISCOVERED = "asset_discovered"
    VULNERABILITY_FOUND = "vulnerability_found"
    GOAL_CREATED = "goal_created"
    GOAL_COMPLETED = "goal_completed"
    ROLLBACK_INITIATED = "rollback_initiated"
    SCAN_COMPLETED = "scan_completed"
    USER_MENTIONED = "user_mentioned"


class Activity(Base):
    """
    Activity model for tracking system events and user actions
    
    Used for:
    - Activity feed
    - Notifications
    - Audit trail of important events
    """
    __tablename__ = "activities"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Tenant relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Actor (nullable for system actions)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Activity classification
    activity_type = Column(Enum(ActivityType), nullable=False)
    
    # Entity reference
    entity_type = Column(String(50), nullable=False)  # "bundle", "asset", "vulnerability", etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Human-readable summary
    title = Column(String(255), nullable=False)
    
    # Additional context (JSON)
    details = Column(JSON, default=dict, nullable=False)
    
    # Notification tracking
    is_read = Column(Boolean, default=False, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    
    def __repr__(self):
        actor = self.user_id if self.user_id else "system"
        return f"<Activity {self.activity_type} by {actor} on {self.entity_type}:{self.entity_id}>"
    
    def to_dict(self):
        """Convert activity to dict for API responses"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "activity_type": self.activity_type.value,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "title": self.title,
            "details": self.details,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
