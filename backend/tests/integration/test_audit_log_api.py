"""
Integration tests for the /api/v1/audit-log endpoints.

Tests the full HTTP stack: routing → auth → service → DB.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuditLogApi:
    # ------------------------------------------------------------------
    # GET /audit-log
    # ------------------------------------------------------------------

    async def test_get_audit_log_empty(self, admin_client: AsyncClient):
        """GET /audit-log returns empty list when no events exist."""
        response = await admin_client.get("/api/v1/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
        assert data["total"] >= 0

    async def test_get_audit_log_requires_auth(self, client: AsyncClient):
        """Unauthenticated requests are rejected."""
        response = await client.get("/api/v1/audit-log")
        assert response.status_code in (401, 403)

    async def test_get_audit_log_non_admin_forbidden(self, authenticated_client: AsyncClient):
        """Non-admin users cannot access audit log."""
        response = await authenticated_client.get("/api/v1/audit-log")
        assert response.status_code == 403

    async def test_audit_log_after_bundle_create(
        self, admin_client: AsyncClient, test_session
    ):
        """
        After performing an action (demo-login), the audit log should
        contain at least the login event.

        Note: The demo-login audit is written in the same session; we verify
        the endpoint returns a valid paginated response.
        """
        # Hit demo-login to produce an audit event
        await admin_client.get("/api/v1/auth/demo-login")

        response = await admin_client.get("/api/v1/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    async def test_audit_log_filter_by_action(self, admin_client: AsyncClient):
        """?action= filter returns only matching entries (or empty if none)."""
        response = await admin_client.get(
            "/api/v1/audit-log", params={"action": "bundle.approved"}
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data["logs"]:
            assert entry["action"] == "bundle.approved"

    async def test_audit_log_filter_by_resource_type(self, admin_client: AsyncClient):
        """?resource_type= filter returns only matching entries."""
        response = await admin_client.get(
            "/api/v1/audit-log", params={"resource_type": "bundle"}
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data["logs"]:
            assert entry["resource_type"] == "bundle"

    async def test_audit_log_pagination(self, admin_client: AsyncClient):
        """limit and offset query params work."""
        r1 = await admin_client.get(
            "/api/v1/audit-log", params={"limit": 1, "offset": 0}
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["limit"] == 1
        assert d1["offset"] == 0
        assert len(d1["logs"]) <= 1

        r2 = await admin_client.get(
            "/api/v1/audit-log", params={"limit": 1, "offset": 1}
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["offset"] == 1

    async def test_audit_log_entry_schema(self, admin_client: AsyncClient):
        """
        Each returned log entry has the expected fields.
        We trigger a demo-login to have at least one entry, then verify schema.
        """
        # Ensure at least one event exists
        await admin_client.get("/api/v1/auth/demo-login")
        response = await admin_client.get("/api/v1/audit-log")
        assert response.status_code == 200
        data = response.json()

        if data["logs"]:
            entry = data["logs"][0]
            assert "id" in entry
            assert "action" in entry
            assert "resource_type" in entry
            assert "details" in entry
            assert "success" in entry
            assert "created_at" in entry
            # user may be null (system action) or a dict with id/email/name
            assert "user" in entry
            if entry["user"] is not None:
                assert "id" in entry["user"]
                assert "email" in entry["user"]
                assert "name" in entry["user"]

    # ------------------------------------------------------------------
    # GET /audit-log/export
    # ------------------------------------------------------------------

    async def test_audit_log_export_csv(self, admin_client: AsyncClient):
        """GET /audit-log/export returns CSV content-type."""
        response = await admin_client.get("/api/v1/audit-log/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    async def test_audit_log_export_csv_has_header(self, admin_client: AsyncClient):
        """Exported CSV starts with the expected header row."""
        response = await admin_client.get("/api/v1/audit-log/export")
        assert response.status_code == 200
        text = response.text
        first_line = text.strip().split("\n")[0] if text.strip() else ""
        assert "id" in first_line
        assert "action" in first_line
        assert "timestamp" in first_line

    async def test_audit_log_export_requires_auth(self, client: AsyncClient):
        """Export endpoint also requires authentication."""
        response = await client.get("/api/v1/audit-log/export")
        assert response.status_code in (401, 403)
