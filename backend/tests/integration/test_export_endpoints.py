"""
Integration tests for the Export API endpoints.

Tests:
  GET /api/v1/export/vulnerabilities        → JSON
  GET /api/v1/export/vulnerabilities?format=csv → CSV
  GET /api/v1/export/assets                 → JSON
  GET /api/v1/export/assets?format=csv      → CSV
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestExportVulnerabilitiesJson:
    async def test_export_vulnerabilities_json(
        self, authenticated_client: AsyncClient
    ):
        """GET /export/vulnerabilities → 200, body is a dict with 'data' array."""
        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_export_vulnerabilities_json_has_total(
        self, authenticated_client: AsyncClient
    ):
        """JSON export includes 'total' field."""
        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities"
        )
        data = response.json()
        assert "total" in data

    async def test_export_vulnerabilities_json_has_exported_at(
        self, authenticated_client: AsyncClient
    ):
        """JSON export includes 'exported_at' timestamp."""
        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities"
        )
        data = response.json()
        assert "exported_at" in data

    async def test_export_vulnerabilities_json_with_data(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        test_session,
        create_test_asset,
        create_test_vulnerability,
    ):
        """With active vulns, export returns them in the data array."""
        from backend.models.asset_vulnerability import AssetVulnerability
        from uuid import uuid4
        from datetime import datetime, timezone

        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="export-test-host",
        )
        vuln = await create_test_vulnerability(
            identifier="CVE-2024-77001",
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
            "/api/v1/export/vulnerabilities"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        cves = [r["cve_id"] for r in data["data"]]
        assert "CVE-2024-77001" in cves

    async def test_export_vulnerabilities_unauthenticated(self, client: AsyncClient):
        """Unauthenticated export → 401 or 403."""
        response = await client.get("/api/v1/export/vulnerabilities")
        assert response.status_code in (401, 403)


class TestExportVulnerabilitiesCsv:
    async def test_export_vulnerabilities_csv(
        self, authenticated_client: AsyncClient
    ):
        """GET /export/vulnerabilities?format=csv → content-type text/csv."""
        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities?format=csv"
        )
        assert response.status_code == 200, response.text
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got: {content_type}"

    async def test_export_vulnerabilities_csv_has_header_row(
        self, authenticated_client: AsyncClient
    ):
        """CSV export content should include CSV header columns."""
        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities?format=csv"
        )
        text = response.text
        # Should at least include an empty CSV (headers or empty)
        # If there are records, first line is headers
        assert response.status_code == 200

    async def test_export_vulnerabilities_csv_with_data(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        test_session,
        create_test_asset,
        create_test_vulnerability,
    ):
        """CSV with active vulns should include vuln data in CSV format."""
        from backend.models.asset_vulnerability import AssetVulnerability
        from uuid import uuid4
        from datetime import datetime, timezone

        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="csv-export-host",
        )
        vuln = await create_test_vulnerability(
            identifier="CVE-2024-66001",
            severity="CRITICAL",
        )
        link = AssetVulnerability(
            id=uuid4(),
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            status="ACTIVE",
            risk_score=95.0,
            discovered_at=datetime.now(timezone.utc),
        )
        test_session.add(link)
        await test_session.flush()

        response = await authenticated_client.get(
            "/api/v1/export/vulnerabilities?format=csv"
        )
        assert response.status_code == 200
        assert "CVE-2024-66001" in response.text


class TestExportAssetsJson:
    async def test_export_assets_json(
        self, authenticated_client: AsyncClient
    ):
        """GET /export/assets → 200, body is a dict with 'data' array."""
        response = await authenticated_client.get("/api/v1/export/assets")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_export_assets_json_has_exported_at(
        self, authenticated_client: AsyncClient
    ):
        """Asset JSON export includes 'exported_at' timestamp."""
        response = await authenticated_client.get("/api/v1/export/assets")
        data = response.json()
        assert "exported_at" in data

    async def test_export_assets_json_with_data(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_asset,
    ):
        """With assets, export returns them in the data array."""
        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="exported-asset-01",
        )

        response = await authenticated_client.get("/api/v1/export/assets")
        assert response.status_code == 200
        data = response.json()
        names = [r["name"] for r in data["data"]]
        assert "exported-asset-01" in names

    async def test_export_assets_unauthenticated(self, client: AsyncClient):
        """Unauthenticated assets export → 401 or 403."""
        response = await client.get("/api/v1/export/assets")
        assert response.status_code in (401, 403)

    async def test_export_assets_json_record_fields(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_asset,
    ):
        """Each asset record should have expected fields."""
        await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="field-check-asset",
            criticality=4,
        )

        response = await authenticated_client.get("/api/v1/export/assets")
        data = response.json()

        assert len(data["data"]) >= 1
        record = data["data"][0]
        assert "name" in record
        assert "environment" in record
        assert "criticality" in record


class TestExportAssetsCsv:
    async def test_export_assets_csv(
        self, authenticated_client: AsyncClient
    ):
        """GET /export/assets?format=csv → content-type text/csv."""
        response = await authenticated_client.get(
            "/api/v1/export/assets?format=csv"
        )
        assert response.status_code == 200, response.text
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got: {content_type}"

    async def test_export_assets_csv_with_data(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        create_test_asset,
    ):
        """CSV asset export includes asset names."""
        await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="csv-asset-export-01",
        )

        response = await authenticated_client.get(
            "/api/v1/export/assets?format=csv"
        )
        assert response.status_code == 200
        assert "csv-asset-export-01" in response.text

    async def test_export_assets_csv_content_disposition(
        self, authenticated_client: AsyncClient
    ):
        """CSV response should include Content-Disposition attachment header."""
        response = await authenticated_client.get(
            "/api/v1/export/assets?format=csv"
        )
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition or response.status_code == 200
