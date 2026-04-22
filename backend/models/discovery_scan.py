"""
Discovery Scan model for tracking asset discovery history.

Stores metadata and results for each discovery scan execution.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class DiscoveryScan(Base):
    """
    Record of a discovery scan execution.
    
    Tracks scan metadata, status, and results over time.
    """
    __tablename__ = "discovery_scans"

    # Identity
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Scan details
    scan_type = Column(String(100), nullable=False)  # "full", "incremental", "targeted", etc.
    status = Column(String(50), nullable=False, index=True)  # "running", "completed", "failed"
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    results_summary = Column(JSON, nullable=True)  # Summary of what was discovered
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Context
    initiated_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    config = Column(JSON, nullable=True)  # Scanner configuration used
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")

    def __repr__(self):
        return f"<DiscoveryScan(id={self.id}, scan_type='{self.scan_type}', status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "scan_type": self.scan_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results_summary": self.results_summary,
            "error_message": self.error_message,
            "initiated_by": str(self.initiated_by) if self.initiated_by else None,
            "config": self.config,
        }
