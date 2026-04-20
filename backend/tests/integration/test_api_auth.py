"""
Integration tests for authentication API endpoints.

Tests demo login, /me profile, API key generation, and authorization.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestAuthAPI:
    """Integration tests for Auth API"""
    
    async def test_demo_login(self, client: AsyncClient):
        """Test demo login endpoint"""
        response = await client.get("/api/v1/auth/demo-login")
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
    
    async def test_me_endpoint_authenticated(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test /me profile endpoint with authenticated user"""
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role
        assert "tenant_id" in data
    
    async def test_me_endpoint_unauthorized(self, client: AsyncClient):
        """Test /me endpoint without authentication returns 401"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_api_key_generation(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test API key generation"""
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test API Key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("gw_")
    
    async def test_update_preferences(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test updating user preferences"""
        new_prefs = {
            "theme": "dark",
            "notifications": {
                "email": True,
                "slack": False
            }
        }
        
        response = await authenticated_client.patch(
            "/api/v1/auth/me/preferences",
            json={"preferences": new_prefs}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["preferences"]["theme"] == "dark"
    
    async def test_forbidden_access_wrong_role(
        self, viewer_client: AsyncClient
    ):
        """Test viewer cannot access admin endpoints (403)"""
        # Try to create a user (admin-only action)
        response = await viewer_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@example.com",
                "name": "New User",
                "role": "engineer"
            }
        )
        
        # Should be forbidden for viewer role
        assert response.status_code == 403
    
    async def test_logout(self, authenticated_client: AsyncClient):
        """Test logout endpoint"""
        response = await authenticated_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
