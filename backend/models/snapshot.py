"""
Snapshot and rollback models for patch state management.

Captures system state before/after patches for safe rollback operations.
"""
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from uuid import uuid4
import hashlib
import json

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    Index, JSON, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class SnapshotType(str, PyEnum):
    """Type of system snapshot."""
    PRE_PATCH = "pre_patch"
    POST_PATCH = "post_patch"
    MANUAL = "manual"


class RollbackStatus(str, PyEnum):
    """Status of a rollback operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PatchSnapshot(Base):
    """
    System state snapshot for rollback capability.
    
    Captures package state, configurations, and services before/after patches.
    Enables safe rollback when patches cause issues.
    """
    __tablename__ = "patch_snapshots"
    __table_args__ = (
        Index("ix_patch_snapshot_bundle_id", "bundle_id"),
        Index("ix_patch_snapshot_asset_id", "asset_id"),
        Index("ix_patch_snapshot_tenant_id", "tenant_id"),
        Index("ix_patch_snapshot_type", "snapshot_type"),
        Index("ix_patch_snapshot_created", "created_at"),
        Index("ix_patch_snapshot_expires", "expires_at"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Snapshot metadata
    snapshot_type = Column(
        SQLEnum(SnapshotType, name="snapshottype"),
        nullable=False,
        index=True
    )
    
    # System state data
    system_state = Column(JSON, nullable=False)
    # Structure:
    # {
    #   "packages": [{"name": "openssl", "version": "1.1.1k", "architecture": "amd64"}],
    #   "configs": {"/etc/nginx/nginx.conf": "sha256:abcd...", ...},
    #   "services": [{"name": "nginx", "state": "running", "enabled": true}],
    #   "kernel": "5.15.0-91-generic"
    # }
    
    # Capture metadata
    snapshot_metadata = Column("metadata", JSON, nullable=False)
    # Structure:
    # {
    #   "capture_method": "apt-history",
    #   "duration_ms": 1234,
    #   "agent_version": "1.0.0",
    #   "hostname": "web-01.prod",
    #   "os_info": "Ubuntu 22.04.3 LTS"
    # }
    
    # Integrity and storage
    checksum = Column(String(64), nullable=False)  # SHA-256 of system_state JSON
    size_bytes = Column(Integer, nullable=False, default=0)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=90)
    )
    
    # Relationships
    bundle = relationship("Bundle", backref="snapshots")
    asset = relationship("Asset", backref="snapshots")
    tenant = relationship("Tenant", backref="snapshots")
    
    def __repr__(self):
        return f"<PatchSnapshot {self.id}: {self.snapshot_type} for asset {self.asset_id}>"
    
    @staticmethod
    def calculate_checksum(system_state: dict) -> str:
        """Calculate SHA-256 checksum of system state."""
        # Serialize to JSON with sorted keys for deterministic hash
        state_json = json.dumps(system_state, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()
    
    def validate_integrity(self) -> bool:
        """Verify snapshot integrity by checking checksum."""
        calculated = self.calculate_checksum(self.system_state)
        return calculated == self.checksum


class RollbackRecord(Base):
    """
    Record of a rollback operation.
    
    Tracks rollback attempts, status, and results for audit and analysis.
    """
    __tablename__ = "rollback_records"
    __table_args__ = (
        Index("ix_rollback_bundle_id", "bundle_id"),
        Index("ix_rollback_asset_id", "asset_id"),
        Index("ix_rollback_tenant_id", "tenant_id"),
        Index("ix_rollback_snapshot_id", "snapshot_id"),
        Index("ix_rollback_status", "status"),
        Index("ix_rollback_started", "started_at"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("patch_snapshots.id"), nullable=False)
    
    # Rollback metadata
    trigger = Column(String(50), nullable=False)  # manual, health_check_failed, automated, approval_rejected
    status = Column(
        SQLEnum(RollbackStatus, name="rollbackstatus"),
        nullable=False,
        default=RollbackStatus.PENDING,
        index=True
    )
    reason = Column(Text, nullable=False)
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Results
    rollback_details = Column(JSON, nullable=True)
    # Structure:
    # {
    #   "packages_reverted": ["openssl", "libssl1.1"],
    #   "configs_restored": ["/etc/nginx/nginx.conf"],
    #   "services_restarted": ["nginx"],
    #   "actions_taken": ["apt-get install openssl=1.1.1k-1ubuntu1.9"],
    #   "verification_status": "success"
    # }
    
    # Relationships
    bundle = relationship("Bundle", backref="rollbacks")
    asset = relationship("Asset", backref="rollbacks")
    tenant = relationship("Tenant", backref="rollbacks")
    snapshot = relationship("PatchSnapshot", backref="rollback_records")
    
    def __repr__(self):
        return f"<RollbackRecord {self.id}: {self.status} for bundle {self.bundle_id}>"
    
    @property
    def duration_seconds(self) -> int:
        """Calculate rollback duration in seconds."""
        if not self.completed_at:
            return 0
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())
    
    @property
    def is_complete(self) -> bool:
        """Check if rollback is in terminal state."""
        return self.status in (RollbackStatus.COMPLETED, RollbackStatus.FAILED)
