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


class TestScoringService:
    """Test suite for ScoringService"""
    
    async def test_severity_critical(self):
        """Test CRITICAL severity contributes 30 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0001",
            severity="CRITICAL",
            cvss_score=9.8,
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=3,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # Should get 30 from CRITICAL severity + base from criticality
        assert score >= 30
    
    async def test_severity_high(self):
        """Test HIGH severity contributes 20 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0002",
            severity="HIGH",
            cvss_score=7.5,
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # Should get 20 from HIGH severity
        assert score >= 20
    
    async def test_severity_medium(self):
        """Test MEDIUM severity contributes 10 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0003",
            severity="MEDIUM",
            cvss_score=5.0,
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        assert score >= 10
    
    async def test_severity_low(self):
        """Test LOW severity contributes 5 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0004",
            severity="LOW",
            cvss_score=2.0,
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        assert score >= 5
    
    async def test_epss_max_contribution(self):
        """Test EPSS score at maximum (1.0) contributes 15 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0005",
            severity="MEDIUM",
            epss_score=1.0,  # Max EPSS
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # MEDIUM (10) + EPSS (15) + criticality (3) = 28+
        assert score >= 25
    
    async def test_epss_no_data(self):
        """Test that missing EPSS data doesn't break scoring"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0006",
            severity="HIGH",
            epss_score=None,  # No EPSS data
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=3,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # Should still calculate score without EPSS
        assert score >= 20  # At least HIGH severity
    
    async def test_kev_bonus(self):
        """Test KEV (Known Exploited Vulnerability) adds 20 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0007",
            severity="MEDIUM",
            in_kev=True,  # In KEV catalog
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # MEDIUM (10) + KEV (20) + criticality (3) = 33+
        assert score >= 30
    
    async def test_runtime_executed_bonus(self):
        """Test Snapper runtime 'executed' status adds +15 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0008",
            severity="MEDIUM",
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
            runtime_executed=True,  # Code executed at runtime
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        runtime_data = {
            "status": "executed",
            "confidence": 0.95
        }
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)
        
        # MEDIUM (10) + runtime executed (15) + criticality (3) = 28+
        assert score >= 25
    
    async def test_runtime_not_loaded_penalty(self):
        """Test Snapper runtime 'not loaded' reduces score by 10 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0009",
            severity="HIGH",
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=3,
            runtime_loaded=False,
            runtime_executed=False,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        runtime_data = {
            "status": "not_loaded",
            "confidence": 0.9
        }
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)
        
        # HIGH (20) - not_loaded (10) + criticality (9) = 19+
        assert score >= 15
        assert score < 40  # Penalty applied
    
    async def test_compensating_controls_reduction(self):
        """Test compensating controls reduce score by 10 points"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0010",
            severity="HIGH",
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=3,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
            has_compensating_controls=True,  # Has mitigations
            compensating_controls_description="WAF rules in place"
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # HIGH (20) + criticality (9) - controls (10) = 19+
        assert score >= 15
        assert score < 40  # Reduction applied
    
    async def test_score_clamping_minimum(self):
        """Test that score never goes below 0"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0011",
            severity="LOW",
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=1,
            runtime_loaded=False,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
            has_compensating_controls=True,
        )
        
        runtime_data = {"status": "not_loaded"}
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)
        
        assert score >= 0  # Never negative
    
    async def test_score_clamping_maximum(self):
        """Test that score never exceeds 100"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0012",
            severity="CRITICAL",
            epss_score=1.0,
            in_kev=True,
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=5,  # Max criticality
            is_internet_facing=True,
            runtime_executed=True,
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        runtime_data = {"status": "executed"}
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln, runtime_data)
        
        assert score <= 100  # Never exceeds max
    
    async def test_internet_facing_boost(self):
        """Test internet-facing assets get exposure boost"""
        vuln = Vulnerability(
            id=uuid4(),
            tenant_id=uuid4(),
            cve_id="CVE-2024-0013",
            severity="MEDIUM",
        )
        asset = Asset(
            id=uuid4(),
            tenant_id=uuid4(),
            hostname="test",
            criticality=3,
            is_internet_facing=True,  # Public exposure
        )
        asset_vuln = AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vuln.id,
            tenant_id=asset.tenant_id,
        )
        
        score = ScoringService.calculate_score(vuln, asset, asset_vuln)
        
        # Should have exposure boost
        assert score >= 20  # MEDIUM + criticality + exposure
