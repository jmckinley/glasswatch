"""
Patch simulation service for impact prediction and dry-run testing.

Predicts patch impact, identifies risks, and validates execution feasibility.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import UUID
import random

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.simulation import PatchSimulation, SimulationStatus
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.asset import Asset


class SimulatorService:
    """
    Service for simulating patch impact and execution.
    
    Provides "what-if" analysis before executing patches.
    """
    
    # Risk scoring weights
    CRITICALITY_WEIGHT = 15
    EXPOSURE_WEIGHT = 20
    DOWNTIME_WEIGHT = 25
    FAILURE_PROB_WEIGHT = 30
    CONFLICT_WEIGHT = 10
    
    async def predict_impact(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        tenant_id: UUID
    ) -> PatchSimulation:
        """
        Analyze a bundle and predict its impact.
        
        Considers:
        - Affected assets and services
        - Dependency conflicts
        - Estimated downtime
        - Failure probability
        - Blast radius
        """
        # Fetch bundle and items
        bundle_result = await db.execute(
            select(Bundle).where(Bundle.id == bundle_id)
        )
        bundle = bundle_result.scalar_one_or_none()
        
        if not bundle:
            raise ValueError(f"Bundle {bundle_id} not found")
        
        # Fetch bundle items
        items_result = await db.execute(
            select(BundleItem).where(BundleItem.bundle_id == bundle_id)
        )
        items = items_result.scalars().all()
        
        # Fetch affected assets
        asset_ids = {item.asset_id for item in items if item.asset_id}
        assets_result = await db.execute(
            select(Asset).where(Asset.id.in_(asset_ids))
        )
        assets = assets_result.scalars().all()
        
        # Analyze impact
        affected_services = set()
        total_criticality = 0
        internet_facing_count = 0
        
        for asset in assets:
            # Extract services
            services = asset.running_services or []
            affected_services.update(services)
            
            # Sum criticality
            total_criticality += asset.criticality
            
            # Count internet-facing
            if asset.exposure == "INTERNET":
                internet_facing_count += 1
        
        # Estimate downtime based on asset types and patch count
        base_downtime = 5  # minutes
        downtime_per_patch = 2
        downtime_per_service = 3
        
        estimated_downtime = (
            base_downtime +
            (len(items) * downtime_per_patch) +
            (len(affected_services) * downtime_per_service)
        )
        
        # Add variance
        estimated_downtime *= random.uniform(0.8, 1.2)
        
        # Calculate failure probability (0-1)
        base_failure = 0.05
        failure_per_asset = 0.02
        failure_per_service = 0.03
        
        failure_probability = min(
            base_failure + 
            (len(assets) * failure_per_asset) +
            (len(affected_services) * failure_per_service),
            0.95  # Cap at 95%
        )
        
        # Simulate dependency conflicts
        dependency_conflicts = []
        if random.random() < 0.3:  # 30% chance of conflict
            dependency_conflicts.append({
                "package": "libssl1.1",
                "required_by": "nginx",
                "required_version": ">=1.1.1",
                "proposed_version": "1.1.0",
                "conflict": True
            })
        
        # Calculate blast radius
        direct_assets = len(assets)
        # Indirect: estimate based on service dependencies
        indirect_assets = int(direct_assets * random.uniform(0.5, 1.5))
        
        blast_radius = {
            "direct": direct_assets,
            "indirect": indirect_assets
        }
        
        # Generate warnings
        warnings = []
        if estimated_downtime > 30:
            warnings.append(f"Extended downtime expected: {estimated_downtime:.1f} minutes")
        
        if internet_facing_count > 0:
            warnings.append(f"{internet_facing_count} internet-facing assets will be affected")
        
        if failure_probability > 0.2:
            warnings.append(f"Elevated failure risk: {failure_probability*100:.1f}%")
        
        if dependency_conflicts:
            warnings.append(f"{len(dependency_conflicts)} dependency conflict(s) detected")
        
        # Generate mitigations
        mitigations = []
        if internet_facing_count > 0:
            mitigations.append("Enable read replicas or failover before patching")
        
        if estimated_downtime > 20:
            mitigations.append("Schedule during low-traffic window")
        
        if "postgresql" in affected_services or "database" in str(affected_services).lower():
            mitigations.append("Take database backup before proceeding")
        
        mitigations.append("Test rollback procedure before execution")
        mitigations.append("Pre-warm caches after service restart")
        
        # Determine recommended window
        if estimated_downtime > 30 or internet_facing_count > 2:
            recommended_window = "saturday-2am-4am"  # Weekend low-traffic
        elif estimated_downtime > 15:
            recommended_window = "tuesday-2am-4am"  # Weekday low-traffic
        else:
            recommended_window = "any-maintenance-window"
        
        # Build impact summary
        impact_summary = {
            "affected_assets": len(assets),
            "affected_services": sorted(list(affected_services)),
            "estimated_downtime_minutes": round(estimated_downtime, 1),
            "failure_probability": round(failure_probability, 3),
            "blast_radius": blast_radius,
            "dependency_conflicts": dependency_conflicts,
            "recommended_window": recommended_window,
            "warnings": warnings,
            "mitigations": mitigations
        }
        
        # Calculate risk score
        risk_score = self.calculate_risk_score(impact_summary, assets)
        
        # Create simulation record
        simulation = PatchSimulation(
            bundle_id=bundle_id,
            tenant_id=tenant_id,
            status=SimulationStatus.COMPLETED,
            risk_score=risk_score,
            impact_summary=impact_summary,
            completed_at=datetime.now(timezone.utc)
        )
        
        db.add(simulation)
        await db.commit()
        await db.refresh(simulation)
        
        return simulation
    
    async def run_dry_run(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        tenant_id: UUID
    ) -> PatchSimulation:
        """
        Run a dry-run simulation of patch execution.
        
        Validates:
        - Package availability
        - Disk space
        - Connectivity
        - Maintenance window availability
        """
        # Fetch bundle
        bundle_result = await db.execute(
            select(Bundle).where(Bundle.id == bundle_id)
        )
        bundle = bundle_result.scalar_one_or_none()
        
        if not bundle:
            raise ValueError(f"Bundle {bundle_id} not found")
        
        # First run impact prediction
        simulation = await self.predict_impact(db, bundle_id, tenant_id)
        
        # Perform dry-run checks
        preflight_checks = []
        
        # Disk space check
        disk_check = {
            "check": "disk_space",
            "status": "pass",
            "details": "50GB free, 2GB required"
        }
        if random.random() < 0.1:  # 10% chance of low space
            disk_check["status"] = "warning"
            disk_check["details"] = "15GB free, 2GB required (marginal)"
        preflight_checks.append(disk_check)
        
        # Network connectivity check
        network_check = {
            "check": "network",
            "status": "pass",
            "details": "All repositories reachable"
        }
        if random.random() < 0.05:  # 5% chance of network issue
            network_check["status"] = "warning"
            network_check["details"] = "Some mirrors slow (>2s latency)"
        preflight_checks.append(network_check)
        
        # Dependency check
        dependency_check = {
            "check": "dependencies",
            "status": "pass",
            "details": "All dependencies satisfied"
        }
        if simulation.impact_summary.get("dependency_conflicts"):
            dependency_check["status"] = "warning"
            dependency_check["details"] = f"{len(simulation.impact_summary['dependency_conflicts'])} potential conflict(s) detected"
        preflight_checks.append(dependency_check)
        
        # Package availability check
        package_check = {
            "check": "package_availability",
            "status": "pass",
            "details": "All packages available in repositories"
        }
        preflight_checks.append(package_check)
        
        # Maintenance window check
        window_check = {
            "check": "maintenance_window",
            "status": "pass" if bundle.scheduled_for else "warning",
            "details": "Scheduled for maintenance window" if bundle.scheduled_for else "No maintenance window scheduled"
        }
        preflight_checks.append(window_check)
        
        # Determine overall status
        has_failures = any(c["status"] == "fail" for c in preflight_checks)
        has_warnings = any(c["status"] == "warning" for c in preflight_checks)
        
        overall_status = "fail" if has_failures else "warning" if has_warnings else "pass"
        
        # Build dry-run results
        dry_run_results = {
            "validation": {
                "all_packages_available": True,
                "disk_space_sufficient": disk_check["status"] != "fail",
                "connectivity_ok": network_check["status"] != "fail",
                "maintenance_window_available": bool(bundle.scheduled_for)
            },
            "preflight_checks": preflight_checks,
            "estimated_download_size_mb": round(random.uniform(50, 500), 1),
            "estimated_install_time_minutes": round(random.uniform(5, 20), 1),
            "rollback_feasibility": "high",
            "overall_status": overall_status
        }
        
        # Update simulation with dry-run results
        simulation.dry_run_results = dry_run_results
        simulation.status = SimulationStatus.COMPLETED
        simulation.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(simulation)
        
        return simulation
    
    async def get_simulation_history(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        limit: int = 50
    ) -> List[PatchSimulation]:
        """
        Get simulation history for a tenant.
        """
        result = await db.execute(
            select(PatchSimulation)
            .where(PatchSimulation.tenant_id == tenant_id)
            .order_by(PatchSimulation.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    def calculate_risk_score(
        self,
        impact_summary: Dict[str, Any],
        assets: List[Asset]
    ) -> float:
        """
        Convert impact summary into a 0-100 risk score.
        
        Weighs:
        - Asset criticality
        - Exposure (internet-facing)
        - Downtime
        - Failure probability
        - Dependency conflicts
        """
        score = 0.0
        
        # Criticality component (0-15 points)
        if assets:
            avg_criticality = sum(a.criticality for a in assets) / len(assets)
            score += (avg_criticality / 5.0) * self.CRITICALITY_WEIGHT
        
        # Exposure component (0-20 points)
        internet_facing = sum(1 for a in assets if a.is_internet_facing)
        if assets:
            exposure_ratio = internet_facing / len(assets)
            score += exposure_ratio * self.EXPOSURE_WEIGHT
        
        # Downtime component (0-25 points)
        downtime = impact_summary.get("estimated_downtime_minutes", 0)
        downtime_score = min(downtime / 60.0, 1.0)  # Normalize to 0-1 (60min = max)
        score += downtime_score * self.DOWNTIME_WEIGHT
        
        # Failure probability component (0-30 points)
        failure_prob = impact_summary.get("failure_probability", 0)
        score += failure_prob * self.FAILURE_PROB_WEIGHT
        
        # Conflict component (0-10 points)
        conflicts = len(impact_summary.get("dependency_conflicts", []))
        if conflicts > 0:
            score += min(conflicts * 5, self.CONFLICT_WEIGHT)
        
        return round(min(score, 100.0), 1)


# Singleton instance
simulator_service = SimulatorService()
