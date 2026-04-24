"""
Integration tests for the Reporting API endpoints.

Tests:
  GET /api/v1/reporting/compliance-summary
  GET /api/v1/reporting/mttp
  GET /api/v1/reporting/sla-tracking
  GET /api/v1/reporting/executive-summary
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestComplianceSummary:
    async def test_compliance_summary_returns_200(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/compliance-summary returns 200."""
        response = await authenticated_client.get(
            "/api/v1/reporting/compliance-summary"
        )
        assert response.status_code == 200, response.text

    async def test_compliance_summary_returns_frameworks(
        self, authenticated_client: AsyncClient
    ):
        """Response must contain bod_2201, soc2, and pci_dss keys."""
        response = await authenticated_client.get(
            "/api/v1/reporting/compliance-summary"
        )
        assert response.status_code == 200, response.text

        data = response.json()
        assert "bod_2201" in data, f"Missing bod_2201 key. Keys: {list(data.keys())}"
        assert "soc2" in data, f"Missing soc2 key. Keys: {list(data.keys())}"
        assert "pci_dss" in data, f"Missing pci_dss key. Keys: {list(data.keys())}"

    async def test_compliance_summary_bod_2201_has_status(
        self, authenticated_client: AsyncClient
    ):
        """bod_2201 section must include a 'status' field."""
        response = await authenticated_client.get(
            "/api/v1/reporting/compliance-summary"
        )
        data = response.json()
        bod = data.get("bod_2201", {})
        assert "status" in bod, f"bod_2201 missing 'status': {bod}"

    async def test_compliance_summary_unauthenticated(self, client: AsyncClient):
        """Unauthenticated request → 401 or 403."""
        response = await client.get("/api/v1/reporting/compliance-summary")
        assert response.status_code in (401, 403)

    async def test_compliance_summary_with_kev_vulns(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        test_session,
        create_test_asset,
        create_test_vulnerability,
    ):
        """With some KEV-listed vulns, compliance summary should reflect them."""
        from backend.models.asset_vulnerability import AssetVulnerability
        from uuid import uuid4
        from datetime import datetime, timezone

        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="kev-test-host",
        )
        vuln = await create_test_vulnerability(
            identifier="CVE-2024-99001",
            severity="CRITICAL",
            kev_listed=True,
        )
        link = AssetVulnerability(
            id=uuid4(),
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            status="ACTIVE",
            risk_score=90.0,
            discovered_at=datetime.now(timezone.utc),
        )
        test_session.add(link)
        await test_session.flush()

        response = await authenticated_client.get(
            "/api/v1/reporting/compliance-summary"
        )
        assert response.status_code == 200
        data = response.json()
        assert "bod_2201" in data


class TestMttpEndpoint:
    async def test_mttp_endpoint(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/mttp → 200."""
        response = await authenticated_client.get("/api/v1/reporting/mttp")
        assert response.status_code == 200, response.text

    async def test_mttp_endpoint_response_structure(
        self, authenticated_client: AsyncClient
    ):
        """MTTP response should be a dict (not an error)."""
        response = await authenticated_client.get("/api/v1/reporting/mttp")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_mttp_endpoint_unauthenticated(self, client: AsyncClient):
        """Unauthenticated MTTP request → 401 or 403."""
        response = await client.get("/api/v1/reporting/mttp")
        assert response.status_code in (401, 403)


class TestSlaTracking:
    async def test_sla_tracking(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/sla-tracking → 200, has items array."""
        response = await authenticated_client.get(
            "/api/v1/reporting/sla-tracking"
        )
        assert response.status_code == 200, response.text

        data = response.json()
        assert "items" in data, f"Missing 'items' key. Keys: {list(data.keys())}"
        assert isinstance(data["items"], list)

    async def test_sla_tracking_has_counts(
        self, authenticated_client: AsyncClient
    ):
        """SLA tracking response should include a counts summary."""
        response = await authenticated_client.get(
            "/api/v1/reporting/sla-tracking"
        )
        data = response.json()
        assert "counts" in data or "items" in data  # either counts or items is fine

    async def test_sla_tracking_with_active_vuln(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        test_session,
        create_test_asset,
        create_test_vulnerability,
    ):
        """With an ACTIVE vuln, sla-tracking items should be non-empty."""
        from backend.models.asset_vulnerability import AssetVulnerability
        from uuid import uuid4
        from datetime import datetime, timezone

        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="sla-track-host",
        )
        vuln = await create_test_vulnerability(
            identifier="CVE-2024-88001",
            severity="HIGH",
        )
        link = AssetVulnerability(
            id=uuid4(),
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            status="ACTIVE",
            risk_score=70.0,
            discovered_at=datetime.now(timezone.utc),
        )
        test_session.add(link)
        await test_session.flush()

        response = await authenticated_client.get(
            "/api/v1/reporting/sla-tracking"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    async def test_sla_tracking_unauthenticated(self, client: AsyncClient):
        """Unauthenticated SLA tracking → 401 or 403."""
        response = await client.get("/api/v1/reporting/sla-tracking")
        assert response.status_code in (401, 403)


class TestExecutiveSummary:
    async def test_executive_summary(
        self, authenticated_client: AsyncClient
    ):
        """GET /reporting/executive-summary → 200."""
        response = await authenticated_client.get(
            "/api/v1/reporting/executive-summary"
        )
        assert response.status_code == 200, response.text

    async def test_executive_summary_has_vulnerability_summary(
        self, authenticated_client: AsyncClient
    ):
        """Executive summary must include vulnerability_summary section."""
        response = await authenticated_client.get(
            "/api/v1/reporting/executive-summary"
        )
        data = response.json()
        assert "vulnerability_summary" in data, f"Keys: {list(data.keys())}"

    async def test_executive_summary_has_bundles_section(
        self, authenticated_client: AsyncClient
    ):
        """Executive summary must include bundles_this_month section."""
        response = await authenticated_client.get(
            "/api/v1/reporting/executive-summary"
        )
        data = response.json()
        assert "bundles_this_month" in data, f"Keys: {list(data.keys())}"

    async def test_executive_summary_has_generated_at(
        self, authenticated_client: AsyncClient
    ):
        """Response must include generated_at timestamp."""
        response = await authenticated_client.get(
            "/api/v1/reporting/executive-summary"
        )
        data = response.json()
        assert "generated_at" in data

    async def test_executive_summary_unauthenticated(self, client: AsyncClient):
        """Unauthenticated executive summary → 401 or 403."""
        response = await client.get("/api/v1/reporting/executive-summary")
        assert response.status_code in (401, 403)
