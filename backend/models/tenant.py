"""
Tenant model - Multi-tenant isolation
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from backend.db.base import Base


class Tenant(Base):
    """
    Tenant model for multi-tenant isolation
    
    Each tenant has:
    - Isolated data (vulnerabilities, assets, goals)
    - Own encryption keys
    - Regional deployment
    - Subscription tier
    """
    __tablename__ = "tenants"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Basic info
    name = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False)
    
    # Regional deployment
    region = Column(String(50), nullable=False, default="us-east-1")
    
    # Subscription
    tier = Column(String(50), nullable=False, default="trial")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Security
    encryption_key_id = Column(String(255), nullable=False)
    
    # Settings
    settings = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bundles = relationship("Bundle", back_populates="tenant")
    maintenance_windows = relationship("MaintenanceWindow", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant {self.name} ({self.id})>"