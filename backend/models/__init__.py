"""
Database models for Glasswatch.

These models represent the core entities in our system:
- Tenant: Multi-tenant isolation
- Vulnerability: Security vulnerabilities from various sources
- Asset: Infrastructure components that may be vulnerable
- AssetVulnerability: The junction between assets and their vulnerabilities
- Goal: User-defined objectives for patching
- EnhancedGoal: Advanced goal settings with business context
- PatchBundle: Collections of patches scheduled together
- BundlePatch: Individual patches within a bundle

The relationships enable our unique goal-based optimization approach.
"""

from backend.models.tenant import Tenant
from backend.models.user import User, UserRole
from backend.models.audit_log import AuditLog
from backend.models.approval import ApprovalAction, ApprovalStatus
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.goal import Goal, EnhancedGoal
from backend.models.patch_bundle import PatchBundle, BundlePatch
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.maintenance_window import MaintenanceWindow

# Export all models
__all__ = [
    "Tenant",
    "User",
    "UserRole",
    "AuditLog",
    "ApprovalAction",
    "ApprovalStatus",
    "Vulnerability", 
    "Asset",
    "AssetVulnerability",
    "Goal",
    "EnhancedGoal",
    "PatchBundle",
    "BundlePatch",
    "Bundle",
    "BundleItem",
    "MaintenanceWindow",
]