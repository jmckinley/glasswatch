"""
Unit tests for the snapshot and rollback service.

Tests snapshot capture, comparison, rollback, and integrity validation.
"""
import pytest
from uuid import uuid4

from backend.services.snapshot_service import SnapshotService
from backend.models.snapshot import SnapshotType, RollbackStatus


pytestmark = pytest.mark.asyncio


class TestSnapshotService:
    """Test suite for SnapshotService"""

    async def test_capture_pre_patch_snapshot(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test capturing a pre-patch snapshot"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        assert snapshot is not None
        assert snapshot.bundle_id == bundle.id
        assert snapshot.asset_id == asset.id
        assert snapshot.snapshot_type == SnapshotType.PRE_PATCH
        assert snapshot.system_state is not None
        assert snapshot.checksum is not None

    async def test_capture_post_patch_snapshot(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test capturing a post-patch snapshot"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.POST_PATCH
        )

        assert snapshot is not None
        assert snapshot.snapshot_type == SnapshotType.POST_PATCH

    async def test_snapshot_contains_packages(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that snapshot includes package information"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        assert "packages" in snapshot.system_state
        assert len(snapshot.system_state["packages"]) > 0

        # Check package structure
        pkg = snapshot.system_state["packages"][0]
        assert "name" in pkg
        assert "version" in pkg

    async def test_snapshot_contains_services(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that snapshot includes service information"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        assert "services" in snapshot.system_state
        assert len(snapshot.system_state["services"]) > 0

    async def test_snapshot_comparison_generates_diff(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test comparing pre and post snapshots generates diff"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        # Capture pre-patch snapshot
        pre_snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        # Capture post-patch snapshot
        post_snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.POST_PATCH
        )

        # Compare snapshots (method uses pre_id/post_id kwargs)
        diff = await service.compare_snapshots(
            db=test_session,
            pre_id=pre_snapshot.id,
            post_id=post_snapshot.id
        )

        assert diff is not None
        assert "summary" in diff
        summary = diff["summary"]
        assert "packages_changed" in summary or "services_changed" in summary

    async def test_rollback_initiation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test initiating a rollback"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        # Create a pre-patch snapshot (initiate_rollback finds the pre-patch automatically)
        await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        # Initiate rollback using bundle_id + asset_id (not snapshot_id)
        rollback = await service.initiate_rollback(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            trigger="manual",
            reason="Testing rollback"
        )

        assert rollback is not None
        assert rollback.bundle_id == bundle.id
        assert rollback.asset_id == asset.id
        assert rollback.reason == "Testing rollback"
        # RollbackRecord starts as PENDING
        assert rollback.status == RollbackStatus.PENDING

    async def test_rollback_requires_pre_patch_snapshot(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that rollback requires a pre-patch snapshot to exist"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        # Only create a POST-patch snapshot (no pre-patch)
        await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.POST_PATCH
        )

        # initiate_rollback should fail since no PRE_PATCH snapshot exists
        with pytest.raises(ValueError):
            await service.initiate_rollback(
                db=test_session,
                bundle_id=bundle.id,
                asset_id=asset.id,
                tenant_id=test_tenant.id,
                trigger="manual",
                reason="Invalid rollback"
            )

    async def test_snapshot_integrity_validation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test snapshot checksum integrity validation"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        # Verify integrity using validate_snapshot_integrity (returns dict)
        result = await service.validate_snapshot_integrity(
            db=test_session,
            snapshot_id=snapshot.id
        )

        assert result["valid"] is True

    async def test_snapshot_integrity_detects_corruption(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that integrity check detects corrupted data"""
        service = SnapshotService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        snapshot = await service.capture_snapshot(
            db=test_session,
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            snapshot_type=SnapshotType.PRE_PATCH
        )

        # Corrupt the snapshot data by clearing packages
        snapshot.system_state = {"packages": [], "configs": {}, "services": [], "kernel": "corrupted"}
        await test_session.flush()

        # Verify integrity should fail (checksum won't match)
        result = await service.validate_snapshot_integrity(
            db=test_session,
            snapshot_id=snapshot.id
        )

        assert result["valid"] is False
