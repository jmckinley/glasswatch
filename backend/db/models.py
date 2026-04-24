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
from backend.models.snapshot import PatchSnapshot, RollbackRecord  # noqa: F401
from backend.models.simulation import PatchSimulation  # noqa: F401
from backend.models.connection import Connection  # noqa: F401
from backend.models.tag import Tag  # noqa: F401
from backend.models.rule import DeploymentRule  # noqa: F401
from backend.models.discovery_scan import DiscoveryScan  # noqa: F401
from backend.models.invite import Invite  # noqa: F401
