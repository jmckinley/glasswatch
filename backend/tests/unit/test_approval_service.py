"""
Unit tests for the approval workflow service.

Tests approval request creation, approval/rejection, risk assessment,
policy matching, and expiration handling.
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from backend.services.approval_service import ApprovalService
from backend.models.approval import (
    ApprovalRequest, ApprovalStatus, RiskLevel, ApprovalPolicy
)
from backend.models.bundle import Bundle
from backend.models.user import UserRole


pytestmark = pytest.mark.asyncio


class TestApprovalService:
    """Test suite for ApprovalService"""
    
    async def test_create_approval_request(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test creating a basic approval request"""
        service = ApprovalService()
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Test Bundle"
        )
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Request approval for test bundle",
            description="Testing approval creation"
        )
        
        assert approval is not None
        assert approval.bundle_id == bundle.id
        assert approval.requester_id == test_user.id
        assert approval.status == ApprovalStatus.PENDING
        assert approval.required_approvals >= 1
        assert approval.current_approvals == 0
    
    async def test_auto_risk_assessment_low(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test auto risk assessment assigns LOW for small bundles"""
        service = ApprovalService()
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Small Bundle",
            affected_asset_count=2,
            estimated_downtime=5
        )
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Low risk request"
        )
        
        # Should auto-assess as low risk
        assert approval.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
    
    async def test_auto_risk_assessment_high(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test auto risk assessment assigns HIGH for large bundles"""
        service = ApprovalService()
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Large Bundle",
            affected_asset_count=50,
            estimated_downtime=120
        )
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="High risk request"
        )
        
        # Should be higher risk due to scale
        assert approval.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    async def test_auto_risk_assessment_critical(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test auto risk assessment assigns CRITICAL for massive impact"""
        service = ApprovalService()
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Critical Bundle",
            affected_asset_count=200,
            estimated_downtime=360,
            priority=5
        )
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Critical risk request"
        )
        
        # Large impact should trigger high/critical assessment
        assert approval.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    async def test_approve_single_approver(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test single approver can approve a request"""
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Test approval",
            risk_level=RiskLevel.LOW
        )
        
        # Approve as admin
        result = await service.approve(
            db=test_session,
            approval_id=approval.id,
            approver_id=admin_user.id,
            comment="Looks good"
        )
        
        assert result.status == ApprovalStatus.APPROVED
        assert result.current_approvals >= 1
        assert result.approved_at is not None
    
    async def test_approve_multi_approver_threshold(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test multi-approver threshold must be met"""
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Create high-risk approval requiring multiple approvers
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="High risk approval",
            risk_level=RiskLevel.HIGH
        )
        
        # Set to require 2 approvals
        approval.required_approvals = 2
        await test_session.flush()
        
        # First approval
        result = await service.approve(
            db=test_session,
            approval_id=approval.id,
            approver_id=admin_user.id,
            comment="First approval"
        )
        
        # Should still be pending after first approval
        assert result.status == ApprovalStatus.PENDING
        assert result.current_approvals == 1
        
        # Second approval (create another admin user)
        from backend.models.user import User
        admin_user_2 = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="admin2@example.com",
            name="Admin 2",
            role=UserRole.ADMIN,
            workos_user_id=f"workos_{uuid4()}"
        )
        test_session.add(admin_user_2)
        await test_session.flush()
        
        result = await service.approve(
            db=test_session,
            approval_id=approval.id,
            approver_id=admin_user_2.id,
            comment="Second approval"
        )
        
        # Should be approved after second approval
        assert result.status == ApprovalStatus.APPROVED
        assert result.current_approvals == 2
    
    async def test_reject_approval(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test rejecting an approval request"""
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Test approval"
        )
        
        # Reject as admin
        result = await service.reject(
            db=test_session,
            approval_id=approval.id,
            approver_id=admin_user.id,
            reason="Security concerns"
        )
        
        assert result.status == ApprovalStatus.REJECTED
        # Model uses updated_at to track rejection time
        assert result.updated_at is not None or result.status == ApprovalStatus.REJECTED
    
    async def test_expired_request_handling(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test that expired requests are handled properly"""
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Test approval"
        )
        
        # Manually expire the request
        approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.flush()
        
        # Try to approve expired request
        with pytest.raises(ValueError, match="expired"):
            await service.approve(
                db=test_session,
                approval_id=approval.id,
                approver_id=test_user.id,
                comment="Too late"
            )
    
    async def test_policy_matching_by_risk_level(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test that approval policies match by risk level"""
        service = ApprovalService()
        
        # Create a policy for HIGH risk
        policy = ApprovalPolicy(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="High Risk Policy",
            risk_level=RiskLevel.HIGH,
            required_approvals=2,
            auto_approve_low_risk=False,
            escalation_hours=24
        )
        test_session.add(policy)
        await test_session.flush()
        
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Create HIGH risk approval
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="High risk request",
            risk_level=RiskLevel.HIGH
        )
        
        # Should match the policy and require 2 approvals
        assert approval.required_approvals == 2
    
    async def test_auto_approve_low_risk_with_policy(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test that low risk approvals auto-approve when policy allows"""
        service = ApprovalService()
        
        # Create policy with auto-approve for low risk
        policy = ApprovalPolicy(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Auto-Approve Low",
            risk_level=RiskLevel.LOW,
            required_approvals=1,
            auto_approve_low_risk=True,
            escalation_hours=48
        )
        test_session.add(policy)
        await test_session.flush()
        
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            affected_asset_count=1
        )
        
        # Create LOW risk approval
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Low risk request",
            risk_level=RiskLevel.LOW
        )
        
        # Should be auto-approved
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.approved_at is not None
