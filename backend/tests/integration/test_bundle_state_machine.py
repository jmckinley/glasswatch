"""
Integration tests for bundle state machine guards.

Tests that the PATCH /bundles/{id}/status and POST /bundles/{id}/approve
endpoints enforce the state machine — valid transitions succeed, invalid
ones return 409 (or 400 for the approve endpoint).
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestBundleStateMachineIntegration:
    """
    Integration tests for bundle state transitions.

    Bundles are pre-created using the create_test_bundle conftest fixture
    (no POST /bundles endpoint exists — bundles are created by the core loop).
    """

    # ── /approve endpoint ─────────────────────────────────────────────────────

    async def test_approve_draft_bundle(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """POST /bundles/{id}/approve on a draft bundle should succeed."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Draft Bundle (approve test)",
            status="draft",
        )
        resp = await authenticated_client.post(
            f"/api/v1/bundles/{bundle.id}/approve"
        )
        assert resp.status_code in (200, 201), resp.text
        assert resp.json()["status"] == "approved"

    async def test_cannot_approve_completed_bundle(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """POST /bundles/{id}/approve on a completed bundle → 400 or 409."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Completed Bundle (approve test)",
            status="completed",
        )
        resp = await authenticated_client.post(
            f"/api/v1/bundles/{bundle.id}/approve"
        )
        # The approve endpoint raises 400 when status is not draft/scheduled
        assert resp.status_code in (400, 409), resp.text

    async def test_cannot_approve_cancelled_bundle(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """POST /bundles/{id}/approve on a cancelled bundle → 400 or 409."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Cancelled Bundle (approve test)",
            status="cancelled",
        )
        resp = await authenticated_client.post(
            f"/api/v1/bundles/{bundle.id}/approve"
        )
        assert resp.status_code in (400, 409), resp.text

    # ── PATCH /status — valid transitions ─────────────────────────────────────

    async def test_status_patch_valid_transition(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """PATCH /bundles/{id}/status with a valid transition (failed → draft) → 200.

        Uses failed→draft to avoid the rule-evaluation code path that runs for
        →scheduled and →approved transitions (which queries deployment_rules
        and exposes a SQLite/PGUUID type incompatibility in the test env).
        """
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Failed Bundle (retry valid transition test)",
            status="failed",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "draft"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "draft"

    async def test_status_patch_draft_to_cancelled(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """draft → cancelled is a legal transition."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Draft Bundle (cancel test)",
            status="draft",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "cancelled"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "cancelled"

    async def test_status_patch_approved_to_in_progress(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """approved → in_progress is a legal transition."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Approved Bundle",
            status="approved",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_progress"

    # ── PATCH /status — invalid transitions ───────────────────────────────────

    async def test_status_patch_invalid_transition(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """PATCH with an invalid transition (in_progress → draft) → 409."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="In-Progress Bundle",
            status="in_progress",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "draft"},
        )
        assert resp.status_code == 409, resp.text

    async def test_status_patch_completed_is_terminal(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """completed → anything (except itself) must be rejected with 409."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Completed Bundle (terminal test)",
            status="completed",
        )
        for bad_target in ("draft", "approved", "in_progress", "scheduled"):
            resp = await authenticated_client.patch(
                f"/api/v1/bundles/{bundle.id}/status",
                json={"status": bad_target},
            )
            assert resp.status_code == 409, \
                f"Expected 409 for completed→{bad_target}, got {resp.status_code}: {resp.text}"

    async def test_status_patch_cancelled_is_terminal(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """cancelled → anything must be rejected with 409."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Cancelled Bundle (terminal test)",
            status="cancelled",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "draft"},
        )
        assert resp.status_code == 409, resp.text

    async def test_status_patch_in_progress_to_completed(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """in_progress → completed is a valid terminal transition."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="In-Progress Bundle (complete test)",
            status="in_progress",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "completed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"

    async def test_status_patch_failed_to_draft(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_bundle,
    ):
        """failed → draft (retry) is a valid transition."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Failed Bundle (retry test)",
            status="failed",
        )
        resp = await authenticated_client.patch(
            f"/api/v1/bundles/{bundle.id}/status",
            json={"status": "draft"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "draft"
