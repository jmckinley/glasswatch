"""
Integration tests for approvals API endpoints.

Tests approval request creation, listing, approval/rejection flow,
and policy management.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestApprovalsAPI:
    """Integration tests for Approvals API"""
    
    async def test_create_approval_request(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """Test POST /approvals to create approval request"""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        response = await authenticated_client.post(
            "/api/v1/approvals",
            json={
                "bundle_id": str(bundle.id),
                "title": "Approval for test bundle",
                "description": "Please review this bundle",
                "risk_level": "MEDIUM"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["bundle_id"] == str(bundle.id)
        assert data["status"] == "PENDING"
        assert "id" in data
    
    async def test_list_approvals(
        self, authenticated_client: AsyncClient, test_tenant, test_user,
        create_test_bundle, test_session
    ):
        """Test GET /approvals with filters"""
        from backend.services.approval_service import ApprovalService
        from backend.models.approval import RiskLevel
        
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Create approval
        await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Test approval",
            risk_level=RiskLevel.LOW
        )
        
        # List approvals
        response = await authenticated_client.get("/api/v1/approvals")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
    
    async def test_list_approvals_filter_by_status(
        self, authenticated_client: AsyncClient, test_tenant, test_user,
        create_test_bundle, test_session
    ):
        """Test listing approvals filtered by status"""
        from backend.services.approval_service import ApprovalService
        from backend.models.approval import RiskLevel
        
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Pending approval",
            risk_level=RiskLevel.MEDIUM
        )
        
        # Filter by PENDING status
        response = await authenticated_client.get(
            "/api/v1/approvals?status=PENDING"
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "PENDING"
    
    async def test_approve_request(
        self, admin_client: AsyncClient, test_tenant, test_user,
        create_test_bundle, test_session
    ):
        """Test POST /approvals/{id}/approve"""
        from backend.services.approval_service import ApprovalService
        from backend.models.approval import RiskLevel
        
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
        response = await admin_client.post(
            f"/api/v1/approvals/{approval.id}/approve",
            json={"comment": "LGTM"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"
    
    async def test_reject_request(
        self, admin_client: AsyncClient, test_tenant, test_user,
        create_test_bundle, test_session
    ):
        """Test POST /approvals/{id}/reject"""
        from backend.services.approval_service import ApprovalService
        from backend.models.approval import RiskLevel
        
        service = ApprovalService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        approval = await service.create_approval_request(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id,
            requester_id=test_user.id,
            title="Test approval",
            risk_level=RiskLevel.MEDIUM
        )
        
        # Reject as admin
        response = await admin_client.post(
            f"/api/v1/approvals/{approval.id}/reject",
            json={"reason": "Too risky"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "REJECTED"
    
    async def test_create_approval_policy(
        self, admin_client: AsyncClient
    ):
        """Test POST /approvals/policies to create policy"""
        response = await admin_client.post(
            "/api/v1/approvals/policies",
            json={
                "name": "High Risk Policy",
                "risk_level": "HIGH",
                "required_approvals": 2,
                "auto_approve_low_risk": False,
                "escalation_hours": 24
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "High Risk Policy"
        assert data["required_approvals"] == 2
    
    async def test_list_policies(self, admin_client: AsyncClient):
        """Test GET /approvals/policies"""
        response = await admin_client.get("/api/v1/approvals/policies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_update_policy(
        self, admin_client: AsyncClient, test_session, test_tenant
    ):
        """Test PATCH /approvals/policies/{id}"""
        from backend.models.approval import ApprovalPolicy, RiskLevel
        from uuid import uuid4
        
        # Create a policy
        policy = ApprovalPolicy(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Policy",
            risk_level=RiskLevel.MEDIUM,
            required_approvals=1,
            auto_approve_low_risk=False,
            escalation_hours=48
        )
        test_session.add(policy)
        await test_session.flush()
        
        # Update policy
        response = await admin_client.patch(
            f"/api/v1/approvals/policies/{policy.id}",
            json={"required_approvals": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["required_approvals"] == 3
