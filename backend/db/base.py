"""
Import all models so Alembic can detect them.

This ensures all models are loaded when generating migrations.
"""
# Import the base class
from backend.db.base_class import Base

# Import all models to ensure they're registered with SQLAlchemy
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.goal import Goal, EnhancedGoal
from backend.models.patch_bundle import PatchBundle, BundlePatch

# Make Base available for Alembic
__all__ = ["Base"]