"""
Regression tests for production bugs.

Each test documents the bug it prevents, including the root cause and fix.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGoalsNewRoute:
    """
    BUG: Dashboard "Create Goal" button linked to /goals/new.
    No dedicated page existed, so Next.js routed to [id]/page with id="new".
    That page called GET /goals/new → backend returned 422 with detail as array.
    Frontend did new Error(data.detail) → Error constructor coerced array → "[object Object]".

    Fix: link changed to /goals?create=true; api.ts serialises array detail properly.
    """

    async def test_get_goal_with_non_uuid_id_returns_422_not_500(
        self, admin_client: AsyncClient
    ) -> None:
        """
        GET /goals/new must return 422 (Unprocessable Entity), never 500.
        The 422 detail is an array — frontend must not display [object Object].
        This test guards the backend side of the contract.
        """
        response = await admin_client.get("/api/v1/goals/new")
        assert response.status_code == 422, (
            f"Expected 422 for non-UUID goal id, got {response.status_code}"
        )
        data = response.json()
        # detail should be a list of validation error dicts, not a string
        assert isinstance(data.get("detail"), list), (
            "FastAPI 422 detail should be a list for path parameter validation errors"
        )
        # Each error dict should have a 'msg' key
        for err in data["detail"]:
            assert "msg" in err, f"Validation error missing 'msg': {err}"

    async def test_get_goal_with_non_uuid_id_detail_is_parseable(
        self, admin_client: AsyncClient
    ) -> None:
        """
        The 422 detail array items must each have a string 'msg' so the
        frontend can join them into a readable error instead of [object Object].
        """
        response = await admin_client.get("/api/v1/goals/new")
        assert response.status_code == 422
        data = response.json()
        for err in data.get("detail", []):
            assert isinstance(err.get("msg"), str), (
                f"detail item 'msg' must be a string, got: {err}"
            )


@pytest.mark.asyncio
class TestAuditLogNoServerError:
    """
    BUG: Audit log page generated 500 errors.
    The endpoint is now guarded; ensure it never returns 500 for
    valid authenticated requests, including with filters applied.
    """

    async def test_audit_log_returns_200_not_500(
        self, admin_client: AsyncClient
    ) -> None:
        response = await admin_client.get("/api/v1/audit-log")
        assert response.status_code == 200, (
            f"Audit log returned {response.status_code}, expected 200. "
            f"Body: {response.text[:300]}"
        )

    async def test_audit_log_with_action_filter_never_500(
        self, admin_client: AsyncClient
    ) -> None:
        """Filtered queries must not 500 even if no rows match."""
        for action in ["bundle", "user", "vulnerability", "nonexistent.action"]:
            response = await admin_client.get(
                f"/api/v1/audit-log?action={action}"
            )
            assert response.status_code == 200, (
                f"Audit log with action={action!r} returned {response.status_code}"
            )
            data = response.json()
            assert isinstance(data["logs"], list)
            assert isinstance(data["total"], int)

    async def test_audit_log_with_date_filter_never_500(
        self, admin_client: AsyncClient
    ) -> None:
        response = await admin_client.get(
            "/api/v1/audit-log?since=2020-01-01T00:00:00Z&until=2030-01-01T00:00:00Z"
        )
        assert response.status_code == 200

    async def test_audit_log_export_never_500(
        self, admin_client: AsyncClient
    ) -> None:
        response = await admin_client.get("/api/v1/audit-log/export?limit=10")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
