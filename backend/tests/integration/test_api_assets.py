"""
Integration tests for assets API endpoints.

Tests CRUD operations and bulk import.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestAssetsAPI:
    """Integration tests for Assets API"""
    
    async def test_create_asset(self, authenticated_client: AsyncClient):
        """Test POST /assets"""
        response = await authenticated_client.post(
            "/api/v1/assets",
            json={
                "hostname": "web-server-01",
                "ip_address": "10.0.1.50",
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "criticality": 4,
                "is_internet_facing": True,
                "environment": "production",
                "tags": {"region": "us-east-1", "team": "platform"}
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["hostname"] == "web-server-01"
        assert data["criticality"] == 4
        assert "id" in data
    
    async def test_get_asset_by_id(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test GET /assets/{id}"""
        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="db-server-01"
        )
        
        response = await authenticated_client.get(f"/api/v1/assets/{asset.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(asset.id)
        assert data["hostname"] == "db-server-01"
    
    async def test_list_assets(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test GET /assets"""
        # Create multiple assets
        for i in range(3):
            await create_test_asset(
                tenant_id=str(test_tenant.id),
                hostname=f"server-{i}"
            )
        
        response = await authenticated_client.get("/api/v1/assets")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3
    
    async def test_filter_by_criticality(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test filtering assets by criticality"""
        await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="critical-server",
            criticality=5
        )
        await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="low-crit-server",
            criticality=1
        )
        
        response = await authenticated_client.get(
            "/api/v1/assets?min_criticality=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["criticality"] >= 5
    
    async def test_filter_internet_facing(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test filtering for internet-facing assets"""
        await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="public-web",
            is_internet_facing=True
        )
        
        response = await authenticated_client.get(
            "/api/v1/assets?is_internet_facing=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_internet_facing"] is True
    
    async def test_update_asset(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test PATCH /assets/{id}"""
        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="update-test"
        )
        
        response = await authenticated_client.patch(
            f"/api/v1/assets/{asset.id}",
            json={"criticality": 5, "tags": {"updated": "true"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["criticality"] == 5
        assert data["tags"]["updated"] == "true"
    
    async def test_delete_asset(
        self, authenticated_client: AsyncClient, test_tenant, create_test_asset
    ):
        """Test DELETE /assets/{id}"""
        asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="delete-test"
        )
        
        response = await authenticated_client.delete(f"/api/v1/assets/{asset.id}")
        
        assert response.status_code == 204
        
        # Verify deleted
        response = await authenticated_client.get(f"/api/v1/assets/{asset.id}")
        assert response.status_code == 404
    
    async def test_bulk_import_assets(self, authenticated_client: AsyncClient):
        """Test POST /assets/bulk-import"""
        assets_data = [
            {
                "hostname": "bulk-server-01",
                "ip_address": "10.0.2.10",
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "criticality": 3
            },
            {
                "hostname": "bulk-server-02",
                "ip_address": "10.0.2.11",
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "criticality": 4
            },
            {
                "hostname": "bulk-server-03",
                "ip_address": "10.0.2.12",
                "os_type": "RHEL",
                "os_version": "8.5",
                "criticality": 5
            }
        ]
        
        response = await authenticated_client.post(
            "/api/v1/assets/bulk-import",
            json={"assets": assets_data}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "imported" in data or "count" in data
        assert data.get("imported", data.get("count", 0)) == 3
    
    async def test_bulk_import_validation(
        self, authenticated_client: AsyncClient
    ):
        """Test bulk import with invalid data"""
        assets_data = [
            {
                "hostname": "valid-server",
                "ip_address": "10.0.2.20",
                "criticality": 3
            },
            {
                # Missing required hostname
                "ip_address": "10.0.2.21",
                "criticality": 2
            }
        ]
        
        response = await authenticated_client.post(
            "/api/v1/assets/bulk-import",
            json={"assets": assets_data}
        )
        
        # Should either reject entirely or report errors
        assert response.status_code in [201, 400, 422]
        
        if response.status_code == 201:
            data = response.json()
            # Should report some failures
            assert "errors" in data or data.get("imported", 2) < 2
