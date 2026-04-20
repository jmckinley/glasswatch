"""
Approval workflow models
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Text, Integer, Boolean
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


class RiskLevel(str, enum.Enum):
    """Risk levels for approval requests"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalRequest(Base):
    """
    Approval requests for bundle deployments.
    
    Tracks the overall approval workflow for a bundle, including
    multi-level approvals and risk assessment.
    """
    __tablename__ = "approval_requests"
    
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
    
    # Who requested
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Request details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    
    # Approval workflow
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    required_approvals = Column(Integer, nullable=False, default=1)
    current_approvals = Column(Integer, nullable=False, default=0)
    
    # Impact and risk
    impact_summary = Column(JSON, nullable=True)  # Assets affected, services impacted, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    bundle = relationship("Bundle", backref="approval_request")
    tenant = relationship("Tenant")
    requester = relationship("User", foreign_keys=[requester_id])
    actions = relationship("ApprovalAction", back_populates="approval_request", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ApprovalRequest {self.title} ({self.status})>"


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
    
    # Link to approval request
    approval_request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=True)
    
    # What needs approval (legacy support)
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
    approval_request = relationship("ApprovalRequest", back_populates="actions")
    bundle = relationship("Bundle", backref="approvals")
    tenant = relationship("Tenant")
    user = relationship("User", back_populates="approval_actions")
    
    def __repr__(self):
        return f"<ApprovalAction {self.status} for bundle {self.bundle_id}>"


class ApprovalPolicy(Base):
    """
    Approval policies define approval requirements based on risk level.
    
    Policies are tenant-specific and control:
    - How many approvals are required
    - Which roles can approve
    - Auto-approval rules
    - Escalation timeframes
    """
    __tablename__ = "approval_policies"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Policy details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    
    # Approval requirements
    required_approvals = Column(Integer, nullable=False, default=1)
    required_roles = Column(JSON, nullable=True)  # List of UserRole values that can approve
    
    # Automation
    auto_approve_low_risk = Column(Boolean, nullable=False, default=False)
    escalation_hours = Column(Integer, nullable=False, default=48)  # Hours before escalation
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    
    def __repr__(self):
        return f"<ApprovalPolicy {self.name} ({self.risk_level})>"