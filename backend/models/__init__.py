"""
Database models for Glasswatch.

Import all models here so SQLAlchemy can resolve relationship string references
(e.g. relationship("Asset")) regardless of which model is imported first.
"""
# Import all models to register them with SQLAlchemy's mapper registry
# Order matters: base models before dependent ones
from backend.models.tenant import Tenant  # noqa: F401
from backend.models.user import User  # noqa: F401
from backend.models.asset import Asset  # noqa: F401
from backend.models.vulnerability import Vulnerability  # noqa: F401
from backend.models.goal import Goal  # noqa: F401
from backend.models.bundle import Bundle  # noqa: F401
from backend.models.maintenance_window import MaintenanceWindow  # noqa: F401
from backend.models.connection import Connection  # noqa: F401
from backend.models.tag import Tag  # noqa: F401
from backend.models.rule import DeploymentRule  # noqa: F401
from backend.models.audit_log import AuditLog  # noqa: F401
from backend.models.notification import Notification  # noqa: F401
from backend.models.activity import Activity
from backend.models.asset_vulnerability import AssetVulnerability  # noqa: F401
from backend.models.approval import ApprovalRequest, ApprovalAction  # noqa: F401
from backend.models.comment import Comment
from backend.models.bundle_item import BundleItem
from backend.models.patch_bundle import PatchBundle
from backend.models.simulation import PatchSimulation
from backend.models.snapshot import PatchSnapshot
from backend.models.invite import Invite  # noqa: F401
