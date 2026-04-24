import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

class TestDebug:
    async def test_demo_body(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/demo-login")
        print(f"\nSTATUS: {resp.status_code}")
        print(f"BODY: {resp.text[:500]}")
        assert True
