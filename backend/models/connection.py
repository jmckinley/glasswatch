"""
Connection model - External service integrations
"""

from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from backend.db.base import Base


class Connection(Base):
    """
    External connection/integration model.
    
    Stores credentials and configuration for external services:
    - Cloud providers (AWS, Azure, GCP)
    - Collaboration tools (Slack, Jira, ServiceNow)
    - Security tools (various scanners)
    - Generic webhooks
    """
    __tablename__ = "connections"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Tenant relationship
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Connection metadata
    provider = Column(
        String(100),
        nullable=False,
        comment="Provider type: aws, azure, gcp, slack, jira, servicenow, webhook, etc."
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment="User-friendly name for this connection"
    )
    
    # Configuration (encrypted at rest)
    config = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Provider-specific configuration including credentials"
    )
    
    # Status tracking
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Connection status: pending, active, error, disabled"
    )
    
    last_health_check = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful health check timestamp"
    )
    
    last_error = Column(
        Text,
        nullable=True,
        comment="Last error message if health check failed"
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="connections")
    
    def __repr__(self):
        return f"<Connection {self.name} ({self.provider}) - {self.status}>"
    
    def mask_secrets(self) -> dict:
        """
        Return a safe version of config with secrets masked.
        
        Returns:
            Config dict with sensitive values masked
        """
        if not self.config:
            return {}
        
        masked = self.config.copy()
        
        # Keys that should be masked
        secret_keys = {
            "access_key",
            "secret_key",
            "access_token",
            "refresh_token",
            "api_key",
            "password",
            "client_secret",
            "private_key",
            "token",
            "secret",
        }
        
        def mask_recursive(obj):
            """Recursively mask secrets in nested dicts."""
            if isinstance(obj, dict):
                return {
                    k: "***MASKED***" if k.lower() in secret_keys or any(s in k.lower() for s in secret_keys)
                    else mask_recursive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            return obj
        
        return mask_recursive(masked)
