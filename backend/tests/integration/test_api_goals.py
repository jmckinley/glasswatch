"""
Integration tests for Goals API endpoints.

Covers full CRUD, validation errors, auth enforcement, and edge cases
that have caused production bugs (e.g. /goals/new returning 422).
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGoalsAPI:
    """Full CRUD coverage for /api/v1/goals."""

    # ------------------------------------------------------------------
    # GET /goals — list
    # ------------------------------------------------------------------

    async def test_list_goals_empty(self, authenticated_client: AsyncClient, test_tenant):
        """GET /goals returns an empty list when none exist."""
        response = await authenticated_client.get("/api/v1/goals")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_goals_requires_auth(self, client: AsyncClient):
        """Unauthenticated GET /goals returns 401."""
        response = await client.get("/api/v1/goals")
        assert response.status_code == 401

    async def test_list_goals_returns_created_goal(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Goals created via POST appear in the list."""
        payload = {
            "name": "List Test Goal",
            "type": "zero_critical",
        }
        create_resp = await authenticated_client.post("/api/v1/goals", json=payload)
        assert create_resp.status_code == 201

        list_resp = await authenticated_client.get("/api/v1/goals?active_only=false")
        assert list_resp.status_code == 200
        names = [g["name"] for g in list_resp.json()]
        assert "List Test Goal" in names

    # ------------------------------------------------------------------
    # POST /goals — create
    # ------------------------------------------------------------------

    async def test_create_goal_zero_critical(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /goals creates a zero_critical goal successfully."""
        payload = {
            "name": "Zero Critical Goal",
            "type": "zero_critical",
            "description": "Eliminate all critical vulns",
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Zero Critical Goal"
        assert data["type"] == "zero_critical"
        assert data["active"] is True
        assert "id" in data
        assert "tenant_id" in data

    async def test_create_goal_kev_elimination(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /goals creates a kev_elimination goal."""
        payload = {
            "name": "KEV Elimination Goal",
            "type": "kev_elimination",
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "kev_elimination"

    async def test_create_goal_compliance_deadline_requires_target_date(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """compliance_deadline goal without target_date returns 400."""
        payload = {
            "name": "Compliance Goal",
            "type": "compliance_deadline",
            # No target_date
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 400

    async def test_create_goal_compliance_deadline_with_future_date(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """compliance_deadline goal with a future target_date succeeds."""
        future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        payload = {
            "name": "Compliance Deadline Goal",
            "type": "compliance_deadline",
            "target_date": future,
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 201

    async def test_create_goal_compliance_deadline_with_past_date(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """compliance_deadline goal with a past target_date returns 422."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        payload = {
            "name": "Expired Compliance Goal",
            "type": "compliance_deadline",
            "target_date": past,
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 422

    async def test_create_goal_risk_reduction_requires_target_value(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """risk_reduction goal without target_value returns 400."""
        payload = {
            "name": "Risk Reduction Goal",
            "type": "risk_reduction",
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 400

    async def test_create_goal_risk_reduction_with_target_value(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """risk_reduction goal with target_value succeeds."""
        payload = {
            "name": "Risk Reduction Goal",
            "type": "risk_reduction",
            "target_value": 500.0,
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 201

    async def test_create_goal_name_too_short(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Goal with empty name returns 422."""
        payload = {
            "name": "",
            "type": "zero_critical",
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 422

    async def test_create_goal_requires_auth(self, client: AsyncClient):
        """Unauthenticated POST /goals returns 401."""
        payload = {"name": "No Auth Goal", "type": "zero_critical"}
        response = await client.post("/api/v1/goals", json=payload)
        assert response.status_code == 401

    async def test_create_goal_invalid_max_vulns_per_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """max_vulns_per_window of 0 (below min 1) returns 422."""
        payload = {
            "name": "Bad Constraint Goal",
            "type": "zero_critical",
            "max_vulns_per_window": 0,
        }
        response = await authenticated_client.post("/api/v1/goals", json=payload)
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # GET /goals/{goal_id} — get single
    # ------------------------------------------------------------------

    async def test_get_goal_by_id(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /goals/{id} returns the goal."""
        create = await authenticated_client.post(
            "/api/v1/goals",
            json={"name": "Fetch Me Goal", "type": "zero_critical"},
        )
        assert create.status_code == 201
        goal_id = create.json()["id"]

        response = await authenticated_client.get(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == goal_id
        assert data["name"] == "Fetch Me Goal"

    async def test_get_goal_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /goals/{nonexistent-id} returns 404."""
        response = await authenticated_client.get(f"/api/v1/goals/{uuid4()}")
        assert response.status_code == 404

    async def test_get_goal_invalid_uuid(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """
        GET /goals/new returns 422 (not a silent 404 that falls through
        to some other page handler). This was a real production bug where
        /goals/new showed "[object Object]" because the 422 detail array
        wasn't serialised properly by the frontend.
        """
        response = await authenticated_client.get("/api/v1/goals/new")
        assert response.status_code == 422
        # detail must be a list of validation error dicts, not a plain string
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        # Each entry should have a "msg" key (FastAPI standard)
        for entry in data["detail"]:
            assert "msg" in entry

    async def test_get_goal_tenant_isolation(
        self,
        test_session,
        create_test_tenant,
        create_test_user,
        test_tenant,
    ):
        """A goal created by tenant A is not visible to tenant B."""
        from backend.core.auth_workos import create_access_token
        from httpx import AsyncClient
        from backend.main import app
        from backend.db.session import get_db
        from backend.models.user import UserRole

        other_tenant = await create_test_tenant(name="Other Tenant", email="other@example.com")
        other_user = await create_test_user(
            tenant_id=str(other_tenant.id),
            email="other@example.com",
            role=UserRole.ENGINEER,
        )

        async def override_get_db():
            yield test_session

        app.dependency_overrides[get_db] = override_get_db
        token = await create_access_token(
            user_id=str(other_user.id), tenant_id=str(other_user.tenant_id)
        )
        async with AsyncClient(app=app, base_url="http://localhost") as other_client:
            other_client.headers["Authorization"] = f"Bearer {token}"

            # Create a goal as the "other" tenant
            create = await other_client.post(
                "/api/v1/goals", json={"name": "Other Tenant Goal", "type": "zero_critical"}
            )
            assert create.status_code == 201
            goal_id = create.json()["id"]

        # Now try to fetch that goal as the main tenant
        from backend.core.auth_workos import create_access_token as cat2
        from backend.models.user import UserRole as UR
        main_user = await create_test_user(
            tenant_id=str(test_tenant.id),
            email="mainuser2@example.com",
            role=UR.ENGINEER,
        )
        main_token = await cat2(user_id=str(main_user.id), tenant_id=str(main_user.tenant_id))
        async with AsyncClient(app=app, base_url="http://localhost") as main_client:
            main_client.headers["Authorization"] = f"Bearer {main_token}"
            response = await main_client.get(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # PATCH /goals/{goal_id} — update
    # ------------------------------------------------------------------

    async def test_update_goal_name(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /goals/{id} updates the name."""
        create = await authenticated_client.post(
            "/api/v1/goals", json={"name": "Old Name", "type": "zero_critical"}
        )
        goal_id = create.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/goals/{goal_id}", json={"name": "New Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_goal_deactivate(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /goals/{id} can deactivate a goal."""
        create = await authenticated_client.post(
            "/api/v1/goals", json={"name": "Active Goal", "type": "zero_critical"}
        )
        goal_id = create.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/goals/{goal_id}", json={"active": False}
        )
        assert response.status_code == 200
        assert response.json()["active"] is False

    async def test_update_goal_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /goals/{nonexistent} returns 404."""
        response = await authenticated_client.patch(
            f"/api/v1/goals/{uuid4()}", json={"name": "Ghost"}
        )
        assert response.status_code == 404

    async def test_update_goal_requires_auth(self, client: AsyncClient):
        """Unauthenticated PATCH returns 401."""
        response = await client.patch(
            f"/api/v1/goals/{uuid4()}", json={"name": "Anon"}
        )
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # DELETE /goals/{goal_id}
    # ------------------------------------------------------------------

    async def test_delete_goal(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /goals/{id} removes the goal."""
        create = await authenticated_client.post(
            "/api/v1/goals", json={"name": "Delete Me", "type": "zero_critical"}
        )
        assert create.status_code == 201
        goal_id = create.json()["id"]

        delete_response = await authenticated_client.delete(f"/api/v1/goals/{goal_id}")
        assert delete_response.status_code == 200

        # Verify it's gone
        get_response = await authenticated_client.get(f"/api/v1/goals/{goal_id}")
        assert get_response.status_code == 404

    async def test_delete_goal_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /goals/{nonexistent} returns 404."""
        response = await authenticated_client.delete(f"/api/v1/goals/{uuid4()}")
        assert response.status_code == 404

    async def test_delete_goal_requires_auth(self, client: AsyncClient):
        """Unauthenticated DELETE returns 401."""
        response = await client.delete(f"/api/v1/goals/{uuid4()}")
        assert response.status_code == 401
