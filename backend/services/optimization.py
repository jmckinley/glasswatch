"""
Optimization service for goal-based patch scheduling.

This is the secret sauce - uses OR-Tools constraint solver to find optimal
patch schedules that meet business objectives.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID, uuid4
import logging

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.goal import Goal
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.maintenance_window import MaintenanceWindow
from backend.services.scoring import scoring_service

# Try to import OR-Tools, but gracefully handle if not installed
try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools not available. Optimization will use heuristic algorithm.")


logger = logging.getLogger(__name__)


class OptimizationService:
    """
    Converts business goals into optimal patch schedules.
    
    This is what sets Glasswatch apart - intelligent scheduling that
    balances risk, downtime, and business objectives.
    """
    
    async def calculate_goal_metrics(
        self,
        db: AsyncSession,
        goal: Goal
    ) -> Dict[str, Any]:
        """Calculate current metrics for a goal."""
        # Get vulnerabilities in scope
        vuln_query = select(AssetVulnerability).join(Asset).join(Vulnerability)
        vuln_query = vuln_query.where(Asset.tenant_id == goal.tenant_id)
        
        # Apply asset filters
        if goal.asset_filters:
            if "type" in goal.asset_filters:
                vuln_query = vuln_query.where(Asset.type == goal.asset_filters["type"])
            if "environment" in goal.asset_filters:
                vuln_query = vuln_query.where(Asset.environment == goal.asset_filters["environment"])
            if "criticality_min" in goal.asset_filters:
                vuln_query = vuln_query.where(Asset.criticality >= goal.asset_filters["criticality_min"])
        
        # Apply vulnerability filters
        if goal.vulnerability_filters:
            if "severity" in goal.vulnerability_filters:
                vuln_query = vuln_query.where(Vulnerability.severity.in_(goal.vulnerability_filters["severity"]))
            if "kev_only" in goal.vulnerability_filters and goal.vulnerability_filters["kev_only"]:
                vuln_query = vuln_query.where(Vulnerability.kev_listed == True)
        
        result = await db.execute(vuln_query.options(selectinload(AssetVulnerability.vulnerability), selectinload(AssetVulnerability.asset)))
        asset_vulns = result.scalars().all()
        
        # Calculate metrics
        total_vulns = len(asset_vulns)
        total_risk = 0.0
        
        for av in asset_vulns:
            score = scoring_service.calculate_vulnerability_score(
                av.vulnerability,
                av.asset,
                runtime_data=av.runtime_data
            )
            total_risk += score["score"]
        
        return {
            "vulnerabilities_total": total_vulns,
            "risk_score_total": total_risk,
            "asset_vulns": asset_vulns,  # For optimization
        }
    
    async def get_maintenance_windows(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[MaintenanceWindow]:
        """Get available maintenance windows for scheduling."""
        result = await db.execute(
            select(MaintenanceWindow)
            .where(
                and_(
                    MaintenanceWindow.tenant_id == tenant_id,
                    MaintenanceWindow.start_time >= start_date,
                    MaintenanceWindow.end_time <= end_date,
                    MaintenanceWindow.active == True,
                )
            )
            .order_by(MaintenanceWindow.start_time)
        )
        return result.scalars().all()
    
    async def optimize_goal(
        self,
        db: AsyncSession,
        goal: Goal,
        preview_only: bool = False,
        max_future_windows: int = 12
    ) -> Dict[str, Any]:
        """
        Main optimization entry point.
        
        Uses constraint solver to find optimal schedule, falls back to
        heuristic if OR-Tools not available.
        """
        logger.info(f"Starting optimization for goal {goal.id}: {goal.name}")
        
        # Get current metrics and vulnerabilities
        metrics = await self.calculate_goal_metrics(db, goal)
        asset_vulns = metrics["asset_vulns"]
        
        if not asset_vulns:
            return {
                "success": True,
                "message": "No vulnerabilities found in scope",
                "vulnerabilities_scheduled": 0,
                "bundles_created": 0,
                "estimated_completion_date": None,
                "total_risk_reduction": 0.0,
                "schedule": [],
                "warnings": [],
            }
        
        # Get maintenance windows
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(weeks=max_future_windows * 4)  # Roughly months
        windows = await self.get_maintenance_windows(db, goal.tenant_id, start_date, end_date)
        
        if not windows:
            # Create default weekly windows if none exist
            windows = self._create_default_windows(goal.tenant_id, start_date, max_future_windows)
            if not preview_only:
                for window in windows:
                    db.add(window)
                await db.flush()
        
        # Run optimization
        if ORTOOLS_AVAILABLE:
            schedule = await self._optimize_with_constraint_solver(
                goal, asset_vulns, windows
            )
        else:
            schedule = await self._optimize_with_heuristic(
                goal, asset_vulns, windows
            )
        
        # Create bundles if not preview
        bundles_created = 0
        if not preview_only:
            for bundle_data in schedule:
                bundle = await self._create_bundle(db, goal, bundle_data)
                bundles_created += 1
            await db.commit()
        
        # Calculate results
        vulnerabilities_scheduled = sum(len(b["vulnerabilities"]) for b in schedule)
        estimated_completion = schedule[-1]["window"].end_time if schedule else None
        total_risk_reduction = sum(b["risk_reduction"] for b in schedule)
        
        # Format schedule for response
        schedule_preview = []
        for bundle_data in schedule:
            window = bundle_data["window"]
            schedule_preview.append({
                "date": window.start_time.isoformat(),
                "vulnerabilities_count": len(bundle_data["vulnerabilities"]),
                "risk_reduction": bundle_data["risk_reduction"],
                "estimated_duration_hours": bundle_data["duration_hours"],
                "assets_affected": len(bundle_data["affected_assets"]),
            })
        
        return {
            "success": True,
            "message": f"Optimization complete. Scheduled {vulnerabilities_scheduled} vulnerabilities across {len(schedule)} windows.",
            "vulnerabilities_scheduled": vulnerabilities_scheduled,
            "bundles_created": bundles_created,
            "estimated_completion_date": estimated_completion,
            "total_risk_reduction": total_risk_reduction,
            "schedule": schedule_preview,
            "warnings": [],
        }
    
    async def _optimize_with_constraint_solver(
        self,
        goal: Goal,
        asset_vulns: List[AssetVulnerability],
        windows: List[MaintenanceWindow]
    ) -> List[Dict[str, Any]]:
        """
        Use OR-Tools CP-SAT solver for optimal scheduling.
        
        This is the secret sauce - balances multiple objectives:
        - Minimize total risk over time
        - Respect maintenance window constraints
        - Group related vulnerabilities
        - Meet business deadlines
        """
        model = cp_model.CpModel()
        
        # Decision variables: assign vuln i to window j
        assignments = {}
        for i, av in enumerate(asset_vulns):
            for j, window in enumerate(windows):
                assignments[(i, j)] = model.NewBoolVar(f'v{i}_w{j}')
        
        # Constraint 1: Each vulnerability assigned to at most one window
        for i in range(len(asset_vulns)):
            model.Add(sum(assignments[(i, j)] for j in range(len(windows))) <= 1)
        
        # Constraint 2: Window capacity (max vulns per window)
        for j in range(len(windows)):
            model.Add(
                sum(assignments[(i, j)] for i in range(len(asset_vulns))) 
                <= goal.max_vulns_per_window
            )
        
        # Constraint 3: Window duration capacity
        durations = []
        for av in asset_vulns:
            # Estimate 30 minutes per vulnerability (can be refined)
            durations.append(0.5)
        
        for j, window in enumerate(windows):
            window_duration_hours = (window.end_time - window.start_time).total_seconds() / 3600
            model.Add(
                sum(assignments[(i, j)] * int(durations[i] * 100) for i in range(len(asset_vulns)))
                <= int(min(goal.max_downtime_hours, window_duration_hours) * 100)
            )
        
        # Constraint 4: High-risk vulnerabilities first
        # Create ordering constraints for critical vulns
        critical_indices = []
        high_indices = []
        for i, av in enumerate(asset_vulns):
            score = scoring_service.calculate_vulnerability_score(
                av.vulnerability, av.asset, av.runtime_data
            )
            if score["risk_level"] == "CRITICAL":
                critical_indices.append(i)
            elif score["risk_level"] == "HIGH":
                high_indices.append(i)
        
        # Critical before high, high before others
        for c_idx in critical_indices:
            for h_idx in high_indices:
                for j in range(len(windows)):
                    # If high is scheduled in window j, critical must be in j or earlier
                    for k in range(j + 1, len(windows)):
                        model.AddImplication(
                            assignments[(h_idx, k)],
                            assignments[(c_idx, k)].Not()
                        )
        
        # Objective: Minimize risk-time product
        # Each unpatched vulnerability contributes risk for each time period
        objective_terms = []
        for i, av in enumerate(asset_vulns):
            score = scoring_service.calculate_vulnerability_score(
                av.vulnerability, av.asset, av.runtime_data
            )
            risk_score = score["score"]
            
            # Penalty for each window the vuln remains unpatched
            for j in range(len(windows)):
                # If assigned to window j, it's patched after j windows
                penalty = risk_score * j
                objective_terms.append(assignments[(i, j)] * int(penalty))
        
        model.Minimize(sum(objective_terms))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # Limit solving time
        status = solver.Solve(model)
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.warning("Constraint solver found no solution, falling back to heuristic")
            return await self._optimize_with_heuristic(goal, asset_vulns, windows)
        
        # Extract solution
        schedule = []
        for j, window in enumerate(windows):
            vulns_in_window = []
            risk_reduction = 0.0
            affected_assets = set()
            
            for i, av in enumerate(asset_vulns):
                if solver.Value(assignments[(i, j)]):
                    vulns_in_window.append(av)
                    score = scoring_service.calculate_vulnerability_score(
                        av.vulnerability, av.asset, av.runtime_data
                    )
                    risk_reduction += score["score"]
                    affected_assets.add(av.asset_id)
            
            if vulns_in_window:
                schedule.append({
                    "window": window,
                    "vulnerabilities": vulns_in_window,
                    "risk_reduction": risk_reduction,
                    "duration_hours": len(vulns_in_window) * 0.5,  # Estimate
                    "affected_assets": affected_assets,
                })
        
        return schedule
    
    async def _optimize_with_heuristic(
        self,
        goal: Goal,
        asset_vulns: List[AssetVulnerability],
        windows: List[MaintenanceWindow]
    ) -> List[Dict[str, Any]]:
        """
        Fallback heuristic algorithm when OR-Tools not available.
        
        Simple greedy approach:
        1. Sort vulnerabilities by risk score (highest first)
        2. Pack into windows respecting constraints
        3. Group by asset when possible
        """
        # Calculate scores and sort
        scored_vulns = []
        for av in asset_vulns:
            score = scoring_service.calculate_vulnerability_score(
                av.vulnerability, av.asset, av.runtime_data
            )
            scored_vulns.append((score["score"], av))
        
        # Sort by score descending (highest risk first)
        scored_vulns.sort(key=lambda x: x[0], reverse=True)
        
        # Pack into windows
        schedule = []
        window_idx = 0
        current_window_vulns = []
        current_window_duration = 0.0
        current_risk_reduction = 0.0
        affected_assets = set()
        
        for score, av in scored_vulns:
            if window_idx >= len(windows):
                break  # No more windows available
            
            window = windows[window_idx]
            window_duration_limit = min(
                goal.max_downtime_hours,
                (window.end_time - window.start_time).total_seconds() / 3600
            )
            
            # Check if vuln fits in current window
            vuln_duration = 0.5  # 30 minutes estimate
            
            if (len(current_window_vulns) < goal.max_vulns_per_window and
                current_window_duration + vuln_duration <= window_duration_limit):
                # Add to current window
                current_window_vulns.append(av)
                current_window_duration += vuln_duration
                current_risk_reduction += score
                affected_assets.add(av.asset_id)
            else:
                # Save current window and start new one
                if current_window_vulns:
                    schedule.append({
                        "window": window,
                        "vulnerabilities": current_window_vulns,
                        "risk_reduction": current_risk_reduction,
                        "duration_hours": current_window_duration,
                        "affected_assets": affected_assets,
                    })
                
                # Move to next window
                window_idx += 1
                if window_idx < len(windows):
                    window = windows[window_idx]
                    current_window_vulns = [av]
                    current_window_duration = vuln_duration
                    current_risk_reduction = score
                    affected_assets = {av.asset_id}
        
        # Add final window if has vulns
        if current_window_vulns and window_idx < len(windows):
            schedule.append({
                "window": windows[window_idx],
                "vulnerabilities": current_window_vulns,
                "risk_reduction": current_risk_reduction,
                "duration_hours": current_window_duration,
                "affected_assets": affected_assets,
            })
        
        return schedule
    
    async def _create_bundle(
        self,
        db: AsyncSession,
        goal: Goal,
        bundle_data: Dict[str, Any]
    ) -> Bundle:
        """Create a bundle from optimization results."""
        window = bundle_data["window"]
        vulns = bundle_data["vulnerabilities"]
        
        # Create bundle
        bundle = Bundle(
            id=uuid4(),
            tenant_id=goal.tenant_id,
            goal_id=goal.id,
            name=f"Patch Bundle - {window.start_time.strftime('%Y-%m-%d')}",
            status="scheduled",
            scheduled_for=window.start_time,
            maintenance_window_id=window.id,
            risk_score=bundle_data["risk_reduction"],
            estimated_duration_minutes=int(bundle_data["duration_hours"] * 60),
            approval_required=len(bundle_data["affected_assets"]) > 5,  # Example rule
            risk_assessment={
                "total_risk_reduction": bundle_data["risk_reduction"],
                "vulnerabilities_count": len(vulns),
                "assets_affected": len(bundle_data["affected_assets"]),
            },
        )
        db.add(bundle)
        await db.flush()
        
        # Create bundle items
        for av in vulns:
            item = BundleItem(
                bundle_id=bundle.id,
                vulnerability_id=av.vulnerability_id,
                asset_id=av.asset_id,
                status="pending",
                risk_score=scoring_service.calculate_vulnerability_score(
                    av.vulnerability, av.asset, av.runtime_data
                )["score"],
            )
            db.add(item)
        
        return bundle
    
    def _create_default_windows(
        self,
        tenant_id: UUID,
        start_date: datetime,
        count: int
    ) -> List[MaintenanceWindow]:
        """Create default weekly maintenance windows."""
        windows = []
        
        # Start from next Sunday 2 AM
        current = start_date
        while current.weekday() != 6:  # Sunday
            current += timedelta(days=1)
        current = current.replace(hour=2, minute=0, second=0, microsecond=0)
        
        for i in range(count):
            window = MaintenanceWindow(
                tenant_id=tenant_id,
                name=f"Weekly Maintenance - {current.strftime('%Y-%m-%d')}",
                start_time=current,
                end_time=current + timedelta(hours=4),
                type="scheduled",
                active=True,
                max_duration_hours=4.0,
                approved_activities=["patching", "updates"],
            )
            windows.append(window)
            current += timedelta(weeks=1)
        
        return windows