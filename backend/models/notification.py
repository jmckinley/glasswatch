"""
Notification model for in-app notifications.

Stores notifications for display in the UI.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, 
    ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Notification(Base):
    """
    In-app notification for display in UI.
    
    Supports per-user notifications and broadcast notifications
    (when user_id is null, notification is for all users in tenant).
    """
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_tenant_user_read", "tenant_id", "user_id", "read"),
        Index("ix_notification_created", "created_at"),
    )

    # Identity
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # null = all users
    
    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional structured data (URLs, IDs, etc.)
    
    # Metadata
    priority = Column(String(20), nullable=False, default="normal")  # low, normal, high, critical
    channel = Column(String(50), nullable=True)  # What triggered this (alert, bundle, vuln, etc.)
    
    # Read tracking
    read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, title='{self.title}', read={self.read})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "priority": self.priority,
            "channel": self.channel,
            "read": self.read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
