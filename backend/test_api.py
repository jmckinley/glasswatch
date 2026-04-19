#!/usr/bin/env python3
"""
Test API endpoints without a database.
"""
import asyncio
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Glasswatch"
    assert "version" in data
    print("✓ Root endpoint works")

def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health endpoint works")

def test_api_structure():
    """Test that API routes are properly mounted."""
    # This will fail with 404 if routes aren't mounted
    response = client.get("/api/v1/vulnerabilities")
    # We expect 500 (database error) not 404 (route not found)
    assert response.status_code in [500, 503], f"Expected database error, got {response.status_code}"
    print("✓ API routes are mounted correctly")

def test_cors_headers():
    """Test CORS is configured."""
    response = client.options("/", headers={"Origin": "http://localhost:3000"})
    assert "access-control-allow-origin" in response.headers
    print("✓ CORS headers configured")

if __name__ == "__main__":
    print("Testing Glasswatch API endpoints...\n")
    
    try:
        test_root()
        test_health()
        test_api_structure()
        test_cors_headers()
        print("\n✅ All API tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()