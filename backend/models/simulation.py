"""
Patch simulation model for impact prediction and dry-run testing.

Enables "what-if" analysis before executing patches.
"""
from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, 
    Index, JSON, Float, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class SimulationStatus(str, PyEnum):
    """Status of a patch simulation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PatchSimulation(Base):
    """
    Simulation of patch impact and execution.
    
    Predicts risk, impact, and outcomes before executing patches.
    Provides dry-run capability for validation.
    """
    __tablename__ = "patch_simulations"
    __table_args__ = (
        Index("ix_patch_simulation_bundle_id", "bundle_id"),
        Index("ix_patch_simulation_tenant_id", "tenant_id"),
        Index("ix_patch_simulation_status", "status"),
        Index("ix_patch_simulation_created", "created_at"),
        Index("ix_patch_simulation_risk", "risk_score"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Simulation state
    status = Column(
        SQLEnum(SimulationStatus, name="simulationstatus"),
        nullable=False,
        default=SimulationStatus.PENDING,
        index=True
    )
    
    # Risk assessment
    risk_score = Column(Float, nullable=False, default=0.0)  # 0-100
    
    # Impact prediction
    impact_summary = Column(JSON, nullable=False)
    # Structure:
    # {
    #   "affected_assets": 12,
    #   "affected_services": ["nginx", "postgresql", "redis"],
    #   "estimated_downtime_minutes": 15.5,
    #   "failure_probability": 0.15,  # 0-1
    #   "blast_radius": {
    #     "direct": 5,        # Assets directly patched
    #     "indirect": 7       # Assets dependent on patched services
    #   },
    #   "dependency_conflicts": [
    #     {
    #       "package": "libssl1.1",
    #       "required_by": "nginx",
    #       "required_version": ">=1.1.1",
    #       "proposed_version": "1.1.0",
    #       "conflict": true
    #     }
    #   ],
    #   "recommended_window": "saturday-2am-4am",
    #   "warnings": [
    #     "This patch requires service restart",
    #     "PostgreSQL will be unavailable during update"
    #   ],
    #   "mitigations": [
    #     "Enable read replica before patching",
    #     "Pre-warm cache after restart",
    #     "Test rollback procedure"
    #   ]
    # }
    
    # Dry-run results
    dry_run_results = Column(JSON, nullable=True)
    # Structure:
    # {
    #   "validation": {
    #     "all_packages_available": true,
    #     "disk_space_sufficient": true,
    #     "connectivity_ok": true,
    #     "maintenance_window_available": true
    #   },
    #   "preflight_checks": [
    #     {"check": "disk_space", "status": "pass", "details": "50GB free, 2GB required"},
    #     {"check": "network", "status": "pass", "details": "All repositories reachable"},
    #     {"check": "dependencies", "status": "warning", "details": "1 potential conflict detected"}
    #   ],
    #   "estimated_download_size_mb": 125.5,
    #   "estimated_install_time_minutes": 8.2,
    #   "rollback_feasibility": "high",
    #   "overall_status": "pass"  # pass, warning, fail
    # }
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    bundle = relationship("Bundle", backref="simulations")
    tenant = relationship("Tenant", backref="simulations")
    
    def __repr__(self):
        return f"<PatchSimulation {self.id}: {self.status}, risk={self.risk_score:.1f}>"
    
    @property
    def duration_seconds(self) -> int:
        """Calculate simulation duration in seconds."""
        if not self.completed_at:
            return 0
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())
    
    @property
    def risk_level(self) -> str:
        """Convert risk score to categorical level."""
        if self.risk_score >= 80:
            return "CRITICAL"
        elif self.risk_score >= 60:
            return "HIGH"
        elif self.risk_score >= 40:
            return "MEDIUM"
        elif self.risk_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"
    
    @property
    def is_safe_to_proceed(self) -> bool:
        """Determine if simulation indicates patch is safe to execute."""
        # Check dry-run passed
        if self.dry_run_results:
            overall_status = self.dry_run_results.get("overall_status")
            if overall_status == "fail":
                return False
        
        # Check risk score
        if self.risk_score >= 80:
            return False
        
        # Check dependency conflicts
        conflicts = self.impact_summary.get("dependency_conflicts", [])
        if any(c.get("conflict") for c in conflicts):
            return False
        
        return True
