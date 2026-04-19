"""
Approval workflow models
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from backend.db.base import Base


class ApprovalStatus(str, enum.Enum):
    """Approval statuses"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalAction(Base):
    """
    Approval actions for bundle deployment workflows
    
    Tracks who approved/rejected what and when
    """
    __tablename__ = "approval_actions"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # What needs approval
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Who took action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Action details
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    bundle = relationship("Bundle", backref="approvals")
    tenant = relationship("Tenant")
    user = relationship("User", back_populates="approval_actions")
    
    def __repr__(self):
        return f"<ApprovalAction {self.status} for bundle {self.bundle_id}>"