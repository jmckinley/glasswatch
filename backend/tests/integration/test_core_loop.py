"""
Core loop integration tests for Glasswatch.

Verifies that the primary user-facing API surface works end-to-end:
auth → data endpoints → bundle workflow → agent → webhooks → reporting.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestCoreLoop:
    """End-to-end core loop tests covering the primary API surface."""

    # -------------------------------------------------------------------------
    # Auth
    # -------------------------------------------------------------------------

    async def test_demo_login_returns_token(self, client: AsyncClient):
        """Demo login should return a JWT access_token and user info."""
        response = await client.get("/api/v1/auth/demo-login")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["access_token"]  # non-empty

    # -------------------------------------------------------------------------
    # Core data endpoints
    # -------------------------------------------------------------------------

    async def test_vulnerabilities_list(
        self, authenticated_client: AsyncClient
    ):
        """GET /vulnerabilities should return a paginated list."""
        response = await authenticated_client.get("/api/v1/vulnerabilities")
        assert response.status_code == 200
        data = response.json()
        # Accept both list and paginated-dict response shapes
        assert isinstance(data, (list, dict))

    async def test_assets_list(self, authenticated_client: AsyncClient):
        """GET /assets should return a paginated list."""
        response = await authenticated_client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_goals_list(self, authenticated_client: AsyncClient):
        """GET /goals should return a list of goals."""
        response = await authenticated_client.get("/api/v1/goals")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_bundles_list(self, authenticated_client: AsyncClient):
        """GET /bundles should return a list of patch bundles."""
        response = await authenticated_client.get("/api/v1/bundles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_maintenance_windows_list(
        self, authenticated_client: AsyncClient
    ):
        """GET /maintenance-windows should return a list."""
        response = await authenticated_client.get(
            "/api/v1/maintenance-windows"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    # -------------------------------------------------------------------------
    # Bundle workflow
    # -------------------------------------------------------------------------

    async def test_bundle_items_endpoint(
        self, authenticated_client: AsyncClient, test_tenant, create_test_bundle
    ):
        """Bundle detail endpoint should return bundle data for a real bundle."""
        bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Core Loop Test Bundle",
        )
        response = await authenticated_client.get(
            f"/api/v1/bundles/{bundle.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bundle.id)
        assert data["name"] == "Core Loop Test Bundle"

    # -------------------------------------------------------------------------
    # Agent
    # -------------------------------------------------------------------------

    async def test_agent_chat_responds(
        self, authenticated_client: AsyncClient
    ):
        """POST /agent/chat should return a response (may be mocked/stubbed)."""
        payload = {"message": "What is the current patch status?"}
        response = await authenticated_client.post(
            "/api/v1/agent/chat", json=payload
        )
        # Accept 200 (real response) or 503 (LLM unavailable in test env)
        assert response.status_code in (200, 422, 503)
        if response.status_code == 200:
            data = response.json()
            # Response must have some kind of message/content field
            assert any(
                k in data for k in ("response", "message", "content", "text")
            )

    # -------------------------------------------------------------------------
    # Webhooks
    # -------------------------------------------------------------------------

    async def test_webhooks_health(self, client: AsyncClient):
        """GET /webhooks/health should return 200 without authentication."""
        response = await client.get("/api/v1/webhooks/health")
        assert response.status_code == 200

    # -------------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------------

    async def test_compliance_summary(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/compliance-summary should return compliance data."""
        response = await authenticated_client.get(
            "/api/v1/reporting/compliance-summary"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_executive_summary(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/executive-summary should return executive data."""
        response = await authenticated_client.get(
            "/api/v1/reporting/executive-summary"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    # -------------------------------------------------------------------------
    # Unauthenticated access (demo-first model)
    # -------------------------------------------------------------------------

    async def test_unauthenticated_requests_return_data_or_auth_error(
        self, client: AsyncClient
    ):
        """Core data endpoints should respond (200 demo data, or 401/403).

        Glasswatch uses a demo-first auth model: unauthenticated requests are
        served from the demo tenant so the product is immediately explorable.
        All endpoints must return a valid HTTP status (not crash).
        """
        endpoints = [
            "/api/v1/vulnerabilities",
            "/api/v1/assets",
            "/api/v1/bundles",
            "/api/v1/goals",
        ]
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code in (
                200, 401, 403
            ), f"{endpoint} returned unexpected status {response.status_code}"
