"""
Vulnerability scoring service - the heart of Glasswatch.

Implements our proven 8-factor scoring algorithm with Snapper runtime integration.
This is what makes our prioritization better than CVSS-based systems.
"""
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability


class ScoringService:
    """
    Multi-factor vulnerability scoring that combines:
    1. Base severity (CVSS)
    2. EPSS (exploit prediction)
    3. KEV (known exploited)
    4. Asset criticality
    5. Asset exposure
    6. Snapper runtime data (±25 points!)
    7. Patch availability
    8. Compensating controls
    
    Scores range from 0-100, with 70+ being high risk.
    """
    
    # Scoring weights (proven from previous implementation)
    SEVERITY_WEIGHTS = {
        "CRITICAL": 30,
        "HIGH": 20,
        "MEDIUM": 10,
        "LOW": 5,
        "NONE": 0,
    }
    
    EXPOSURE_WEIGHTS = {
        "INTERNET": 10,
        "INTRANET": 5,
        "ISOLATED": 0,
    }
    
    # These constants tune the algorithm
    EPSS_MAX_POINTS = 15
    KEV_BONUS_POINTS = 20
    CRITICALITY_MULTIPLIER = 3  # criticality * 3 = max 15 points
    
    # Snapper runtime modifiers - our key differentiator!
    RUNTIME_EXECUTED_BONUS = 15
    RUNTIME_LOADED_NEUTRAL = 0
    RUNTIME_NOT_LOADED_PENALTY = -10
    
    # Negative modifiers
    NO_PATCH_PENALTY = -5
    COMPENSATING_CONTROLS_PENALTY = -10
    
    @staticmethod
    def calculate_score(
        vulnerability: Vulnerability,
        asset: Asset,
        asset_vulnerability: AssetVulnerability,
        runtime_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Calculate risk score for a specific vulnerability on a specific asset.
        
        This is called for each asset-vulnerability pair and determines
        patching priority.
        
        Args:
            vulnerability: The vulnerability entity
            asset: The affected asset
            asset_vulnerability: Junction with additional context
            runtime_data: Optional Snapper runtime analysis
            
        Returns:
            Risk score from 0-100
        """
        score = 0
        factors = {}
        
        # 1. Base severity (0-30 points)
        severity = vulnerability.severity or "MEDIUM"
        severity_score = ScoringService.SEVERITY_WEIGHTS.get(
            severity.upper(), 
            ScoringService.SEVERITY_WEIGHTS["MEDIUM"]
        )
        score += severity_score
        factors["severity"] = {
            "value": severity,
            "points": severity_score
        }
        
        # 2. EPSS score (0-15 points)
        if vulnerability.epss_score is not None:
            epss_points = int(vulnerability.epss_score * ScoringService.EPSS_MAX_POINTS)
            score += epss_points
            factors["epss"] = {
                "value": vulnerability.epss_score,
                "points": epss_points
            }
        
        # 3. KEV listing (+20 points if listed)
        if vulnerability.kev_listed:
            score += ScoringService.KEV_BONUS_POINTS
            factors["kev"] = {
                "value": True,
                "points": ScoringService.KEV_BONUS_POINTS
            }
        
        # 4. Asset criticality (0-15 points)
        criticality_points = asset.criticality * ScoringService.CRITICALITY_MULTIPLIER
        score += criticality_points
        factors["criticality"] = {
            "value": asset.criticality,
            "points": criticality_points
        }
        
        # 5. Asset exposure (0-10 points)
        exposure = asset.exposure or "ISOLATED"
        exposure_points = ScoringService.EXPOSURE_WEIGHTS.get(
            exposure.upper(),
            ScoringService.EXPOSURE_WEIGHTS["ISOLATED"]
        )
        score += exposure_points
        factors["exposure"] = {
            "value": exposure,
            "points": exposure_points
        }
        
        # 6. SNAPPER RUNTIME DATA - THE GAME CHANGER (±25 points)
        # This is our key differentiator from other tools
        runtime_points = 0
        
        # Use runtime data from parameter or asset_vulnerability
        if runtime_data:
            code_executed = runtime_data.get("code_executed")
            library_loaded = runtime_data.get("library_loaded")
        else:
            code_executed = asset_vulnerability.code_executed
            library_loaded = asset_vulnerability.library_loaded
        
        if code_executed:
            # Vulnerable code is actually executing - HIGH PRIORITY
            runtime_points = ScoringService.RUNTIME_EXECUTED_BONUS
            factors["runtime"] = {
                "value": "EXECUTED",
                "points": runtime_points,
                "detail": "Vulnerable code confirmed executing in production"
            }
        elif library_loaded:
            # Library is loaded but code path not executed - MEDIUM
            runtime_points = ScoringService.RUNTIME_LOADED_NEUTRAL
            factors["runtime"] = {
                "value": "LOADED",
                "points": runtime_points,
                "detail": "Vulnerable library loaded but not executed"
            }
        else:
            # Not even loaded - LOW PRIORITY
            runtime_points = ScoringService.RUNTIME_NOT_LOADED_PENALTY
            factors["runtime"] = {
                "value": "NOT_LOADED",
                "points": runtime_points,
                "detail": "Vulnerable code not loaded in runtime"
            }
        
        score += runtime_points
        
        # 7. Patch availability (-5 if no patch available)
        if not vulnerability.patch_available:
            score += ScoringService.NO_PATCH_PENALTY
            factors["no_patch"] = {
                "value": True,
                "points": ScoringService.NO_PATCH_PENALTY
            }
        
        # 8. Compensating controls (-10 if mitigated)
        if asset_vulnerability.mitigation_applied or asset.compensating_controls:
            score += ScoringService.COMPENSATING_CONTROLS_PENALTY
            factors["controls"] = {
                "value": True,
                "points": ScoringService.COMPENSATING_CONTROLS_PENALTY,
                "detail": asset_vulnerability.mitigation_details or "Controls in place"
            }
        
        # Additional factors for context (not scoring)
        
        # Days since published (for context, not scoring)
        if vulnerability.published_at:
            days_old = (datetime.now(timezone.utc) - vulnerability.published_at).days
            factors["age_days"] = days_old
        
        # Exploit maturity (for context)
        if vulnerability.exploit_maturity:
            factors["exploit_maturity"] = vulnerability.exploit_maturity
        
        # Execution frequency (for context)
        if asset_vulnerability.execution_frequency:
            factors["execution_frequency"] = asset_vulnerability.execution_frequency
        
        # Clamp score to 0-100 range
        final_score = max(0, min(100, score))
        
        # Store the scoring breakdown
        asset_vulnerability.score_factors = factors
        asset_vulnerability.risk_score = final_score
        
        return final_score
    
    @staticmethod
    def get_risk_level(score: int) -> str:
        """
        Convert numeric score to risk level.
        
        Returns:
            CRITICAL (80+), HIGH (60-79), MEDIUM (40-59), LOW (0-39)
        """
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
    
    @staticmethod
    def get_recommended_action(
        score: int,
        vulnerability: Vulnerability,
        asset: Asset,
        asset_vulnerability: AssetVulnerability
    ) -> str:
        """
        Recommend action based on score and context.
        
        Returns:
            PATCH_IMMEDIATELY, PATCH_STANDARD, MONITOR, ACCEPT_RISK
        """
        # Immediate action triggers
        if (
            score >= 80 or
            vulnerability.kev_listed or
            asset_vulnerability.code_executed or
            (asset.exposure == "INTERNET" and score >= 60)
        ):
            return "PATCH_IMMEDIATELY"
        
        # Standard patching
        elif score >= 40 or vulnerability.exploit_available:
            return "PATCH_STANDARD"
        
        # Monitor for now
        elif score >= 20:
            return "MONITOR"
        
        # Low risk - can accept
        else:
            return "ACCEPT_RISK"
    
    async def bulk_score_vulnerabilities(
        self,
        asset_vulnerabilities: list[AssetVulnerability],
        recalculate: bool = False
    ) -> Dict[str, Any]:
        """
        Score multiple vulnerabilities efficiently.
        
        Used during scanning or when refreshing scores.
        
        Args:
            asset_vulnerabilities: List of asset-vulnerability pairs
            recalculate: Force recalculation even if score exists
            
        Returns:
            Summary of scoring results
        """
        scored_count = 0
        score_distribution = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        
        for av in asset_vulnerabilities:
            # Skip if already scored and not forcing recalculation
            if av.risk_score is not None and not recalculate:
                continue
            
            # Calculate score
            score = self.calculate_score(
                vulnerability=av.vulnerability,
                asset=av.asset,
                asset_vulnerability=av
            )
            
            # Update distribution
            risk_level = self.get_risk_level(score)
            score_distribution[risk_level] += 1
            
            # Set recommended action
            av.recommended_action = self.get_recommended_action(
                score, av.vulnerability, av.asset, av
            )
            
            scored_count += 1
        
        return {
            "scored_count": scored_count,
            "distribution": score_distribution,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Create a singleton instance
scoring_service = ScoringService()