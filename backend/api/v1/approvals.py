"""
Approval workflow API endpoints.

Handles approval request creation, approval/rejection actions,
policy management, and approval statistics.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.approval import (
    ApprovalRequest,
    ApprovalAction,
    ApprovalPolicy,
    ApprovalStatus,
    RiskLevel,
)
from backend.models.user import User, UserRole
from backend.services.approval_service import approval_service
from backend.core.auth_workos import get_current_user, require_role


router = APIRouter()


# Pydantic schemas

class ApprovalRequestCreate(BaseModel):
    """Schema for creating an approval request."""
    bundle_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    impact_summary: Optional[Dict[str, Any]] = None


class ApprovalActionCreate(BaseModel):
    """Schema for approval/rejection actions."""
    comment: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    """Schema for approval request response."""
    id: UUID
    bundle_id: UUID
    tenant_id: UUID
    requester_id: UUID
    title: str
    description: Optional[str]
    risk_level: RiskLevel
    status: ApprovalStatus
    required_approvals: int
    current_approvals: int
    impact_summary: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    approved_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApprovalActionResponse(BaseModel):
    """Schema for approval action response."""
    id: UUID
    approval_request_id: Optional[UUID]
    bundle_id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    status: ApprovalStatus
    comment: Optional[str]
    created_at: datetime
    acted_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApprovalPolicyCreate(BaseModel):
    """Schema for creating an approval policy."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    risk_level: RiskLevel
    required_approvals: int = Field(default=1, ge=1)
    required_roles: Optional[List[str]] = None
    auto_approve_low_risk: bool = False
    escalation_hours: int = Field(default=48, ge=1)


class ApprovalPolicyUpdate(BaseModel):
    """Schema for updating an approval policy."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    required_approvals: Optional[int] = Field(None, ge=1)
    required_roles: Optional[List[str]] = None
    auto_approve_low_risk: Optional[bool] = None
    escalation_hours: Optional[int] = Field(None, ge=1)


class ApprovalPolicyResponse(BaseModel):
    """Schema for approval policy response."""
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    risk_level: RiskLevel
    required_approvals: int
    required_roles: Optional[List[str]]
    auto_approve_low_risk: bool
    escalation_hours: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApprovalStatsResponse(BaseModel):
    """Schema for approval statistics."""
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    expired_requests: int
    avg_approval_time_hours: Optional[float]
    by_risk_level: Dict[str, int]


# API Endpoints

@router.post("/approvals", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request: ApprovalRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new approval request for a bundle.
    
    The risk level is automatically assessed if not provided.
    Required approvals are determined by tenant policies.
    """
    try:
        approval_request = await approval_service.create_approval_request(
            db=db,
            bundle_id=request.bundle_id,
            tenant_id=current_user.tenant_id,
            requester_id=current_user.id,
            title=request.title,
            description=request.description,
            risk_level=request.risk_level,
            impact_summary=request.impact_summary,
        )
        
        await db.commit()
        await db.refresh(approval_request)
        
        return approval_request
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/approvals", response_model=List[ApprovalRequestResponse])
async def list_approval_requests(
    status_filter: Optional[ApprovalStatus] = Query(None, description="Filter by status"),
    risk_level_filter: Optional[RiskLevel] = Query(None, description="Filter by risk level"),
    pending_only: bool = Query(False, description="Only show pending approvals I can act on"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List approval requests for the current user's tenant.
    
    Can filter by status, risk level, or only show pending requests
    the current user can approve.
    """
    query = select(ApprovalRequest).where(
        ApprovalRequest.tenant_id == current_user.tenant_id
    ).options(
        selectinload(ApprovalRequest.bundle),
        selectinload(ApprovalRequest.requester),
        selectinload(ApprovalRequest.actions),
    )
    
    # Apply filters
    if status_filter:
        query = query.where(ApprovalRequest.status == status_filter)
    
    if risk_level_filter:
        query = query.where(ApprovalRequest.risk_level == risk_level_filter)
    
    if pending_only:
        # Get only pending requests the user can approve
        requests = await approval_service.get_pending_approvals(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return requests
    
    query = query.order_by(ApprovalRequest.created_at.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    return list(requests)


@router.get("/approvals/{approval_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    approval_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific approval request."""
    result = await db.execute(
        select(ApprovalRequest)
        .where(
            and_(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.tenant_id == current_user.tenant_id,
            )
        )
        .options(
            selectinload(ApprovalRequest.bundle),
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.actions),
        )
    )
    
    approval_request = result.scalar_one_or_none()
    
    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    return approval_request


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalActionResponse)
async def approve_request(
    approval_id: UUID,
    action: ApprovalActionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve an approval request.
    
    Requires ADMIN or APPROVER role, or role specified in policy.
    """
    try:
        approval_action = await approval_service.approve_request(
            db=db,
            approval_request_id=approval_id,
            user_id=current_user.id,
            comment=action.comment,
        )
        
        await db.commit()
        await db.refresh(approval_action)
        
        return approval_action
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalActionResponse)
async def reject_request(
    approval_id: UUID,
    action: ApprovalActionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject an approval request.
    
    Requires ADMIN or APPROVER role, or role specified in policy.
    A single rejection immediately rejects the entire request.
    """
    try:
        approval_action = await approval_service.reject_request(
            db=db,
            approval_request_id=approval_id,
            user_id=current_user.id,
            comment=action.comment,
        )
        
        await db.commit()
        await db.refresh(approval_action)
        
        return approval_action
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Policy Management

@router.get("/approvals/policies", response_model=List[ApprovalPolicyResponse])
async def list_approval_policies(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    List approval policies for the tenant.
    
    Only accessible to ADMIN users.
    """
    result = await db.execute(
        select(ApprovalPolicy)
        .where(ApprovalPolicy.tenant_id == current_user.tenant_id)
        .order_by(ApprovalPolicy.risk_level, ApprovalPolicy.created_at.desc())
    )
    
    policies = result.scalars().all()
    return list(policies)


@router.post("/approvals/policies", response_model=ApprovalPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_policy(
    policy: ApprovalPolicyCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new approval policy.
    
    Only accessible to ADMIN users.
    """
    # Validate roles if provided
    if policy.required_roles:
        valid_roles = [role.value for role in UserRole]
        invalid_roles = [r for r in policy.required_roles if r not in valid_roles]
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {invalid_roles}"
            )
    
    new_policy = ApprovalPolicy(
        tenant_id=current_user.tenant_id,
        name=policy.name,
        description=policy.description,
        risk_level=policy.risk_level,
        required_approvals=policy.required_approvals,
        required_roles=policy.required_roles,
        auto_approve_low_risk=policy.auto_approve_low_risk,
        escalation_hours=policy.escalation_hours,
    )
    
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    
    return new_policy


@router.patch("/approvals/policies/{policy_id}", response_model=ApprovalPolicyResponse)
async def update_approval_policy(
    policy_id: UUID,
    policy_update: ApprovalPolicyUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an approval policy.
    
    Only accessible to ADMIN users.
    """
    result = await db.execute(
        select(ApprovalPolicy).where(
            and_(
                ApprovalPolicy.id == policy_id,
                ApprovalPolicy.tenant_id == current_user.tenant_id,
            )
        )
    )
    
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    # Update fields
    update_data = policy_update.model_dump(exclude_unset=True)
    
    # Validate roles if provided
    if "required_roles" in update_data and update_data["required_roles"]:
        valid_roles = [role.value for role in UserRole]
        invalid_roles = [r for r in update_data["required_roles"] if r not in valid_roles]
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {invalid_roles}"
            )
    
    for field, value in update_data.items():
        setattr(policy, field, value)
    
    policy.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(policy)
    
    return policy


# Statistics

@router.get("/approvals/stats", response_model=ApprovalStatsResponse)
async def get_approval_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get approval statistics for the tenant.
    
    Includes counts by status, risk level, and average approval time.
    """
    # Get all requests for tenant
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == current_user.tenant_id
        )
    )
    requests = result.scalars().all()
    
    # Calculate stats
    total_requests = len(requests)
    pending_requests = sum(1 for r in requests if r.status == ApprovalStatus.PENDING)
    approved_requests = sum(1 for r in requests if r.status == ApprovalStatus.APPROVED)
    rejected_requests = sum(1 for r in requests if r.status == ApprovalStatus.REJECTED)
    expired_requests = sum(1 for r in requests if r.status == ApprovalStatus.EXPIRED)
    
    # Calculate average approval time
    approval_times = [
        (r.approved_at - r.created_at).total_seconds() / 3600
        for r in requests
        if r.status == ApprovalStatus.APPROVED and r.approved_at
    ]
    avg_approval_time = sum(approval_times) / len(approval_times) if approval_times else None
    
    # Count by risk level
    by_risk_level = {}
    for risk_level in RiskLevel:
        by_risk_level[risk_level.value] = sum(
            1 for r in requests if r.risk_level == risk_level
        )
    
    return ApprovalStatsResponse(
        total_requests=total_requests,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        rejected_requests=rejected_requests,
        expired_requests=expired_requests,
        avg_approval_time_hours=avg_approval_time,
        by_risk_level=by_risk_level,
    )
