"""
Tag model - represents a taxonomy system for organizing assets and bundles.

Provides namespace-based tagging with autocomplete, aliases, and usage tracking.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    UniqueConstraint, Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class Tag(Base):
    """
    Tag for categorizing and organizing assets, bundles, and other entities.
    
    Multi-tenant model with namespace-based organization and autocomplete support.
    """
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'namespace', 'name', name='uq_tag_tenant_namespace_name'),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Tag identity
    name = Column(String(100), nullable=False)  # e.g. "financial"
    namespace = Column(String(50), nullable=False)  # e.g. "system", "compliance", "env", "tier", "team"
    display_name = Column(String(150))  # e.g. "system:financial"
    description = Column(Text, nullable=True)
    
    # UI and metadata
    color = Column(String(7), nullable=True)  # hex color for UI badges (e.g. "#3B82F6")
    aliases = Column(JSON, default=list)  # ["finance", "fin-systems"] for autocomplete matching
    usage_count = Column(Integer, default=0)  # denormalized count of entities using this tag
    
    # System flags
    is_default = Column(Boolean, default=False)  # shipped with the system
    is_system = Column(Boolean, default=False)  # cannot be deleted by users
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="tags")
    
    def __repr__(self):
        return f"<Tag {self.display_name or f'{self.namespace}:{self.name}'}>"
    
    @property
    def full_name(self) -> str:
        """Return the full namespaced tag name."""
        return self.display_name or f"{self.namespace}:{self.name}"
