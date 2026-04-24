"""
Audit log model for compliance and security tracking
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from backend.db.base import Base


class AuditLog(Base):
    """
    Audit log for tracking all significant actions

    Required for:
    - SOC 2 compliance
    - Security investigations
    - Change tracking
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # Who
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Nullable for system actions

    # What
    action = Column(String(100), nullable=False)  # e.g., "bundle.approved", "user.login"
    resource_type = Column(String(50), nullable=True)  # e.g., "bundle", "asset"
    resource_id = Column(String(255), nullable=True)  # ID of affected resource
    resource_name = Column(String(255), nullable=True)  # Human-readable name e.g. "KEV Emergency Response"

    # Details
    details = Column(JSON, default=dict, nullable=False)  # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)

    # Outcome
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(String(500), nullable=True)

    # When — both column names accepted; created_at is canonical, timestamp is alias
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    # Backward-compat property so existing code using .timestamp still works
    @property
    def timestamp(self):
        return self.created_at

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id} at {self.created_at}>"

    @classmethod
    async def log_action(cls, db_session, tenant_id: uuid.UUID, user_id: uuid.UUID,
                   action: str, resource_type: str = None, resource_id: str = None,
                   resource_name: str = None, details: dict = None,
                   ip_address: str = None, user_agent: str = None,
                   success: bool = True, error_message: str = None):
        """
        Helper method to create audit log entries.
        Async to support await from async route handlers.
        """
        log_entry = cls(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )
        db_session.add(log_entry)
        return log_entry
