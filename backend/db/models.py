"""
Import all models to register them with SQLAlchemy.

Import this module when you need all models discovered
(e.g., Alembic migrations, create_all).
"""
# noqa: F401 — side-effect imports to register models on Base.metadata
from backend.models.tenant import Tenant  # noqa: F401
from backend.models.user import User  # noqa: F401
from backend.models.audit_log import AuditLog  # noqa: F401
from backend.models.vulnerability import Vulnerability  # noqa: F401
from backend.models.asset import Asset  # noqa: F401
from backend.models.asset_vulnerability import AssetVulnerability  # noqa: F401
from backend.models.goal import Goal, EnhancedGoal  # noqa: F401
from backend.models.patch_bundle import PatchBundle, BundlePatch  # noqa: F401
from backend.models.bundle import Bundle  # noqa: F401
from backend.models.bundle_item import BundleItem  # noqa: F401
from backend.models.maintenance_window import MaintenanceWindow  # noqa: F401
from backend.models.comment import Comment, Reaction  # noqa: F401
from backend.models.activity import Activity  # noqa: F401
from backend.models.approval import ApprovalRequest, ApprovalAction, ApprovalPolicy  # noqa: F401
