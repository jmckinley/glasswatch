"""
Approval workflow service.

Handles creation, processing, and management of approval requests
for bundle deployments.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from backend.models.approval import (
    ApprovalRequest,
    ApprovalAction,
    ApprovalPolicy,
    ApprovalStatus,
    RiskLevel,
)
from backend.models.bundle import Bundle
from backend.models.user import User, UserRole
from backend.services.notifications import notification_service, NotificationType


class ApprovalService:
    """Service for managing approval workflows."""
    
    async def create_approval_request(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        tenant_id: UUID,
        requester_id: UUID,
        title: str,
        description: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        impact_summary: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request for a bundle.
        
        Automatically determines risk level and required approvals
        based on tenant policies if not specified.
        """
        # Get bundle to assess risk if not provided
        bundle_result = await db.execute(
            select(Bundle).where(Bundle.id == bundle_id)
        )
        bundle = bundle_result.scalar_one_or_none()
        
        if not bundle:
            raise ValueError(f"Bundle {bundle_id} not found")
        
        # Auto-assess risk level if not provided
        if risk_level is None:
            risk_level = await self.auto_assess_risk(db, bundle, tenant_id)
        
        # Get applicable policy
        policy = await self._get_policy_for_risk(db, tenant_id, risk_level)
        
        # Determine required approvals
        required_approvals = policy.required_approvals if policy else 1
        
        # Check for auto-approval
        if policy and policy.auto_approve_low_risk and risk_level == RiskLevel.LOW:
            status = ApprovalStatus.APPROVED
            current_approvals = required_approvals
            approved_at = datetime.now(timezone.utc)
        else:
            status = ApprovalStatus.PENDING
            current_approvals = 0
            approved_at = None
        
        # Calculate expiration (48 hours default)
        escalation_hours = policy.escalation_hours if policy else 48
        expires_at = datetime.now(timezone.utc) + timedelta(hours=escalation_hours)
        
        # Create approval request
        approval_request = ApprovalRequest(
            bundle_id=bundle_id,
            tenant_id=tenant_id,
            requester_id=requester_id,
            title=title,
            description=description,
            risk_level=risk_level,
            status=status,
            required_approvals=required_approvals,
            current_approvals=current_approvals,
            impact_summary=impact_summary or {},
            approved_at=approved_at,
            expires_at=expires_at,
        )
        
        db.add(approval_request)
        await db.flush()
        
        # Send notification if not auto-approved
        if status == ApprovalStatus.PENDING:
            # Get tenant for notifications
            from backend.models.tenant import Tenant
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one()
            
            await notification_service.send_notification(
                tenant=tenant,
                notification_type=NotificationType.APPROVAL_NEEDED,
                title=f"Approval Required: {title}",
                message=f"Bundle '{bundle.name}' requires {required_approvals} approval(s) before deployment.\n\nRisk Level: {risk_level.value.upper()}\nRequested by: {requester_id}",
                data={
                    "approval_request_id": str(approval_request.id),
                    "bundle_id": str(bundle_id),
                    "action_url": f"/approvals/{approval_request.id}",
                },
                priority="high" if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "normal",
            )
        
        return approval_request
    
    async def approve_request(
        self,
        db: AsyncSession,
        approval_request_id: UUID,
        user_id: UUID,
        comment: Optional[str] = None,
    ) -> ApprovalAction:
        """
        Approve an approval request.
        
        Creates an approval action and updates the request status
        if enough approvals have been collected.
        """
        # Get approval request
        result = await db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.actions))
            .where(ApprovalRequest.id == approval_request_id)
        )
        approval_request = result.scalar_one_or_none()
        
        if not approval_request:
            raise ValueError(f"Approval request {approval_request_id} not found")
        
        # Check if already approved/rejected/expired
        if approval_request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request is {approval_request.status}, cannot approve")
        
        # Check if expired
        if approval_request.expires_at and datetime.now(timezone.utc) > approval_request.expires_at:
            approval_request.status = ApprovalStatus.EXPIRED
            await db.flush()
            raise ValueError("Approval request has expired")
        
        # Get user to check permissions
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user has permission to approve
        if not await self._can_approve(db, user, approval_request):
            raise ValueError(f"User does not have permission to approve this request")
        
        # Check if user already approved
        existing_approval = next(
            (a for a in approval_request.actions if a.user_id == user_id and a.status == ApprovalStatus.APPROVED),
            None
        )
        if existing_approval:
            raise ValueError("User has already approved this request")
        
        # Create approval action
        approval_action = ApprovalAction(
            approval_request_id=approval_request_id,
            bundle_id=approval_request.bundle_id,
            tenant_id=approval_request.tenant_id,
            user_id=user_id,
            status=ApprovalStatus.APPROVED,
            comment=comment,
            acted_at=datetime.now(timezone.utc),
        )
        
        db.add(approval_action)
        
        # Update approval request
        approval_request.current_approvals += 1
        approval_request.updated_at = datetime.now(timezone.utc)
        
        # Check if we have enough approvals
        if approval_request.current_approvals >= approval_request.required_approvals:
            approval_request.status = ApprovalStatus.APPROVED
            approval_request.approved_at = datetime.now(timezone.utc)
            
            # Update bundle status
            bundle_result = await db.execute(
                select(Bundle).where(Bundle.id == approval_request.bundle_id)
            )
            bundle = bundle_result.scalar_one()
            bundle.approved_by = user.email
            bundle.approved_at = datetime.now(timezone.utc)
            bundle.status = "approved"
            
            # Send notification
            from backend.models.tenant import Tenant
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == approval_request.tenant_id)
            )
            tenant = tenant_result.scalar_one()
            
            await notification_service.send_notification(
                tenant=tenant,
                notification_type=NotificationType.BUNDLE_READY,
                title=f"Approval Complete: {approval_request.title}",
                message=f"Bundle '{bundle.name}' has been approved and is ready for deployment.\n\nApprovals: {approval_request.current_approvals}/{approval_request.required_approvals}",
                data={
                    "approval_request_id": str(approval_request_id),
                    "bundle_id": str(approval_request.bundle_id),
                    "action_url": f"/bundles/{approval_request.bundle_id}",
                },
                priority="normal",
            )
        
        await db.flush()
        
        return approval_action
    
    async def reject_request(
        self,
        db: AsyncSession,
        approval_request_id: UUID,
        user_id: UUID,
        comment: Optional[str] = None,
    ) -> ApprovalAction:
        """
        Reject an approval request.
        
        A single rejection immediately rejects the entire request.
        """
        # Get approval request
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_request_id)
        )
        approval_request = result.scalar_one_or_none()
        
        if not approval_request:
            raise ValueError(f"Approval request {approval_request_id} not found")
        
        # Check if already approved/rejected/expired
        if approval_request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request is {approval_request.status}, cannot reject")
        
        # Get user to check permissions
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user has permission to reject
        if not await self._can_approve(db, user, approval_request):
            raise ValueError(f"User does not have permission to reject this request")
        
        # Create rejection action
        approval_action = ApprovalAction(
            approval_request_id=approval_request_id,
            bundle_id=approval_request.bundle_id,
            tenant_id=approval_request.tenant_id,
            user_id=user_id,
            status=ApprovalStatus.REJECTED,
            comment=comment,
            acted_at=datetime.now(timezone.utc),
        )
        
        db.add(approval_action)
        
        # Update approval request
        approval_request.status = ApprovalStatus.REJECTED
        approval_request.updated_at = datetime.now(timezone.utc)
        
        # Update bundle status
        bundle_result = await db.execute(
            select(Bundle).where(Bundle.id == approval_request.bundle_id)
        )
        bundle = bundle_result.scalar_one()
        bundle.status = "cancelled"
        
        await db.flush()
        
        return approval_action
    
    async def get_pending_approvals(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[ApprovalRequest]:
        """
        Get pending approval requests for a tenant.
        
        If user_id is provided, only returns requests the user can approve.
        """
        query = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
        ).options(
            selectinload(ApprovalRequest.bundle),
            selectinload(ApprovalRequest.requester),
            selectinload(ApprovalRequest.actions),
        ).order_by(ApprovalRequest.created_at.desc())
        
        result = await db.execute(query)
        requests = result.scalars().all()
        
        # Filter by user permissions if specified
        if user_id:
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                requests = [
                    req for req in requests
                    if await self._can_approve(db, user, req)
                ]
        
        return list(requests)
    
    async def check_expired_requests(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
    ) -> List[ApprovalRequest]:
        """
        Check for expired approval requests and mark them as expired.
        
        Returns list of expired requests.
        """
        query = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.expires_at < datetime.now(timezone.utc),
            )
        )
        
        if tenant_id:
            query = query.where(ApprovalRequest.tenant_id == tenant_id)
        
        result = await db.execute(query)
        expired_requests = result.scalars().all()
        
        for request in expired_requests:
            request.status = ApprovalStatus.EXPIRED
            request.updated_at = datetime.now(timezone.utc)
        
        await db.flush()
        
        return list(expired_requests)
    
    async def auto_assess_risk(
        self,
        db: AsyncSession,
        bundle: Bundle,
        tenant_id: UUID,
    ) -> RiskLevel:
        """
        Automatically assess risk level for a bundle.
        
        Based on:
        - Number of assets affected
        - CVSS scores
        - Whether vulnerabilities are in KEV
        - Maintenance window timing
        """
        # Get bundle items to assess
        from backend.models.bundle_item import BundleItem
        
        result = await db.execute(
            select(BundleItem)
            .where(BundleItem.bundle_id == bundle.id)
            .options(selectinload(BundleItem.vulnerability))
        )
        items = result.scalars().all()
        
        # Calculate risk factors
        max_cvss = max([item.vulnerability.cvss_score for item in items if item.vulnerability.cvss_score], default=0)
        has_kev = any(item.vulnerability.kev_listed for item in items if item.vulnerability)
        assets_count = bundle.assets_affected_count or 0
        
        # Risk assessment logic
        if max_cvss >= 9.0 or has_kev or assets_count >= 100:
            return RiskLevel.CRITICAL
        elif max_cvss >= 7.0 or assets_count >= 50:
            return RiskLevel.HIGH
        elif max_cvss >= 4.0 or assets_count >= 10:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _get_policy_for_risk(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        risk_level: RiskLevel,
    ) -> Optional[ApprovalPolicy]:
        """Get the approval policy for a given risk level."""
        result = await db.execute(
            select(ApprovalPolicy).where(
                and_(
                    ApprovalPolicy.tenant_id == tenant_id,
                    ApprovalPolicy.risk_level == risk_level,
                )
            ).order_by(ApprovalPolicy.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def _can_approve(
        self,
        db: AsyncSession,
        user: User,
        approval_request: ApprovalRequest,
    ) -> bool:
        """Check if user has permission to approve a request."""
        # Admins can always approve
        if user.role == UserRole.ADMIN:
            return True
        
        # Approvers can approve
        if user.role == UserRole.APPROVER:
            return True
        
        # Check policy requirements
        policy = await self._get_policy_for_risk(
            db,
            approval_request.tenant_id,
            approval_request.risk_level,
        )
        
        if policy and policy.required_roles:
            # Check if user's role is in required roles
            return user.role.value in policy.required_roles
        
        # Default: only ADMIN and APPROVER can approve
        return False

    async def approve(
        self,
        db: AsyncSession,
        approval_id: UUID,
        approver_id: UUID,
        comment: Optional[str] = None,
    ):
        """Alias for approve_request that returns the updated ApprovalRequest."""
        from backend.models.approval import ApprovalRequest
        await self.approve_request(
            db=db,
            approval_request_id=approval_id,
            user_id=approver_id,
            comment=comment,
        )
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        return result.scalar_one()

    async def reject(
        self,
        db: AsyncSession,
        approval_id: UUID,
        approver_id: UUID,
        reason: Optional[str] = None,
    ):
        """Alias for reject_request that returns the updated ApprovalRequest."""
        from backend.models.approval import ApprovalRequest
        await self.reject_request(
            db=db,
            approval_request_id=approval_id,
            user_id=approver_id,
            comment=reason,  # reject_request uses 'comment' param
        )
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        return result.scalar_one()


# Global instance
approval_service = ApprovalService()
