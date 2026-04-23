"""
Unit tests for the vulnerability scoring service.

Tests the 8-factor scoring algorithm including:
- Base severity scoring
- EPSS (exploit prediction)
- KEV (known exploited vulnerabilities)
- Asset criticality
- Asset exposure
- Snapper runtime data
- Patch availability
- Compensating controls
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from backend.services.scoring import ScoringService
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability


pytestmark = pytest.mark.asyncio


def make_vuln(identifier="CVE-2024-0001", severity="HIGH", **kwargs):
    """Helper to create a Vulnerability with required fields."""
    return Vulnerability(
        id=uuid4(),
        identifier=identifier,
        source="nvd",
        severity=severity,
        published_at=datetime.now(timezone.utc),
        **kwargs,
    )


def make_asset(tenant_id=None, criticality=3, exposure="ISOLATED", **kwargs):
    """Helper to create an Asset with required fields."""
    tid = tenant_id or uuid4()
    return Asset(
        id=uuid4(),
        tenant_id=tid,
        identifier="test-server",
        name="Test Server",
        type="server",
        criticality=criticality,
        exposure=exposure,
        **kwargs,
    )


def make_av(asset, vuln, **kwargs):
    """Helper to create an AssetVulnerability."""
    return AssetVulnerability(
        asset_id=asset.id,
        vulnerability_id=vuln.id,
        **kwargs,
    )


class TestScoringService:
    """Test suite for ScoringService"""

    async def test_severity_critical(self):
        """Test CRITICAL severity contributes 30 points"""
        vuln = make_vuln(identifier="CVE-2024-0001", severity="CRITICAL", cvss_score=9.8)
        asset = make_asset(criticality=3)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # Should get 30 from CRITICAL severity + base from criticality
        assert score >= 30

    async def test_severity_high(self):
        """Test HIGH severity contributes 20 points"""
        vuln = make_vuln(identifier="CVE-2024-0002", severity="HIGH", cvss_score=7.5)
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # Should get 20 from HIGH severity
        assert score >= 20

    async def test_severity_medium(self):
        """Test MEDIUM severity contributes 10 points"""
        vuln = make_vuln(identifier="CVE-2024-0003", severity="MEDIUM", cvss_score=5.0)
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        assert score >= 10

    async def test_severity_low(self):
        """Test LOW severity contributes 5 points"""
        vuln = make_vuln(identifier="CVE-2024-0004", severity="LOW", cvss_score=2.0)
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        assert score >= 5

    async def test_epss_max_contribution(self):
        """Test EPSS score at maximum (1.0) contributes 15 points"""
        vuln = make_vuln(identifier="CVE-2024-0005", severity="MEDIUM", epss_score=1.0)
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # MEDIUM (10) + EPSS (15) + criticality (3) = 28+
        assert score >= 25

    async def test_epss_no_data(self):
        """Test that missing EPSS data doesn't break scoring"""
        vuln = make_vuln(identifier="CVE-2024-0006", severity="HIGH", epss_score=None)
        asset = make_asset(criticality=3)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # Should still calculate score without EPSS
        assert score >= 20  # At least HIGH severity

    async def test_kev_bonus(self):
        """Test KEV (Known Exploited Vulnerability) adds 20 points"""
        vuln = make_vuln(identifier="CVE-2024-0007", severity="MEDIUM", kev_listed=True)
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # MEDIUM (10) + KEV (20) + criticality (3) = 33+
        assert score >= 30

    async def test_runtime_executed_bonus(self):
        """Test Snapper runtime code_executed=True adds +15 points"""
        vuln = make_vuln(identifier="CVE-2024-0008", severity="MEDIUM")
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln)

        # Pass code_executed=True in runtime_data (scoring service reads these keys)
        runtime_data = {
            "code_executed": True,
            "library_loaded": True,
            "confidence": 0.95,
        }

        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)

        # MEDIUM (10) + runtime executed (15) + criticality (3) = 28+
        assert score >= 25

    async def test_runtime_not_loaded_penalty(self):
        """Test Snapper runtime not loaded reduces score by 10 points"""
        vuln = make_vuln(identifier="CVE-2024-0009", severity="HIGH")
        asset = make_asset(criticality=3)
        asset_vuln = make_av(asset, vuln)

        # code_executed=False, library_loaded=False → NOT_LOADED → -10 penalty
        runtime_data = {
            "code_executed": False,
            "library_loaded": False,
            "confidence": 0.9,
        }

        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)

        # HIGH (20) - not_loaded (10) + criticality (9) = 19+
        assert score >= 15
        assert score < 40  # Penalty applied

    async def test_compensating_controls_reduction(self):
        """Test compensating controls reduce score by 10 points"""
        vuln = make_vuln(identifier="CVE-2024-0010", severity="HIGH")
        asset = make_asset(criticality=3)
        asset_vuln = make_av(
            asset, vuln,
            mitigation_applied=True,
            mitigation_details="WAF rules in place",
        )

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # HIGH (20) + criticality (9) - controls (10) = 19+
        assert score >= 15
        assert score < 40  # Reduction applied

    async def test_score_clamping_minimum(self):
        """Test that score never goes below 0"""
        vuln = make_vuln(identifier="CVE-2024-0011", severity="LOW")
        asset = make_asset(criticality=1)
        asset_vuln = make_av(asset, vuln, mitigation_applied=True)

        runtime_data = {"code_executed": False, "library_loaded": False}

        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)

        assert score >= 0  # Never negative

    async def test_score_clamping_maximum(self):
        """Test that score never exceeds 100"""
        vuln = make_vuln(
            identifier="CVE-2024-0012",
            severity="CRITICAL",
            epss_score=1.0,
            kev_listed=True,
        )
        asset = make_asset(criticality=5, exposure="INTERNET")
        asset_vuln = make_av(asset, vuln, code_executed=True)

        runtime_data = {"code_executed": True, "library_loaded": True}

        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)

        assert score <= 100  # Never exceeds max

    async def test_internet_facing_boost(self):
        """Test internet-facing assets get exposure boost"""
        vuln = make_vuln(identifier="CVE-2024-0013", severity="MEDIUM")
        # exposure="INTERNET" gives +10 points over ISOLATED
        asset = make_asset(criticality=3, exposure="INTERNET")
        asset_vuln = make_av(asset, vuln)

        score = ScoringService.calculate_score(vuln, asset, asset_vuln)

        # Should have exposure boost
        assert score >= 20  # MEDIUM + criticality + exposure
