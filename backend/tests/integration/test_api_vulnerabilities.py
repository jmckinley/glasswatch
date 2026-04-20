"""
Integration tests for vulnerabilities API endpoints.

Tests CRUD operations, search, filtering, and pagination.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestVulnerabilitiesAPI:
    """Integration tests for Vulnerabilities API"""
    
    async def test_create_vulnerability(
        self, authenticated_client: AsyncClient
    ):
        """Test POST /vulnerabilities"""
        response = await authenticated_client.post(
            "/api/v1/vulnerabilities",
            json={
                "cve_id": "CVE-2024-9999",
                "title": "Test Vulnerability",
                "description": "A test vulnerability",
                "severity": "HIGH",
                "cvss_score": 7.5,
                "epss_score": 0.5,
                "affected_products": ["test-product"],
                "references": ["https://example.com/cve"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["cve_id"] == "CVE-2024-9999"
        assert data["severity"] == "HIGH"
        assert "id" in data
    
    async def test_get_vulnerability_by_id(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test GET /vulnerabilities/{id}"""
        vuln = await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-1111"
        )
        
        response = await authenticated_client.get(
            f"/api/v1/vulnerabilities/{vuln.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(vuln.id)
        assert data["cve_id"] == "CVE-2024-1111"
    
    async def test_list_vulnerabilities(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test GET /vulnerabilities with pagination"""
        # Create multiple vulnerabilities
        for i in range(5):
            await create_test_vulnerability(
                tenant_id=str(test_tenant.id),
                cve_id=f"CVE-2024-{1000+i}"
            )
        
        response = await authenticated_client.get("/api/v1/vulnerabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 5
        assert "total" in data
    
    async def test_search_vulnerabilities_by_cve(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test searching vulnerabilities by CVE ID"""
        await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-SEARCH"
        )
        
        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?search=CVE-2024-SEARCH"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert any("CVE-2024-SEARCH" in item["cve_id"] for item in data["items"])
    
    async def test_filter_by_severity(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test filtering vulnerabilities by severity"""
        await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-CRIT",
            severity="CRITICAL"
        )
        await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-LOW",
            severity="LOW"
        )
        
        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?severity=CRITICAL"
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["severity"] == "CRITICAL"
    
    async def test_filter_by_kev(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test filtering for KEV vulnerabilities"""
        await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-KEV",
            in_kev=True
        )
        
        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?in_kev=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["in_kev"] is True
    
    async def test_pagination(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test pagination parameters"""
        # Create 15 vulnerabilities
        for i in range(15):
            await create_test_vulnerability(
                tenant_id=str(test_tenant.id),
                cve_id=f"CVE-2024-PAGE{i:03d}"
            )
        
        # Get first page
        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?page=1&page_size=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        
        # Get second page
        response = await authenticated_client.get(
            "/api/v1/vulnerabilities?page=2&page_size=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 5
    
    async def test_update_vulnerability(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test PATCH /vulnerabilities/{id}"""
        vuln = await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-UPDATE"
        )
        
        response = await authenticated_client.patch(
            f"/api/v1/vulnerabilities/{vuln.id}",
            json={"epss_score": 0.95}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["epss_score"] == 0.95
    
    async def test_delete_vulnerability(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability
    ):
        """Test DELETE /vulnerabilities/{id}"""
        vuln = await create_test_vulnerability(
            tenant_id=str(test_tenant.id),
            cve_id="CVE-2024-DELETE"
        )
        
        response = await authenticated_client.delete(
            f"/api/v1/vulnerabilities/{vuln.id}"
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        response = await authenticated_client.get(
            f"/api/v1/vulnerabilities/{vuln.id}"
        )
        assert response.status_code == 404
