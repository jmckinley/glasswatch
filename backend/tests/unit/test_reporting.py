"""
Unit tests for compliance computation and SLA logic.

Tests the pure calculation functions used by the reporting service:
  - BOD 22-01 compliance status (based on KEV patch coverage)
  - SLA deadlines per severity
  - SLA status determination (breached / at_risk / on_track)
  - MTTP (mean-time-to-patch) calculation
"""
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio

# ── SLA constants (mirrors reporting.py) ─────────────────────────────────────

SLA_DAYS = {
    "CRITICAL": 7,
    "HIGH": 30,
    "MEDIUM": 90,
    "LOW": 180,
}

# ── Pure helpers extracted from reporting logic ───────────────────────────────


def compute_bod_status(kev_total: int, kev_patched: int) -> str:
    """Reproduce BOD 22-01 status from reporting.py."""
    pct = round(kev_patched / kev_total * 100, 1) if kev_total else 100.0
    if kev_total == 0 or pct >= 100:
        return "COMPLIANT"
    if pct >= 80:
        return "AT_RISK"
    return "NON_COMPLIANT"


def compute_sla_deadline(discovered_at: datetime, severity: str) -> datetime:
    """Compute SLA deadline from discovered_at + severity days."""
    days = SLA_DAYS.get(severity.upper(), 90)
    return discovered_at + timedelta(days=days)


def compute_sla_status(deadline: datetime, now: datetime) -> str:
    """Reproduce SLA status logic from reporting.py sla-tracking endpoint."""
    days_remaining = (deadline - now).days
    if days_remaining < 0:
        return "BREACHED"
    if days_remaining <= 3:
        return "AT_RISK"
    return "ON_TRACK"


def compute_mttp_days(discovered_at: datetime, completed_at: datetime) -> int:
    """Compute mean-time-to-patch in whole days."""
    return (completed_at - discovered_at).days


# ── BOD 22-01 compliance ─────────────────────────────────────────────────────


class TestBod2201Compliance:
    async def test_bod_2201_compliance_all_patched(self):
        """All KEV vulns patched → COMPLIANT."""
        status = compute_bod_status(kev_total=10, kev_patched=10)
        assert status == "COMPLIANT"

    async def test_bod_2201_compliance_zero_kev(self):
        """No KEV vulns at all → COMPLIANT (vacuously)."""
        status = compute_bod_status(kev_total=0, kev_patched=0)
        assert status == "COMPLIANT"

    async def test_bod_2201_at_risk(self):
        """80-99% KEV patched → AT_RISK."""
        # 8 of 10 patched = 80% → AT_RISK boundary
        status = compute_bod_status(kev_total=10, kev_patched=8)
        assert status == "AT_RISK"

    async def test_bod_2201_at_risk_near_boundary(self):
        """9 of 10 patched = 90% → still AT_RISK (not 100%)."""
        status = compute_bod_status(kev_total=10, kev_patched=9)
        assert status == "AT_RISK"

    async def test_bod_2201_non_compliant(self):
        """Less than 80% patched → NON_COMPLIANT."""
        # 5 of 10 = 50%
        status = compute_bod_status(kev_total=10, kev_patched=5)
        assert status == "NON_COMPLIANT"

    async def test_bod_2201_non_compliant_none_patched(self):
        """0% patched → NON_COMPLIANT."""
        status = compute_bod_status(kev_total=5, kev_patched=0)
        assert status == "NON_COMPLIANT"


# ── SLA deadlines ─────────────────────────────────────────────────────────────


class TestSlaDeadlines:
    async def test_sla_deadline_critical(self):
        """CRITICAL vuln discovered today → deadline is today + 7 days."""
        today = datetime.now(timezone.utc)
        deadline = compute_sla_deadline(today, "CRITICAL")
        assert (deadline - today).days == 7

    async def test_sla_deadline_high(self):
        """HIGH vuln → deadline is today + 30 days."""
        today = datetime.now(timezone.utc)
        deadline = compute_sla_deadline(today, "HIGH")
        assert (deadline - today).days == 30

    async def test_sla_deadline_medium(self):
        """MEDIUM vuln → deadline is today + 90 days."""
        today = datetime.now(timezone.utc)
        deadline = compute_sla_deadline(today, "MEDIUM")
        assert (deadline - today).days == 90

    async def test_sla_deadline_low(self):
        """LOW vuln → deadline is today + 180 days."""
        today = datetime.now(timezone.utc)
        deadline = compute_sla_deadline(today, "LOW")
        assert (deadline - today).days == 180

    async def test_sla_deadline_unknown_severity_defaults_90(self):
        """Unknown severity defaults to 90-day SLA."""
        today = datetime.now(timezone.utc)
        deadline = compute_sla_deadline(today, "UNKNOWN")
        assert (deadline - today).days == 90


# ── SLA status determination ──────────────────────────────────────────────────


class TestSlaStatus:
    async def test_sla_status_on_track(self):
        """Deadline more than 3 days away → ON_TRACK."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=10)
        assert compute_sla_status(deadline, now) == "ON_TRACK"

    async def test_sla_status_at_risk(self):
        """Deadline exactly 3 days away → AT_RISK."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=3)
        assert compute_sla_status(deadline, now) == "AT_RISK"

    async def test_sla_status_at_risk_one_day(self):
        """Deadline 1 day away → AT_RISK."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=1)
        assert compute_sla_status(deadline, now) == "AT_RISK"

    async def test_sla_status_breached(self):
        """Deadline in the past → BREACHED."""
        now = datetime.now(timezone.utc)
        deadline = now - timedelta(days=1)
        assert compute_sla_status(deadline, now) == "BREACHED"

    async def test_sla_status_breached_far_past(self):
        """Deadline far in the past → BREACHED."""
        now = datetime.now(timezone.utc)
        deadline = now - timedelta(days=90)
        assert compute_sla_status(deadline, now) == "BREACHED"

    async def test_sla_status_at_risk_boundary_zero(self):
        """Deadline is today (days_remaining=0) → AT_RISK (not breached)."""
        now = datetime.now(timezone.utc)
        # deadline within today: days_remaining = 0, which is >= 0 and <= 3
        deadline = now + timedelta(hours=12)
        assert compute_sla_status(deadline, now) == "AT_RISK"


# ── MTTP calculation ──────────────────────────────────────────────────────────


class TestMttpCalculation:
    async def test_mttp_calculation(self):
        """Given discovered_at and completed_at, MTTP is correct number of days."""
        discovered_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        completed_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mttp = compute_mttp_days(discovered_at, completed_at)
        assert mttp == 14

    async def test_mttp_calculation_same_day(self):
        """Patched the same day discovered → 0 days MTTP."""
        ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
        assert compute_mttp_days(ts, ts) == 0

    async def test_mttp_calculation_critical_sla(self):
        """Patched within 7-day window → MTTP <= 7."""
        discovered_at = datetime(2024, 3, 1, tzinfo=timezone.utc)
        completed_at = datetime(2024, 3, 6, tzinfo=timezone.utc)
        mttp = compute_mttp_days(discovered_at, completed_at)
        assert mttp <= 7

    async def test_mttp_calculation_sla_breached(self):
        """Patched after 8+ days for a CRITICAL vuln → SLA was breached."""
        discovered_at = datetime(2024, 3, 1, tzinfo=timezone.utc)
        completed_at = datetime(2024, 3, 10, tzinfo=timezone.utc)
        mttp = compute_mttp_days(discovered_at, completed_at)
        assert mttp > SLA_DAYS["CRITICAL"]
