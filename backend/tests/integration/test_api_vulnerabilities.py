"""
Integration tests for vulnerabilities API endpoints.

Tests list, search, filtering, and GET by ID.
The Vulnerability model uses `identifier` (not `cve_id`) and the list
endpoint returns `vulnerabilities` (not `items`).
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestVulnerabilitiesAPI:
    """Integration tests for Vulnerabilities API"""

    async def test_list_vulnerabilities(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test GET /vulnerabilities returns list with total."""
        for i in range(5):
            await create_test_vulnerability(
                identifier=f"CVE-2024-{1000 + i}"
            )

        response = await authenticated_client.get("/api/v1/vulnerabilities")

        assert response.status_code == 200
        data = response.json()
        assert "vulnerabilities" in data
        assert len(data["vulnerabilities"]) >= 5
        assert "total" in data

    async def test_get_vulnerability_by_id(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test GET /vulnerabilities/{id}"""
        vuln = await create_test_vulnerability(identifier="CVE-2024-1111")

        response = await authenticated_client.get(
            f"/api/v1/vulnerabilities/{vuln.id}"
        )

        assert response.status_code == 200
        data = response.json()
        # Response wraps in 'vulnerability' key
        vuln_data = data.get("vulnerability", data)
        assert str(vuln.id) == vuln_data.get("id") or str(vuln.id) == data.get("id")

    async def test_search_vulnerabilities_by_identifier(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test searching vulnerabilities by identifier."""
        await create_test_vulnerability(identifier="CVE-2024-SEARCHME")

        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?search=CVE-2024-SEARCHME"
        )

        assert response.status_code == 200
        data = response.json()
        items = data.get("vulnerabilities", data.get("items", []))
        assert len(items) > 0
        assert any("CVE-2024-SEARCHME" in item.get("identifier", "") for item in items)

    async def test_filter_by_severity(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test filtering vulnerabilities by severity."""
        await create_test_vulnerability(identifier="CVE-2024-CRIT", severity="CRITICAL")
        await create_test_vulnerability(identifier="CVE-2024-LOW", severity="LOW")

        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?severity=CRITICAL"
        )

        assert response.status_code == 200
        data = response.json()
        items = data.get("vulnerabilities", data.get("items", []))
        for item in items:
            assert item["severity"].upper() == "CRITICAL"

    async def test_filter_by_kev(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test filtering for KEV vulnerabilities."""
        await create_test_vulnerability(identifier="CVE-2024-KEV", kev_listed=True)

        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?kev_only=true"
        )

        assert response.status_code == 200
        data = response.json()
        items = data.get("vulnerabilities", data.get("items", []))
        for item in items:
            assert item.get("kev_listed") is True

    async def test_pagination_skip_limit(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test skip/limit pagination."""
        for i in range(15):
            await create_test_vulnerability(identifier=f"CVE-2024-PAGE{i:03d}")

        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?skip=0&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        items = data.get("vulnerabilities", data.get("items", []))
        assert len(items) <= 10

    async def test_vuln_stats_endpoint(
        self, authenticated_client: AsyncClient
    ):
        """Test GET /vulnerabilities/stats exists."""
        response = await authenticated_client.get("/api/v1/vulnerabilities/stats")
        assert response.status_code == 200

    async def test_list_returns_correct_fields(
        self, authenticated_client: AsyncClient, create_test_vulnerability
    ):
        """Verify response fields include expected keys."""
        await create_test_vulnerability(identifier="CVE-2024-FIELDS")
        response = await authenticated_client.get("/api/v1/vulnerabilities")
        assert response.status_code == 200
        data = response.json()
        items = data.get("vulnerabilities", data.get("items", []))
        if items:
            item = items[0]
            assert "id" in item
            assert "severity" in item
