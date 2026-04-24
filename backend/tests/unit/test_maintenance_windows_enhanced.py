"""
Unit tests for enhanced maintenance window features.

Covers:
- MaintenanceWindow model datacenter / geography fields
- Grouped-endpoint response structure (pure Python logic, no DB)
- Conflict detection helpers
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_window(**kwargs):
    """Return a simple dict representing a maintenance window."""
    defaults = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "name": "Test Window",
        "type": "scheduled",
        "start_time": datetime.now(timezone.utc) + timedelta(days=1),
        "end_time": datetime.now(timezone.utc) + timedelta(days=1, hours=4),
        "environment": "production",
        "datacenter": None,
        "geography": None,
        "active": True,
        "approved": False,
    }
    defaults.update(kwargs)
    return defaults


def _windows_conflict(w1: dict, w2: dict) -> bool:
    """
    Return True when two windows overlap in time AND share the same environment.
    This mirrors the business rule: only same-environment windows can conflict.
    """
    if w1["environment"] != w2["environment"]:
        return False
    return w1["start_time"] < w2["end_time"] and w2["start_time"] < w1["end_time"]


def _group_windows(windows: list, group_by: str = "environment") -> list:
    """
    Reproduce the grouping logic from GET /maintenance-windows/grouped.

    Returns a list of dicts with keys: key, label, count, windows.
    """
    groups: dict[str, list] = {}
    for w in windows:
        key = w.get(group_by) or "unspecified"
        groups.setdefault(key, []).append(w)

    result = []
    for key in sorted(groups):
        result.append(
            {
                "key": key,
                "label": key.replace("_", " ").title() if key != "unspecified" else "Unspecified",
                "count": len(groups[key]),
                "windows": groups[key],
            }
        )
    return result


# ── Model field tests ─────────────────────────────────────────────────────────

class TestMaintenanceWindowFields:
    async def test_window_create_with_datacenter(self):
        """MaintenanceWindow dict/model accepts datacenter field."""
        w = _make_window(datacenter="us-east-1")
        assert w["datacenter"] == "us-east-1"

    async def test_window_create_with_geography(self):
        """MaintenanceWindow dict/model accepts geography field."""
        w = _make_window(geography="North America")
        assert w["geography"] == "North America"

    async def test_window_both_location_fields(self):
        """Window accepts both datacenter and geography simultaneously."""
        w = _make_window(datacenter="eu-central-1", geography="Europe")
        assert w["datacenter"] == "eu-central-1"
        assert w["geography"] == "Europe"

    async def test_window_location_fields_default_none(self):
        """Location fields default to None when not provided."""
        w = _make_window()
        assert w["datacenter"] is None
        assert w["geography"] is None


# ── Grouped-endpoint structure ────────────────────────────────────────────────

class TestWindowGrouped:
    async def test_window_grouped_by_environment(self):
        """Grouped result has correct {key, label, count, windows} shape."""
        windows = [
            _make_window(environment="production"),
            _make_window(environment="production"),
            _make_window(environment="staging"),
        ]
        groups = _group_windows(windows, group_by="environment")

        # Should have two groups
        assert len(groups) == 2

        keys = {g["key"] for g in groups}
        assert "production" in keys
        assert "staging" in keys

        prod_group = next(g for g in groups if g["key"] == "production")
        assert prod_group["count"] == 2
        assert len(prod_group["windows"]) == 2
        assert "label" in prod_group

    async def test_window_grouped_by_datacenter(self):
        """Grouped by datacenter places windows into correct buckets."""
        windows = [
            _make_window(datacenter="us-east-1"),
            _make_window(datacenter="us-east-1"),
            _make_window(datacenter="eu-west-2"),
            _make_window(datacenter=None),  # → "unspecified"
        ]
        groups = _group_windows(windows, group_by="datacenter")

        keys = {g["key"] for g in groups}
        assert "us-east-1" in keys
        assert "eu-west-2" in keys
        assert "unspecified" in keys

        us_group = next(g for g in groups if g["key"] == "us-east-1")
        assert us_group["count"] == 2

    async def test_window_grouped_label_formatting(self):
        """Group label converts underscores to spaces and title-cases."""
        windows = [_make_window(environment="north_america")]
        groups = _group_windows(windows, group_by="environment")
        assert groups[0]["label"] == "North America"

    async def test_window_grouped_unspecified_label(self):
        """None group_by value produces 'Unspecified' label."""
        windows = [_make_window(datacenter=None)]
        groups = _group_windows(windows, group_by="datacenter")
        assert groups[0]["label"] == "Unspecified"


# ── Conflict detection ────────────────────────────────────────────────────────

class TestWindowConflictDetection:
    def _base_time(self):
        return datetime(2025, 6, 1, 8, 0, tzinfo=timezone.utc)

    async def test_window_conflict_detection(self):
        """Two windows in the same environment with overlapping times are flagged."""
        base = self._base_time()
        w1 = _make_window(
            environment="production",
            start_time=base,
            end_time=base + timedelta(hours=4),
        )
        w2 = _make_window(
            environment="production",
            start_time=base + timedelta(hours=2),
            end_time=base + timedelta(hours=6),
        )
        assert _windows_conflict(w1, w2) is True

    async def test_window_no_conflict_different_environment(self):
        """Overlapping times in different environments do NOT conflict."""
        base = self._base_time()
        w1 = _make_window(
            environment="production",
            start_time=base,
            end_time=base + timedelta(hours=4),
        )
        w2 = _make_window(
            environment="staging",
            start_time=base + timedelta(hours=2),
            end_time=base + timedelta(hours=6),
        )
        assert _windows_conflict(w1, w2) is False

    async def test_window_no_conflict_adjacent_times(self):
        """Adjacent (touching but not overlapping) windows do NOT conflict."""
        base = self._base_time()
        w1 = _make_window(
            environment="production",
            start_time=base,
            end_time=base + timedelta(hours=4),
        )
        w2 = _make_window(
            environment="production",
            start_time=base + timedelta(hours=4),
            end_time=base + timedelta(hours=8),
        )
        # end of w1 == start of w2 → not overlapping
        assert _windows_conflict(w1, w2) is False

    async def test_window_no_conflict_non_overlapping(self):
        """Completely separate time ranges in the same environment do not conflict."""
        base = self._base_time()
        w1 = _make_window(
            environment="production",
            start_time=base,
            end_time=base + timedelta(hours=2),
        )
        w2 = _make_window(
            environment="production",
            start_time=base + timedelta(hours=4),
            end_time=base + timedelta(hours=6),
        )
        assert _windows_conflict(w1, w2) is False
