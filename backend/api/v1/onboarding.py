"""
Onboarding API endpoints.

Handles tenant onboarding flow with multi-step wizard support.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.core.auth_workos import get_current_user


router = APIRouter()


# Pydantic models
class OnboardingStatus(BaseModel):
    onboarding_completed: bool
    onboarding_step: int
    onboarding_data: Optional[Dict[str, Any]] = None
    tenant_id: str
    tenant_name: str


class StepData(BaseModel):
    data: Dict[str, Any]


class StepResponse(BaseModel):
    success: bool
    current_step: int
    message: str


class CompleteResponse(BaseModel):
    success: bool
    message: str
    redirect_to: str = "/"


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current onboarding state for the tenant.
    
    Returns:
        OnboardingStatus with current step and data
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return OnboardingStatus(
        onboarding_completed=tenant.onboarding_completed,
        onboarding_step=tenant.onboarding_step,
        onboarding_data=tenant.onboarding_data,
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
    )


@router.post("/step/{step_number}", response_model=StepResponse)
async def save_step(
    step_number: int,
    step_data: StepData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save step data and advance to next step.
    
    Steps:
    1. Organization Setup - tenant name, industry, size
    2. Connect Your Tools - connection creation
    3. Asset Discovery - trigger discovery scan
    4. Create First Goal - create patching goal
    5. Schedule Setup - create maintenance window
    6. Review & Launch - confirmation
    
    Args:
        step_number: Step number (1-6)
        step_data: Data for this step
        
    Returns:
        StepResponse with updated step number
    """
    if step_number < 1 or step_number > 6:
        raise HTTPException(status_code=400, detail="Invalid step number (must be 1-6)")
    
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Initialize onboarding_data if None
    if tenant.onboarding_data is None:
        tenant.onboarding_data = {}
    
    # Save step data
    tenant.onboarding_data[f"step_{step_number}"] = {
        **step_data.data,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Handle step-specific actions
    if step_number == 1:
        # Organization Setup - update tenant name if provided
        if "tenant_name" in step_data.data:
            tenant.name = step_data.data["tenant_name"]

    elif step_number == 2:
        # Connect Tools — create Connection records for each configured provider
        connections_data = step_data.data.get("connections", [])
        if connections_data:
            from backend.models.connection import Connection
            for conn_info in connections_data:
                provider = conn_info.get("provider")
                if not provider:
                    continue
                connection = Connection(
                    tenant_id=tenant.id,
                    provider=provider,
                    name=conn_info.get("name", f"{provider.upper()} Production"),
                    config=conn_info.get("config", {}),
                    status="pending",
                )
                db.add(connection)

    elif step_number == 4:
        # Create Goal record
        goal_info = step_data.data.get("goal", {})
        if goal_info.get("name"):
            from backend.models.goal import Goal
            from datetime import datetime, timezone as tz
            target_date = None
            if goal_info.get("target_date"):
                try:
                    target_date = datetime.fromisoformat(goal_info["target_date"]).replace(tzinfo=tz.utc)
                except Exception:
                    pass
            goal = Goal(
                tenant_id=tenant.id,
                name=goal_info["name"],
                description=goal_info.get("description", ""),
                goal_type=step_data.data.get("template", "TIME_BASED").upper().replace("-", "_"),
                target_completion_date=target_date,
            )
            db.add(goal)
            await db.flush()
            # Store goal_id back in onboarding data
            tenant.onboarding_data[f"step_{step_number}"]["goal_id"] = str(goal.id)

    elif step_number == 5:
        # Create MaintenanceWindow if weekly_enabled
        if step_data.data.get("weekly_enabled"):
            from backend.models.maintenance_window import MaintenanceWindow
            from datetime import datetime, timezone as tz, timedelta
            day_name = step_data.data.get("weekly_day", "Sunday")
            start_hour_str = step_data.data.get("weekly_start_hour", "02:00")
            duration_hours = int(step_data.data.get("weekly_duration", 4))
            environment = step_data.data.get("environment", "production")

            # Compute next occurrence of the given day/time
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            target_weekday = days_of_week.index(day_name) if day_name in days_of_week else 6
            now = datetime.now(tz.utc)
            hour, minute = (int(x) for x in start_hour_str.split(":"))
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 and (now.hour, now.minute) >= (hour, minute):
                days_ahead = 7
            next_start = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            next_end = next_start + timedelta(hours=duration_hours)

            mw = MaintenanceWindow(
                tenant_id=tenant.id,
                name="Weekly Maintenance",
                type="scheduled",
                start_time=next_start,
                end_time=next_end,
                timezone="America/New_York",
                environment=environment,
                max_duration_hours=float(duration_hours),
            )
            db.add(mw)

    # Update step number to the next step (but don't mark complete yet)
    tenant.onboarding_step = step_number
    
    await db.commit()
    await db.refresh(tenant)
    
    return StepResponse(
        success=True,
        current_step=tenant.onboarding_step,
        message=f"Step {step_number} saved successfully",
    )


@router.post("/complete", response_model=CompleteResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark onboarding as complete.
    
    Returns:
        CompleteResponse with redirect URL
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Mark as completed
    tenant.onboarding_completed = True
    tenant.onboarding_step = 6  # All steps done
    
    await db.commit()
    
    return CompleteResponse(
        success=True,
        message="Onboarding completed successfully",
        redirect_to="/",
    )


@router.post("/skip", response_model=CompleteResponse)
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Skip onboarding and mark as complete without data.
    
    Returns:
        CompleteResponse with redirect URL
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Mark as completed (skipped)
    tenant.onboarding_completed = True
    tenant.onboarding_step = 0  # Indicates skipped
    
    await db.commit()
    
    return CompleteResponse(
        success=True,
        message="Onboarding skipped",
        redirect_to="/",
    )
