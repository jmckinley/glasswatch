"""
BundleItem model for individual patches within a bundle.

Each item represents a specific vulnerability-asset pair to be patched.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float,
    ForeignKey, JSON, Text, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class BundleItem(Base):
    """
    Individual patch item within a bundle.
    
    Represents one vulnerability on one asset that needs patching.
    """
    __tablename__ = "bundle_items"
    __table_args__ = (
        # Ensure no duplicate vuln-asset pairs in same bundle
        UniqueConstraint("bundle_id", "vulnerability_id", "asset_id", name="uq_bundle_vuln_asset"),
    )

    # Identity
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(PGUUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False, index=True)
    vulnerability_id = Column(PGUUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False, index=True)
    asset_id = Column(PGUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True)
    
    # Status tracking
    status = Column(
        SQLEnum(
            "pending",
            "in_progress", 
            "success",
            "failed",
            "skipped",
            "rolled_back",
            name="bundle_item_status_enum"
        ),
        nullable=False,
        default="pending",
        index=True
    )
    
    # Risk and priority
    risk_score = Column(Float, nullable=False)
    priority = Column(Integer, nullable=True)  # Order within bundle
    
    # Patch details
    patch_identifier = Column(String(200), nullable=True)  # KB number, package name, etc.
    patch_source = Column(String(100), nullable=True)  # vendor, repository, etc.
    patch_verified = Column(Boolean, nullable=False, default=False)
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Results
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    rollback_performed = Column(Boolean, nullable=False, default=False)
    rollback_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    pre_patch_data = Column(JSON, nullable=True)  # Snapshot before patching
    post_patch_data = Column(JSON, nullable=True)  # Verification after patching
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bundle = relationship("Bundle", back_populates="items")
    vulnerability = relationship("Vulnerability")
    asset = relationship("Asset")

    def __repr__(self):
        return f"<BundleItem(id={self.id}, bundle_id={self.bundle_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "bundle_id": str(self.bundle_id),
            "vulnerability_id": str(self.vulnerability_id),
            "asset_id": str(self.asset_id),
            "status": self.status,
            "risk_score": self.risk_score,
            "priority": self.priority,
            "patch_identifier": self.patch_identifier,
            "patch_source": self.patch_source,
            "patch_verified": self.patch_verified,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "error_message": self.error_message,
            "rollback_performed": self.rollback_performed,
            "rollback_at": self.rollback_at.isoformat() if self.rollback_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }