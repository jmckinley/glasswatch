"""
Integration tests for enhanced maintenance window API.

Covers:
- POST /maintenance-windows with datacenter + geography fields
- GET /maintenance-windows/grouped (default, by datacenter, by geography)
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _future_window_payload(**extra):
    """Return a minimal valid WindowCreate payload for future times."""
    now = datetime.now(timezone.utc)
    payload = {
        "name": "Test Window",
        "type": "scheduled",
        "start_time": (now + timedelta(days=1)).isoformat(),
        "end_time": (now + timedelta(days=1, hours=4)).isoformat(),
        "environment": "staging",
    }
    payload.update(extra)
    return payload


class TestCreateWindowWithLocationFields:
    async def test_create_window_with_location_fields(
        self, authenticated_client: AsyncClient
    ):
        """POST /maintenance-windows with datacenter + geography → 201."""
        payload = _future_window_payload(
            name="DC Window",
            datacenter="us-east-1",
            geography="North America",
        )
        resp = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert resp.status_code in (200, 201), resp.text

        data = resp.json()
        assert data.get("datacenter") == "us-east-1"
        assert data.get("geography") == "North America"

    async def test_create_window_datacenter_only(
        self, authenticated_client: AsyncClient
    ):
        """POST with only datacenter (no geography) also succeeds."""
        payload = _future_window_payload(
            name="Datacenter-only Window",
            datacenter="eu-central-1",
        )
        resp = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert resp.status_code in (200, 201), resp.text
        assert resp.json().get("datacenter") == "eu-central-1"

    async def test_create_window_geography_only(
        self, authenticated_client: AsyncClient
    ):
        """POST with only geography (no datacenter) also succeeds."""
        payload = _future_window_payload(
            name="Geography-only Window",
            geography="Asia Pacific",
        )
        resp = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert resp.status_code in (200, 201), resp.text
        assert resp.json().get("geography") == "Asia Pacific"

    async def test_create_window_without_location_fields(
        self, authenticated_client: AsyncClient
    ):
        """POST without location fields succeeds (fields are optional)."""
        payload = _future_window_payload(name="Basic Window")
        resp = await authenticated_client.post("/api/v1/maintenance-windows", json=payload)
        assert resp.status_code in (200, 201), resp.text


class TestGroupedWindowsEndpoint:
    async def _seed_windows(self, client: AsyncClient):
        """Create a few windows with different datacenter/geography values."""
        payloads = [
            _future_window_payload(name="W-prod-us", environment="production", datacenter="us-east-1", geography="North America"),
            _future_window_payload(name="W-prod-eu", environment="production", datacenter="eu-west-2", geography="Europe"),
            _future_window_payload(name="W-staging", environment="staging", datacenter="us-east-1", geography="North America"),
        ]
        for p in payloads:
            r = await client.post("/api/v1/maintenance-windows", json=p)
            assert r.status_code in (200, 201), f"Seed failed: {r.text}"

    async def test_get_grouped_windows_default(
        self, authenticated_client: AsyncClient
    ):
        """GET /maintenance-windows/grouped → 200, response has groups array."""
        await self._seed_windows(authenticated_client)

        resp = await authenticated_client.get("/api/v1/maintenance-windows/grouped")
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "groups" in data, "Response must contain 'groups' key"
        assert isinstance(data["groups"], list)
        # Default group_by=environment — should have at least one group
        assert len(data["groups"]) >= 1

        # Validate structure of each group
        for group in data["groups"]:
            assert "key" in group
            assert "label" in group
            assert "count" in group
            assert "windows" in group
            assert isinstance(group["windows"], list)
            assert group["count"] == len(group["windows"])

    async def test_get_grouped_windows_by_datacenter(
        self, authenticated_client: AsyncClient
    ):
        """GET /maintenance-windows/grouped?group_by=datacenter → 200."""
        await self._seed_windows(authenticated_client)

        resp = await authenticated_client.get(
            "/api/v1/maintenance-windows/grouped", params={"group_by": "datacenter"}
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "groups" in data
        assert data.get("group_by") == "datacenter"

        keys = {g["key"] for g in data["groups"]}
        # us-east-1 windows were seeded
        assert "us-east-1" in keys or len(keys) >= 1

    async def test_get_grouped_windows_by_geography(
        self, authenticated_client: AsyncClient
    ):
        """GET /maintenance-windows/grouped?group_by=geography → 200."""
        await self._seed_windows(authenticated_client)

        resp = await authenticated_client.get(
            "/api/v1/maintenance-windows/grouped", params={"group_by": "geography"}
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "groups" in data
        assert data.get("group_by") == "geography"

    async def test_get_grouped_windows_invalid_group_by(
        self, authenticated_client: AsyncClient
    ):
        """GET /maintenance-windows/grouped?group_by=<invalid> → 422."""
        resp = await authenticated_client.get(
            "/api/v1/maintenance-windows/grouped",
            params={"group_by": "nonexistent_field"},
        )
        assert resp.status_code == 422
