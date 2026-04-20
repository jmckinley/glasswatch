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
        item = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="openssl",
            current_version="1.1.1k",
            target_version="1.1.1l"
        )
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
        assert simulation.affected_services is not None
        assert simulation.estimated_downtime is not None
        assert simulation.blast_radius is not None
    
    async def test_risk_score_range(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test that risk score is within 0-100 range"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))
        
        item = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="nginx",
            current_version="1.18.0",
            target_version="1.18.1"
        )
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
            
            item = BundleItem(
                id=uuid4(),
                bundle_id=bundle.id,
                asset_id=asset.id,
                tenant_id=test_tenant.id,
                patch_name=f"package-{i}",
                current_version="1.0.0",
                target_version="1.1.0"
            )
            test_session.add(item)
        
        await test_session.flush()
        
        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )
        
        # Blast radius should reflect multiple assets
        assert simulation.blast_radius >= 5
    
    async def test_dependency_conflict_detection(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test detection of potential dependency conflicts"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))
        
        # Add items that might conflict (same asset, different packages)
        item1 = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="openssl",
            current_version="1.1.1k",
            target_version="3.0.0"  # Major version jump
        )
        item2 = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="libssl",
            current_version="1.1.1k",
            target_version="1.1.1l"
        )
        test_session.add_all([item1, item2])
        await test_session.flush()
        
        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )
        
        # Should identify potential conflicts
        assert simulation.impact_details is not None
    
    async def test_downtime_estimation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test downtime estimation scales with bundle size"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Small bundle
        asset = await create_test_asset(tenant_id=str(test_tenant.id))
        item = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="vim",
            current_version="8.0",
            target_version="8.1"
        )
        test_session.add(item)
        await test_session.flush()
        
        simulation = await service.predict_impact(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )
        
        # Should have reasonable downtime estimate
        assert simulation.estimated_downtime > 0
        assert simulation.estimated_downtime < 1000  # Less than 1000 minutes for small bundle
    
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
        item1 = BundleItem(
            id=uuid4(),
            bundle_id=small_bundle.id,
            asset_id=asset1.id,
            tenant_id=test_tenant.id,
            patch_name="vim",
            current_version="8.0",
            target_version="8.1"
        )
        test_session.add(item1)
        
        # Large bundle - 10 items
        for i in range(10):
            asset = await create_test_asset(
                tenant_id=str(test_tenant.id),
                hostname=f"large-server-{i}"
            )
            item = BundleItem(
                id=uuid4(),
                bundle_id=large_bundle.id,
                asset_id=asset.id,
                tenant_id=test_tenant.id,
                patch_name=f"package-{i}",
                current_version="1.0.0",
                target_version="1.1.0"
            )
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
        assert large_sim.estimated_downtime > small_sim.estimated_downtime
    
    async def test_dry_run_validation(
        self, test_session, test_tenant, create_test_bundle, create_test_asset
    ):
        """Test dry-run validation detects issues"""
        service = SimulatorService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        asset = await create_test_asset(tenant_id=str(test_tenant.id))
        
        item = BundleItem(
            id=uuid4(),
            bundle_id=bundle.id,
            asset_id=asset.id,
            tenant_id=test_tenant.id,
            patch_name="kernel",
            current_version="5.15.0",
            target_version="6.0.0"
        )
        test_session.add(item)
        await test_session.flush()
        
        # Run dry-run
        dry_run = await service.dry_run(
            db=test_session,
            bundle_id=bundle.id,
            tenant_id=test_tenant.id
        )
        
        assert dry_run is not None
        assert dry_run.validation_passed is not None
        assert dry_run.validation_warnings is not None
    
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
        item1 = BundleItem(
            id=uuid4(),
            bundle_id=low_bundle.id,
            asset_id=low_asset.id,
            tenant_id=test_tenant.id,
            patch_name="vim",
            current_version="8.0",
            target_version="8.1"
        )
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
        item2 = BundleItem(
            id=uuid4(),
            bundle_id=high_bundle.id,
            asset_id=high_asset.id,
            tenant_id=test_tenant.id,
            patch_name="nginx",
            current_version="1.18.0",
            target_version="1.18.1"
        )
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
