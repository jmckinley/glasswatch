"""
Database base class and metadata.

Import all models here to ensure they're registered with SQLAlchemy.
"""
from sqlalchemy.orm import declarative_base

# Create base class for models
Base = declarative_base()

# Import all models to register them
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.goal import Goal, EnhancedGoal
from backend.models.patch_bundle import PatchBundle, BundlePatch
from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.maintenance_window import MaintenanceWindow
from backend.models.comment import Comment, Reaction
from backend.models.activity import Activity
from backend.models.approval import ApprovalRequest, ApprovalAction, ApprovalPolicy

# This ensures all models are available when creating/migrating database
__all__ = [
    "Base",
    "Tenant",
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
    "Comment",
    "Reaction",
    "Activity",
    "ApprovalRequest",
    "ApprovalAction",
    "ApprovalPolicy",
]