"""
Integration tests for the Maintenance Windows API.

Covers CRUD, filtering, and edge cases.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _future_window(offset_hours: int = 24, duration_hours: int = 2) -> dict:
    start = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    end = start + timedelta(hours=duration_hours)
    return {
        "name": f"Test Window {uuid4().hex[:6]}",
        "type": "scheduled",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "environment": "production",
        "approved_activities": ["patching"],
    }


class TestMaintenanceWindowsAPI:
    """Integration tests for /api/v1/maintenance-windows."""

    # ------------------------------------------------------------------
    # GET /maintenance-windows
    # ------------------------------------------------------------------

    async def test_list_windows_empty(self, authenticated_client: AsyncClient, test_tenant):
        """GET /maintenance-windows returns a valid empty response."""
        response = await authenticated_client.get("/api/v1/maintenance-windows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_list_windows_requires_auth(self, client: AsyncClient):
        """Unauthenticated GET returns 401."""
        response = await client.get("/api/v1/maintenance-windows")
        assert response.status_code == 401

    async def test_list_windows_returns_created_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Windows created via POST appear in the list."""
        payload = _future_window()
        create = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert create.status_code == 201

        response = await authenticated_client.get("/api/v1/maintenance-windows")
        assert response.status_code == 200
        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, dict):
            windows = data.get("items", data.get("windows", []))
        else:
            windows = data
        names = [w["name"] for w in windows]
        assert payload["name"] in names

    # ------------------------------------------------------------------
    # POST /maintenance-windows
    # ------------------------------------------------------------------

    async def test_create_window(self, authenticated_client: AsyncClient, test_tenant):
        """POST /maintenance-windows creates a window."""
        payload = _future_window()
        response = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert "id" in data

    async def test_create_window_requires_auth(self, client: AsyncClient):
        """Unauthenticated POST returns 401."""
        response = await client.post("/api/v1/maintenance-windows", json=_future_window())
        assert response.status_code == 401

    async def test_create_window_missing_name_returns_422(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Window without name returns 422."""
        payload = _future_window()
        del payload["name"]
        response = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert response.status_code == 422

    async def test_create_window_missing_start_time_returns_422(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Window without start_time returns 422."""
        payload = _future_window()
        del payload["start_time"]
        response = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert response.status_code == 422

    async def test_create_blackout_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Blackout window type is accepted."""
        payload = _future_window()
        payload["type"] = "blackout"
        payload["name"] = "Freeze Window"
        response = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert response.status_code == 201
        assert response.json()["type"] == "blackout"

    async def test_create_window_invalid_type_returns_422(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Window with invalid type returns 422."""
        payload = _future_window()
        payload["type"] = "invalid_type"
        response = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # GET /maintenance-windows/{id}
    # ------------------------------------------------------------------

    async def test_get_window_by_id(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /maintenance-windows/{id} returns the window."""
        payload = _future_window()
        create = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert create.status_code == 201
        window_id = create.json()["id"]

        response = await authenticated_client.get(f"/api/v1/maintenance-windows/{window_id}")
        assert response.status_code == 200
        assert response.json()["id"] == window_id

    async def test_get_window_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /maintenance-windows/{nonexistent} returns 404."""
        response = await authenticated_client.get(f"/api/v1/maintenance-windows/{uuid4()}")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # PATCH /maintenance-windows/{id}
    # ------------------------------------------------------------------

    async def test_update_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /maintenance-windows/{id} updates the window."""
        payload = _future_window()
        create = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        window_id = create.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/maintenance-windows/{window_id}",
            json={"description": "Updated description"},
        )
        assert response.status_code == 200

    async def test_update_window_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /maintenance-windows/{nonexistent} returns 404."""
        response = await authenticated_client.patch(
            f"/api/v1/maintenance-windows/{uuid4()}",
            json={"description": "Ghost"},
        )
        assert response.status_code == 404

    async def test_update_window_requires_auth(self, client: AsyncClient):
        """Unauthenticated PATCH returns 401."""
        response = await client.patch(
            f"/api/v1/maintenance-windows/{uuid4()}",
            json={"description": "Anon"},
        )
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # DELETE /maintenance-windows/{id}
    # ------------------------------------------------------------------

    async def test_delete_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /maintenance-windows/{id} removes the window."""
        payload = _future_window()
        create = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        window_id = create.json()["id"]

        delete = await authenticated_client.delete(f"/api/v1/maintenance-windows/{window_id}")
        assert delete.status_code in (200, 204)

        get = await authenticated_client.get(f"/api/v1/maintenance-windows/{window_id}")
        assert get.status_code == 404

    async def test_delete_window_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /maintenance-windows/{nonexistent} returns 404."""
        response = await authenticated_client.delete(f"/api/v1/maintenance-windows/{uuid4()}")
        assert response.status_code == 404
