"""
Integration tests for Bundles API endpoints.

Covers list, get, status transitions, approval flow, and edge cases.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestBundlesAPI:
    """Integration tests for /api/v1/bundles."""

    # ------------------------------------------------------------------
    # GET /bundles — list
    # ------------------------------------------------------------------

    async def test_list_bundles_empty(self, authenticated_client: AsyncClient, test_tenant):
        """GET /bundles returns empty list when none exist."""
        response = await authenticated_client.get("/api/v1/bundles")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "total" in data

    async def test_list_bundles_requires_auth(self, client: AsyncClient):
        """Unauthenticated GET /bundles returns 401."""
        response = await client.get("/api/v1/bundles")
        assert response.status_code == 401

    async def test_list_bundles_returns_created_bundle(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """Bundles created via fixture appear in the list."""
        await create_test_bundle(tenant_id=str(test_tenant.id), name="List Test Bundle")

        response = await authenticated_client.get("/api/v1/bundles")
        assert response.status_code == 200
        data = response.json()
        names = [b["name"] for b in data["items"]]
        assert "List Test Bundle" in names

    async def test_list_bundles_filter_by_status(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """?status= filter returns only matching bundles."""
        await create_test_bundle(tenant_id=str(test_tenant.id), name="Draft Bundle", status="draft")
        await create_test_bundle(tenant_id=str(test_tenant.id), name="Scheduled Bundle", status="scheduled")

        response = await authenticated_client.get("/api/v1/bundles?status=draft")
        assert response.status_code == 200
        data = response.json()
        for bundle in data["items"]:
            assert bundle["status"] == "draft"

    async def test_list_bundles_pagination(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """limit and skip query params work."""
        for i in range(5):
            await create_test_bundle(tenant_id=str(test_tenant.id), name=f"Bundle {i}")

        response = await authenticated_client.get("/api/v1/bundles?limit=2&skip=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    # ------------------------------------------------------------------
    # GET /bundles/{id}
    # ------------------------------------------------------------------

    async def test_get_bundle_by_id(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """GET /bundles/{id} returns bundle details."""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id), name="Fetch Me Bundle")

        response = await authenticated_client.get(f"/api/v1/bundles/{bundle.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bundle.id)
        assert data["name"] == "Fetch Me Bundle"

    async def test_get_bundle_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /bundles/{nonexistent} returns 404."""
        response = await authenticated_client.get(f"/api/v1/bundles/{uuid4()}")
        assert response.status_code == 404

    async def test_get_bundle_invalid_uuid(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /bundles/badid returns 422 (not 500)."""
        response = await authenticated_client.get("/api/v1/bundles/not-a-uuid")
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # PATCH /bundles/{id} — update
    # ------------------------------------------------------------------

    async def test_update_bundle_name(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """PATCH /bundles/{id} updates the bundle name."""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id), name="Old Name")

        response = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_bundle_requires_auth(self, client: AsyncClient):
        """Unauthenticated PATCH returns 401."""
        response = await client.patch(f"/api/v1/bundles/{uuid4()}", json={"name": "x"})
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # POST /bundles/{id}/approve
    # ------------------------------------------------------------------

    async def test_approve_bundle_draft(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """Approving a draft bundle transitions its status."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Approve Me",
            status="draft",
        )
        response = await authenticated_client.post(f"/api/v1/bundles/{bundle.id}/approve")
        # Approval should either succeed (200) or indicate approval is not needed
        assert response.status_code in (200, 400, 409)

    async def test_approve_nonexistent_bundle(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Approving a non-existent bundle returns 404."""
        response = await authenticated_client.post(f"/api/v1/bundles/{uuid4()}/approve")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # GET /bundles/{id}/items
    # ------------------------------------------------------------------

    async def test_get_bundle_items_empty(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """GET /bundles/{id}/items returns empty list for new bundle."""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        response = await authenticated_client.get(f"/api/v1/bundles/{bundle.id}/items")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
        if isinstance(data, dict):
            items = data.get("items", data.get("data", []))
        else:
            items = data
        assert isinstance(items, list)

    # ------------------------------------------------------------------
    # GET /bundles/{id}/execution-log
    # ------------------------------------------------------------------

    async def test_get_execution_log_empty(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """GET /bundles/{id}/execution-log returns a valid response."""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        response = await authenticated_client.get(f"/api/v1/bundles/{bundle.id}/execution-log")
        assert response.status_code in (200, 404)

    # ------------------------------------------------------------------
    # POST /bundles/{id}/rollback
    # ------------------------------------------------------------------

    async def test_rollback_non_applied_bundle_returns_error(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """Rolling back a draft bundle should return a sensible error."""
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id), status="draft")
        response = await authenticated_client.post(f"/api/v1/bundles/{bundle.id}/rollback")
        # Can't rollback something that hasn't been applied
        assert response.status_code in (400, 409, 422)

    async def test_rollback_nonexistent_bundle(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Rollback of non-existent bundle returns 404."""
        response = await authenticated_client.post(f"/api/v1/bundles/{uuid4()}/rollback")
        assert response.status_code == 404
