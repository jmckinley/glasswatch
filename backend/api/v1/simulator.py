"""
Patch simulator API endpoints.

Provides impact prediction and dry-run simulation capabilities.
"""
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.simulation import PatchSimulation
from backend.models.tenant import Tenant
from backend.core.auth import get_current_tenant
from backend.services.simulator_service import simulator_service


router = APIRouter()


# Request models
class PredictImpactRequest(BaseModel):
    """Request to predict patch impact."""
    bundle_id: UUID


class DryRunRequest(BaseModel):
    """Request to run dry-run simulation."""
    bundle_id: UUID


@router.post("/predict")
async def predict_impact(
    request: PredictImpactRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Predict patch impact for a bundle.
    
    Analyzes affected assets, services, downtime, risks, and generates recommendations.
    """
    try:
        simulation = await simulator_service.predict_impact(
            db=db,
            bundle_id=request.bundle_id,
            tenant_id=tenant.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to predict impact: {str(e)}")
    
    return {
        "id": str(simulation.id),
        "bundle_id": str(simulation.bundle_id),
        "status": simulation.status.value,
        "risk_score": simulation.risk_score,
        "risk_level": simulation.risk_level,
        "impact_summary": simulation.impact_summary,
        "is_safe_to_proceed": simulation.is_safe_to_proceed,
        "created_at": simulation.created_at.isoformat(),
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None
    }


@router.post("/dry-run")
async def run_dry_run(
    request: DryRunRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Run dry-run simulation for a bundle.
    
    Validates package availability, disk space, connectivity, and maintenance windows.
    Includes full impact prediction plus pre-flight validation.
    """
    try:
        simulation = await simulator_service.run_dry_run(
            db=db,
            bundle_id=request.bundle_id,
            tenant_id=tenant.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run dry-run: {str(e)}")
    
    return {
        "id": str(simulation.id),
        "bundle_id": str(simulation.bundle_id),
        "status": simulation.status.value,
        "risk_score": simulation.risk_score,
        "risk_level": simulation.risk_level,
        "impact_summary": simulation.impact_summary,
        "dry_run_results": simulation.dry_run_results,
        "is_safe_to_proceed": simulation.is_safe_to_proceed,
        "created_at": simulation.created_at.isoformat(),
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None
    }


@router.get("/simulations")
async def list_simulations(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    bundle_id: Optional[UUID] = Query(None, description="Filter by bundle"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum risk score"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List simulations with filtering.
    
    Returns paginated list of simulations for the current tenant.
    """
    # Build query
    query = select(PatchSimulation).where(PatchSimulation.tenant_id == tenant.id)
    
    # Apply filters
    filters = []
    
    if bundle_id:
        filters.append(PatchSimulation.bundle_id == bundle_id)
    
    if status:
        filters.append(PatchSimulation.status == status)
    
    if min_risk_score is not None:
        filters.append(PatchSimulation.risk_score >= min_risk_score)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(PatchSimulation.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    simulations = result.scalars().all()
    
    return {
        "simulations": [
            {
                "id": str(s.id),
                "bundle_id": str(s.bundle_id),
                "status": s.status.value,
                "risk_score": s.risk_score,
                "risk_level": s.risk_level,
                "affected_assets": s.impact_summary.get("affected_assets", 0),
                "estimated_downtime_minutes": s.impact_summary.get("estimated_downtime_minutes", 0),
                "is_safe_to_proceed": s.is_safe_to_proceed,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None
            }
            for s in simulations
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/simulations/{simulation_id}")
async def get_simulation(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get simulation detail.
    
    Returns full simulation including impact analysis and dry-run results.
    """
    result = await db.execute(
        select(PatchSimulation).where(
            and_(
                PatchSimulation.id == simulation_id,
                PatchSimulation.tenant_id == tenant.id
            )
        )
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {
        "id": str(simulation.id),
        "bundle_id": str(simulation.bundle_id),
        "tenant_id": str(simulation.tenant_id),
        "status": simulation.status.value,
        "risk_score": simulation.risk_score,
        "risk_level": simulation.risk_level,
        "impact_summary": simulation.impact_summary,
        "dry_run_results": simulation.dry_run_results,
        "is_safe_to_proceed": simulation.is_safe_to_proceed,
        "created_at": simulation.created_at.isoformat(),
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None
    }
