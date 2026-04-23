"""
Unit tests for the patch simulation service.

Tests impact prediction, risk scoring, blast radius calculation,
dependency detection, downtime estimation, and dry-run validation.
"""
import pytest
from uuid import uuid4

from backend.services.simulator_service import SimulatorService
from backend.models.bundle_item import BundleItem


pytestmark = pytest.mark.asyncio


def make_bundle_item(bundle_id, asset_id, patch_identifier="openssl", risk_score=50.0):
    """Create a BundleItem with correct model fields."""
    return BundleItem(
        id=uuid4(),
        bundle_id=bundle_id,
        asset_id=asset_id,
        # vulnerability_id is required; using random UUID (SQLite doesn't enforce FK)
        vulnerability_id=uuid4(),
        patch_identifier=patch_identifier,
        risk_score=risk_score,
    )


class TestSimulatorService:
    """Test suite for SimulatorService"""

    async def test_impact_prediction_output_structure(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that predict_impact returns properly structured output"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        # Add bundle item
        item = make_bundle_item(bundle.id, asset.id, patch_identifier="openssl")
        test_session.add(item)
        await test_session.flush()

        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        assert simulation is not None
        assert simulation.bundle_id == bundle.id
        assert simulation.risk_score is not None
        assert simulation.impact_summary is not None
        assert "affected_services" in simulation.impact_summary
        assert "estimated_downtime_minutes" in simulation.impact_summary
        assert "blast_radius" in simulation.impact_summary

    async def test_risk_score_range(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that risk score is within 0-100 range"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        item = make_bundle_item(bundle.id, asset.id, patch_identifier="nginx")
        test_session.add(item)
        await test_session.flush()

        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        assert 0 <= simulation.risk_score <= 100

    async def test_blast_radius_calculation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test blast radius calculation based on affected assets"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))

        # Create multiple assets
        assets = []
        for i in range(5):
            asset = await create_test_asset(
                tenant_id=str(test_tenant.id),
                hostname=f"server-{i}",
                criticality=3
            )
            assets.append(asset)

            item = make_bundle_item(bundle.id, asset.id, patch_identifier=f"package-{i}")
            test_session.add(item)

        await test_session.flush()

        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        # Blast radius is a dict {"direct": N, "indirect": M}
        blast = simulation.impact_summary["blast_radius"]
        assert blast["direct"] >= 5

    async def test_dependency_conflict_detection(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test detection of potential dependency conflicts (impact_details in summary)"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        # Add items that might conflict (same asset, different packages)
        item1 = make_bundle_item(bundle.id, asset.id, patch_identifier="openssl")
        item2 = make_bundle_item(bundle.id, asset.id, patch_identifier="libssl")
        test_session.add_all([item1, item2])
        await test_session.flush()

        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        # impact_summary should exist with structured output
        assert simulation.impact_summary is not None
        assert "dependency_conflicts" in simulation.impact_summary

    async def test_downtime_estimation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test downtime estimation is positive"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))

        # Small bundle
        asset = await create_test_asset(tenant_id=str(test_tenant.id))
        item = make_bundle_item(bundle.id, asset.id, patch_identifier="vim")
        test_session.add(item)
        await test_session.flush()

        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        downtime = simulation.impact_summary["estimated_downtime_minutes"]
        # Should have reasonable downtime estimate
        assert downtime > 0
        assert downtime < 1000  # Less than 1000 minutes for small bundle

    async def test_downtime_scales_with_size(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that larger bundles have longer estimated downtime"""
        service = SimulatorService()
        small_bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Small"
        )
        large_bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Large"
        )

        # Small bundle - 1 item
        asset1 = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="small-server"
        )
        item1 = make_bundle_item(small_bundle.id, asset1.id, patch_identifier="vim")
        test_session.add(item1)

        # Large bundle - 10 items
        for i in range(10):
            asset = await create_test_asset(
                tenant_id=str(test_tenant.id),
                hostname=f"large-server-{i}"
            )
            item = make_bundle_item(large_bundle.id, asset.id, patch_identifier=f"package-{i}")
            test_session.add(item)

        await test_session.flush()

        small_sim = await service.predict_impact(
            db=test_session,
            bundle_id=small_bundle.id,
            tenant_id=test_tenant.id
        )
        large_sim = await service.predict_impact(
            db=test_session,
            bundle_id=large_bundle.id,
            tenant_id=test_tenant.id
        )

        # Larger bundle should have more downtime
        small_dt = small_sim.impact_summary["estimated_downtime_minutes"]
        large_dt = large_sim.impact_summary["estimated_downtime_minutes"]
        assert large_dt > small_dt

    async def test_dry_run_validation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test dry-run validation (run_dry_run method)"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))

        item = make_bundle_item(bundle.id, asset.id, patch_identifier="kernel")
        test_session.add(item)
        await test_session.flush()

        # Run dry-run (method is called run_dry_run)
        dry_run = await service.run_dry_run(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )

        assert dry_run is not None
        assert dry_run.dry_run_results is not None
        assert "validation" in dry_run.dry_run_results
        assert "preflight_checks" in dry_run.dry_run_results

    async def test_high_criticality_increases_risk(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that high criticality assets increase risk score"""
        service = SimulatorService()

        # Low criticality bundle
        low_bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="Low Crit"
        )
        low_asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="low-crit",
            criticality=1
        )
        item1 = make_bundle_item(low_bundle.id, low_asset.id, patch_identifier="vim", risk_score=10.0)
        test_session.add(item1)

        # High criticality bundle
        high_bundle = await create_test_bundle(
            tenant_id=str(test_tenant.id),
            name="High Crit"
        )
        high_asset = await create_test_asset(
            tenant_id=str(test_tenant.id),
            hostname="high-crit",
            criticality=5,
            is_internet_facing=True
        )
        item2 = make_bundle_item(high_bundle.id, high_asset.id, patch_identifier="nginx", risk_score=90.0)
        test_session.add(item2)

        await test_session.flush()

        low_sim = await service.predict_impact(
            db=test_session,
            bundle_id=low_bundle.id,
            tenant_id=test_tenant.id
        )
        high_sim = await service.predict_impact(
            db=test_session,
            bundle_id=high_bundle.id,
            tenant_id=test_tenant.id
        )

        # High criticality should have higher risk
        assert high_sim.risk_score > low_sim.risk_score
