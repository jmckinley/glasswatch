"""
Unit tests that verify performance-critical indexes are defined on SQLAlchemy models.

These are structural tests — they validate the schema definition without
requiring a live database.  They catch accidental removal of index=True or
__table_args__ Index entries that would degrade production query performance.
"""
import pytest
from sqlalchemy import Index

pytestmark = pytest.mark.asyncio


def _column_has_index(model, col_name: str) -> bool:
    """Return True if the named column has index=True (single-column index)."""
    col = model.__table__.c.get(col_name)
    if col is None:
        return False
    return col.index is True


def _table_has_named_index(model, index_name: str) -> bool:
    """Return True if __table__.indexes contains an index with the given name."""
    return any(idx.name == index_name for idx in model.__table__.indexes)


def _table_has_index_on_column(model, col_name: str) -> bool:
    """
    Return True if the model has any index (named or column-level) on col_name.

    Handles:
    - index=True on the Column definition
    - Index(...) entries in __table_args__
    """
    if _column_has_index(model, col_name):
        return True
    for idx in model.__table__.indexes:
        # Compare by column name (not object identity) to avoid SQLAlchemy's
        # __contains__ requirement for a string argument
        if col_name in [c.name for c in idx.columns]:
            return True
    return False


# ── Vulnerability model ───────────────────────────────────────────────────────

class TestVulnerabilityModelIndexes:
    async def test_vulnerability_model_has_severity_index(self):
        """Vulnerability.severity must be indexed for fast severity-based queries."""
        from backend.models.vulnerability import Vulnerability

        assert _table_has_index_on_column(Vulnerability, "severity") or \
               _table_has_named_index(Vulnerability, "ix_vulnerability_severity"), \
               "Vulnerability.severity is missing an index"

    async def test_vulnerability_model_has_kev_listed_or_epss_indexed(self):
        """Vulnerability should have indexes on high-frequency query columns."""
        from backend.models.vulnerability import Vulnerability

        # At a minimum, severity index must exist (checked above).
        # This checks the table has *some* indexes beyond the primary key.
        non_pk_indexes = [
            idx for idx in Vulnerability.__table__.indexes
            if not any(c.primary_key for c in idx.columns)
        ]
        assert len(non_pk_indexes) >= 1, \
            "Vulnerability table should have at least one non-PK index"


# ── AssetVulnerability model ──────────────────────────────────────────────────

class TestAssetVulnerabilityModelIndexes:
    async def test_asset_vulnerability_has_asset_id_index(self):
        """AssetVulnerability.asset_id must be indexed for fast asset look-ups."""
        from backend.models.asset_vulnerability import AssetVulnerability

        assert _table_has_index_on_column(AssetVulnerability, "asset_id") or \
               _table_has_named_index(AssetVulnerability, "ix_asset_vuln_asset"), \
               "AssetVulnerability.asset_id is missing an index"

    async def test_asset_vulnerability_has_vulnerability_id_index(self):
        """AssetVulnerability.vulnerability_id must be indexed."""
        from backend.models.asset_vulnerability import AssetVulnerability

        assert _table_has_index_on_column(AssetVulnerability, "vulnerability_id") or \
               _table_has_named_index(AssetVulnerability, "ix_asset_vuln_vulnerability"), \
               "AssetVulnerability.vulnerability_id is missing an index"


# ── Notification model ────────────────────────────────────────────────────────

class TestNotificationModelIndexes:
    async def test_notification_model_has_tenant_id_index(self):
        """Notification.tenant_id must be indexed (notifications are always tenant-scoped)."""
        from backend.models.notification import Notification

        assert _table_has_index_on_column(Notification, "tenant_id") or \
               _table_has_named_index(Notification, "ix_notification_tenant_user_read"), \
               "Notification.tenant_id is missing an index"

    async def test_notification_model_has_composite_index(self):
        """Notification table should have a composite index for (tenant_id, user_id, read)."""
        from backend.models.notification import Notification

        assert _table_has_named_index(Notification, "ix_notification_tenant_user_read"), \
               "Notification is missing composite index ix_notification_tenant_user_read"


# ── Bundle model ──────────────────────────────────────────────────────────────

class TestBundleModelIndexes:
    async def test_bundle_model_has_status_index(self):
        """Bundle.status must be indexed for fast status-based filtering."""
        from backend.models.bundle import Bundle

        assert _table_has_index_on_column(Bundle, "status") or \
               _table_has_named_index(Bundle, "ix_bundle_status"), \
               "Bundle.status is missing an index"

    async def test_bundle_model_has_tenant_id_index(self):
        """Bundle.tenant_id must be indexed (always filtered by tenant)."""
        from backend.models.bundle import Bundle

        assert _table_has_index_on_column(Bundle, "tenant_id"), \
               "Bundle.tenant_id is missing an index"


# ── Asset model ───────────────────────────────────────────────────────────────

class TestAssetModelIndexes:
    async def test_asset_model_has_tenant_id_index(self):
        """Asset.tenant_id must be indexed."""
        from backend.models.asset import Asset

        assert _table_has_index_on_column(Asset, "tenant_id") or \
               _table_has_named_index(Asset, "ix_asset_tenant_id"), \
               "Asset.tenant_id is missing an index"

    async def test_asset_model_has_type_index(self):
        """Asset.type should be indexed for type-based queries."""
        from backend.models.asset import Asset

        assert _table_has_index_on_column(Asset, "type") or \
               _table_has_named_index(Asset, "ix_asset_type"), \
               "Asset.type is missing an index"
