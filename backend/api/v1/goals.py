"""
Goals API endpoints.

The secret sauce - converts business objectives into optimized patch schedules
using constraint solving.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict
from uuid import UUID
import json
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.goal import Goal
from backend.models.tenant import Tenant
from backend.models.bundle import Bundle
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.services.optimization import OptimizationService
from backend.services.scoring import scoring_service


router = APIRouter()


class GoalType(str, Enum):
    COMPLIANCE_DEADLINE = "compliance_deadline"
    RISK_REDUCTION = "risk_reduction"
    ZERO_CRITICAL = "zero_critical"
    KEV_ELIMINATION = "kev_elimination"
    CUSTOM = "custom"


class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class GoalCreate(BaseModel):
    """Request model for creating a goal."""
    name: str = Field(..., min_length=1, max_length=200)
    type: GoalType
    description: Optional[str] = None
    
    # Target parameters
    target_date: Optional[datetime] = Field(None, description="When goal should be achieved")
    target_metric: Optional[str] = Field(None, description="Metric to optimize (e.g., 'risk_score', 'vuln_count')")
    target_value: Optional[float] = Field(None, description="Target value for metric")
    
    # Constraints
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    max_vulns_per_window: int = Field(10, ge=1, le=100, description="Max vulnerabilities per maintenance window")
    max_downtime_hours: float = Field(4.0, ge=0.5, le=24.0, description="Max downtime per window")
    require_vendor_approval: bool = Field(False, description="Wait for vendor patches")
    min_patch_weather_score: int = Field(60, ge=0, le=100, description="Minimum Patch Weather score")
    
    # Scope
    asset_filters: Dict[str, Any] = Field(default_factory=dict, description="Filter which assets to include")
    vulnerability_filters: Dict[str, Any] = Field(default_factory=dict, description="Filter which vulnerabilities to include")
    
    @validator('target_date')
    def target_date_future(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError("Target date must be in the future")
        return v


class GoalUpdate(BaseModel):
    """Request model for updating a goal."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    active: Optional[bool] = None
    risk_tolerance: Optional[RiskTolerance] = None
    max_vulns_per_window: Optional[int] = Field(None, ge=1, le=100)
    max_downtime_hours: Optional[float] = Field(None, ge=0.5, le=24.0)
    require_vendor_approval: Optional[bool] = None
    min_patch_weather_score: Optional[int] = Field(None, ge=0, le=100)


class GoalResponse(BaseModel):
    """Response model for a goal."""
    id: UUID
    tenant_id: UUID
    name: str
    type: GoalType
    description: Optional[str]
    active: bool
    
    # Progress
    progress_percentage: float = 0.0
    vulnerabilities_total: int = 0
    vulnerabilities_addressed: int = 0
    risk_score_initial: float = 0.0
    risk_score_current: float = 0.0
    
    # Target
    target_date: Optional[datetime] = None
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    
    # Constraints
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    max_vulns_per_window: Optional[int] = None
    max_downtime_hours: Optional[float] = None
    require_vendor_approval: bool = False
    min_patch_weather_score: Optional[int] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Optimization results
    next_bundle_id: Optional[UUID] = None
    next_bundle_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None


class OptimizationRequest(BaseModel):
    """Request to optimize schedule for a goal."""
    force_reoptimize: bool = Field(False, description="Force reoptimization even if recent plan exists")
    preview_only: bool = Field(False, description="Only preview the plan without creating bundles")
    max_future_windows: int = Field(12, ge=1, le=52, description="How many future windows to plan")


class OptimizationResponse(BaseModel):
    """Response from optimization engine."""
    goal_id: UUID
    success: bool
    message: str
    
    # Statistics
    vulnerabilities_scheduled: int
    bundles_created: int
    estimated_completion_date: Optional[datetime]
    total_risk_reduction: float
    
    # Schedule preview
    schedule: List[Dict[str, Any]]  # List of planned bundles with dates
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)


@router.post("", response_model=GoalResponse)
async def create_goal(
    goal_data: GoalCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    optimization_service: OptimizationService = Depends(),
) -> GoalResponse:
    """
    Create a new optimization goal.
    
    This is where business objectives are translated into technical requirements.
    The optimization service will create an optimal patch schedule.
    """
    # Validate goal type and requirements
    if goal_data.type == GoalType.COMPLIANCE_DEADLINE and not goal_data.target_date:
        raise HTTPException(400, "Compliance deadline goals require a target date")
    
    if goal_data.type == GoalType.RISK_REDUCTION and not goal_data.target_value:
        raise HTTPException(400, "Risk reduction goals require a target risk score")
    
    # Create goal record
    goal = Goal(
        tenant_id=tenant.id,
        name=goal_data.name,
        type=goal_data.type.value,
        description=goal_data.description,
        active=True,
        
        # Target
        target_date=goal_data.target_date,
        target_metric=goal_data.target_metric,
        target_value=goal_data.target_value,
        
        # Constraints  
        risk_tolerance=goal_data.risk_tolerance.value,
        max_vulns_per_window=goal_data.max_vulns_per_window,
        max_downtime_hours=goal_data.max_downtime_hours,
        require_vendor_approval=goal_data.require_vendor_approval,
        min_patch_weather_score=goal_data.min_patch_weather_score,
        
        # Scope
        asset_filters=goal_data.asset_filters,
        vulnerability_filters=goal_data.vulnerability_filters,
        
        # Progress (calculated)
        progress_percentage=0.0,
        vulnerabilities_total=0,
        vulnerabilities_addressed=0,
        risk_score_initial=0.0,
        risk_score_current=0.0,
    )
    
    db.add(goal)
    await db.flush()
    
    # Calculate initial metrics
    initial_metrics = await optimization_service.calculate_goal_metrics(db, goal)
    goal.vulnerabilities_total = initial_metrics["vulnerabilities_total"]
    goal.risk_score_initial = initial_metrics["risk_score_total"]
    goal.risk_score_current = initial_metrics["risk_score_total"]
    
    await db.commit()
    
    # Return enriched response
    return GoalResponse(
        id=goal.id,
        tenant_id=goal.tenant_id,
        name=goal.name,
        type=GoalType(goal.type) if goal.type else GoalType.CUSTOM,
        description=goal.description,
        active=goal.active,
        
        progress_percentage=goal.progress_percentage,
        vulnerabilities_total=goal.vulnerabilities_total,
        vulnerabilities_addressed=goal.vulnerabilities_addressed,
        risk_score_initial=goal.risk_score_initial,
        risk_score_current=goal.risk_score_current,
        
        target_date=goal.target_date,
        target_metric=goal.target_metric,
        target_value=goal.target_value,
        
        risk_tolerance=RiskTolerance(goal.risk_tolerance) if goal.risk_tolerance else RiskTolerance.BALANCED,
        max_vulns_per_window=goal.max_vulns_per_window,
        max_downtime_hours=goal.max_downtime_hours,
        require_vendor_approval=goal.require_vendor_approval,
        min_patch_weather_score=goal.min_patch_weather_score,
        
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        completed_at=goal.completed_at,
        
        next_bundle_id=None,
        next_bundle_date=None,
        estimated_completion_date=None,
    )


@router.get("/", response_model=List[GoalResponse])
async def list_goals(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    active_only: bool = Query(True, description="Only show active goals"),
    type: Optional[GoalType] = Query(None, description="Filter by goal type"),
) -> List[GoalResponse]:
    """
    List all goals for the current tenant.
    
    Returns goals with their current progress and next scheduled actions.
    """
    query = select(Goal).where(Goal.tenant_id == tenant.id)
    
    if active_only:
        query = query.where(Goal.active == True)
    
    if type:
        query = query.where(Goal.type == type.value)
    
    query = query.order_by(Goal.created_at.desc())
    
    result = await db.execute(query)
    goals = result.scalars().all()
    
    # Enrich with next bundle info
    responses = []
    for goal in goals:
        # Get next bundle
        next_bundle_result = await db.execute(
            select(Bundle)
            .where(
                and_(
                    Bundle.goal_id == goal.id,
                    Bundle.status == "scheduled",
                )
            )
            .order_by(Bundle.scheduled_for)
            .limit(1)
        )
        next_bundle = next_bundle_result.scalar_one_or_none()
        
        responses.append(GoalResponse(
            id=goal.id,
            tenant_id=goal.tenant_id,
            name=goal.name,
            type=GoalType(goal.type) if goal.type else GoalType.CUSTOM,
            description=goal.description,
            active=goal.active,
            
            progress_percentage=goal.progress_percentage,
            vulnerabilities_total=goal.vulnerabilities_total,
            vulnerabilities_addressed=goal.vulnerabilities_addressed,
            risk_score_initial=goal.risk_score_initial,
            risk_score_current=goal.risk_score_current,
            
            target_date=goal.target_date,
            target_metric=goal.target_metric,
            target_value=goal.target_value,
            
            risk_tolerance=RiskTolerance(goal.risk_tolerance) if goal.risk_tolerance else RiskTolerance.BALANCED,
            max_vulns_per_window=goal.max_vulns_per_window,
            max_downtime_hours=goal.max_downtime_hours,
            require_vendor_approval=goal.require_vendor_approval,
            min_patch_weather_score=goal.min_patch_weather_score,
            
            created_at=goal.created_at,
            updated_at=goal.updated_at,
            completed_at=goal.completed_at,
            
            next_bundle_id=next_bundle.id if next_bundle else None,
            next_bundle_date=next_bundle.scheduled_for if next_bundle else None,
            estimated_completion_date=goal.estimated_completion_date,
        ))
    
    return responses


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> GoalResponse:
    """Get details for a specific goal."""
    result = await db.execute(
        select(Goal).where(
            and_(
                Goal.id == goal_id,
                Goal.tenant_id == tenant.id
            )
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(404, "Goal not found")
    
    # Get next bundle
    next_bundle_result = await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.goal_id == goal.id,
                Bundle.status == "scheduled",
            )
        )
        .order_by(Bundle.scheduled_for)
        .limit(1)
    )
    next_bundle = next_bundle_result.scalar_one_or_none()
    
    return GoalResponse(
        id=goal.id,
        tenant_id=goal.tenant_id,
        name=goal.name,
        type=GoalType(goal.type) if goal.type else GoalType.CUSTOM,
        description=goal.description,
        active=goal.active,
        
        progress_percentage=goal.progress_percentage,
        vulnerabilities_total=goal.vulnerabilities_total,
        vulnerabilities_addressed=goal.vulnerabilities_addressed,
        risk_score_initial=goal.risk_score_initial,
        risk_score_current=goal.risk_score_current,
        
        target_date=goal.target_date,
        target_metric=goal.target_metric,
        target_value=goal.target_value,
        
        risk_tolerance=RiskTolerance(goal.risk_tolerance) if goal.risk_tolerance else RiskTolerance.BALANCED,
        max_vulns_per_window=goal.max_vulns_per_window,
        max_downtime_hours=goal.max_downtime_hours,
        require_vendor_approval=goal.require_vendor_approval,
        min_patch_weather_score=goal.min_patch_weather_score,
        
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        completed_at=goal.completed_at,
        
        next_bundle_id=next_bundle.id if next_bundle else None,
        next_bundle_date=next_bundle.scheduled_for if next_bundle else None,
        estimated_completion_date=goal.estimated_completion_date,
    )


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    updates: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> GoalResponse:
    """Update a goal's configuration."""
    result = await db.execute(
        select(Goal).where(
            and_(
                Goal.id == goal_id,
                Goal.tenant_id == tenant.id
            )
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(404, "Goal not found")
    
    # Apply updates
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    goal.updated_at = datetime.utcnow()
    await db.commit()
    
    # Get next bundle for response
    next_bundle_result = await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.goal_id == goal.id,
                Bundle.status == "scheduled",
            )
        )
        .order_by(Bundle.scheduled_for)
        .limit(1)
    )
    next_bundle = next_bundle_result.scalar_one_or_none()
    
    return GoalResponse(
        id=goal.id,
        tenant_id=goal.tenant_id,
        name=goal.name,
        type=GoalType(goal.type) if goal.type else GoalType.CUSTOM,
        description=goal.description,
        active=goal.active,
        
        progress_percentage=goal.progress_percentage,
        vulnerabilities_total=goal.vulnerabilities_total,
        vulnerabilities_addressed=goal.vulnerabilities_addressed,
        risk_score_initial=goal.risk_score_initial,
        risk_score_current=goal.risk_score_current,
        
        target_date=goal.target_date,
        target_metric=goal.target_metric,
        target_value=goal.target_value,
        
        risk_tolerance=RiskTolerance(goal.risk_tolerance) if goal.risk_tolerance else RiskTolerance.BALANCED,
        max_vulns_per_window=goal.max_vulns_per_window,
        max_downtime_hours=goal.max_downtime_hours,
        require_vendor_approval=goal.require_vendor_approval,
        min_patch_weather_score=goal.min_patch_weather_score,
        
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        completed_at=goal.completed_at,
        
        next_bundle_id=next_bundle.id if next_bundle else None,
        next_bundle_date=next_bundle.scheduled_for if next_bundle else None,
        estimated_completion_date=goal.estimated_completion_date,
    )


@router.post("/{goal_id}/optimize", response_model=OptimizationResponse)
async def optimize_goal(
    goal_id: UUID,
    request: OptimizationRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    optimization_service: OptimizationService = Depends(),
) -> OptimizationResponse:
    """
    Run the optimization engine for a goal.
    
    This is where the magic happens - constraint solving to create an optimal
    patch schedule that meets business objectives while respecting constraints.
    """
    # Get goal
    result = await db.execute(
        select(Goal).where(
            and_(
                Goal.id == goal_id,
                Goal.tenant_id == tenant.id
            )
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(404, "Goal not found")
    
    if not goal.active:
        raise HTTPException(400, "Cannot optimize inactive goal")
    
    # Check if recent optimization exists
    if not request.force_reoptimize:
        recent_bundle = await db.execute(
            select(Bundle)
            .where(
                and_(
                    Bundle.goal_id == goal.id,
                    Bundle.created_at > datetime.utcnow() - timedelta(hours=24)
                )
            )
            .limit(1)
        )
        if recent_bundle.scalar_one_or_none():
            return OptimizationResponse(
                goal_id=goal.id,
                success=False,
                message="Recent optimization exists. Use force_reoptimize=true to regenerate.",
                vulnerabilities_scheduled=0,
                bundles_created=0,
                estimated_completion_date=None,
                total_risk_reduction=0.0,
                schedule=[],
                warnings=["Optimization skipped - recent plan exists"],
            )
    
    # Run optimization
    try:
        result = await optimization_service.optimize_goal(
            db=db,
            goal=goal,
            preview_only=request.preview_only,
            max_future_windows=request.max_future_windows,
        )
        
        return OptimizationResponse(
            goal_id=goal.id,
            success=result["success"],
            message=result["message"],
            vulnerabilities_scheduled=result["vulnerabilities_scheduled"],
            bundles_created=result["bundles_created"],
            estimated_completion_date=result["estimated_completion_date"],
            total_risk_reduction=result["total_risk_reduction"],
            schedule=result["schedule"],
            warnings=result.get("warnings", []),
        )
        
    except Exception as e:
        return OptimizationResponse(
            goal_id=goal.id,
            success=False,
            message=f"Optimization failed: {str(e)}",
            vulnerabilities_scheduled=0,
            bundles_created=0,
            estimated_completion_date=None,
            total_risk_reduction=0.0,
            schedule=[],
            warnings=[f"Error: {str(e)}"],
        )


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Delete a goal.
    
    This will also cancel any scheduled bundles associated with the goal.
    """
    result = await db.execute(
        select(Goal).where(
            and_(
                Goal.id == goal_id,
                Goal.tenant_id == tenant.id
            )
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(404, "Goal not found")
    
    # Cancel scheduled bundles
    await db.execute(
        select(Bundle)
        .where(
            and_(
                Bundle.goal_id == goal.id,
                Bundle.status == "scheduled"
            )
        )
        .update({"status": "cancelled"})
    )
    
    # Delete goal
    await db.delete(goal)
    await db.commit()
    
    return {"message": f"Goal '{goal.name}' deleted successfully"}