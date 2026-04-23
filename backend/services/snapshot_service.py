"""
Snapshot and rollback service for patch state management.

Captures system state, enables rollback, and provides snapshot comparison.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
import random

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.snapshot import (
    PatchSnapshot, RollbackRecord, SnapshotType, RollbackStatus
)
from backend.models.asset import Asset
from backend.models.bundle import Bundle


class SnapshotService:
    """
    Service for capturing and managing system snapshots.
    
    Simulates snapshot capture for now - in production, this would
    integrate with agents running on target systems.
    """
    
    # Sample data for realistic snapshots
    SAMPLE_PACKAGES = [
        ("openssl", "1.1.1k-1ubuntu1.9", "amd64"),
        ("libssl1.1", "1.1.1k-1ubuntu1.9", "amd64"),
        ("nginx", "1.18.0-6ubuntu14", "amd64"),
        ("postgresql-14", "14.9-0ubuntu0.22.04.1", "amd64"),
        ("redis-server", "6.0.16-1ubuntu1", "amd64"),
        ("python3", "3.10.12-1~22.04", "amd64"),
        ("systemd", "249.11-0ubuntu3.11", "amd64"),
        ("openssh-server", "1:8.9p1-3ubuntu0.4", "amd64"),
    ]
    
    SAMPLE_SERVICES = [
        ("nginx", "running", True),
        ("postgresql", "running", True),
        ("redis-server", "running", True),
        ("ssh", "running", True),
        ("cron", "running", True),
    ]
    
    SAMPLE_CONFIGS = {
        "/etc/nginx/nginx.conf": "sha256:a1b2c3d4e5f6",
        "/etc/postgresql/14/main/postgresql.conf": "sha256:1a2b3c4d5e6f",
        "/etc/ssh/sshd_config": "sha256:9f8e7d6c5b4a",
        "/etc/systemd/system.conf": "sha256:abcdef123456",
    }
    
    async def capture_snapshot(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        asset_id: UUID,
        tenant_id: UUID,
        snapshot_type: SnapshotType
    ) -> PatchSnapshot:
        """
        Capture a system snapshot.
        
        In production, this would communicate with agents on target systems.
        For now, generates realistic simulated data.
        """
        # Fetch asset info for metadata
        asset_result = await db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Generate system state
        system_state = {
            "packages": [
                {
                    "name": name,
                    "version": version,
                    "architecture": arch
                }
                for name, version, arch in self.SAMPLE_PACKAGES
            ],
            "configs": self.SAMPLE_CONFIGS.copy(),
            "services": [
                {
                    "name": name,
                    "state": state,
                    "enabled": enabled
                }
                for name, state, enabled in self.SAMPLE_SERVICES
            ],
            "kernel": "5.15.0-91-generic"
        }
        
        # Generate metadata
        metadata = {
            "capture_method": "apt-history",
            "duration_ms": random.randint(500, 2000),
            "agent_version": "1.0.0",
            "hostname": asset.identifier,
            "os_info": asset.os_version or "Ubuntu 22.04.3 LTS"
        }
        
        # Calculate checksum and size
        checksum = PatchSnapshot.calculate_checksum(system_state)
        import json
        size_bytes = len(json.dumps(system_state).encode())
        
        # Create snapshot
        snapshot = PatchSnapshot(
            bundle_id=bundle_id,
            asset_id=asset_id,
            tenant_id=tenant_id,
            snapshot_type=snapshot_type,
            system_state=system_state,
            snapshot_metadata=metadata,
            checksum=checksum,
            size_bytes=size_bytes
        )
        
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        
        return snapshot
    
    async def compare_snapshots(
        self,
        db: AsyncSession,
        pre_id: UUID,
        post_id: UUID
    ) -> Dict[str, Any]:
        """
        Compare two snapshots and return differences.
        
        Useful for understanding what changed during patching.
        """
        # Fetch both snapshots
        pre_result = await db.execute(
            select(PatchSnapshot).where(PatchSnapshot.id == pre_id)
        )
        pre = pre_result.scalar_one_or_none()
        
        post_result = await db.execute(
            select(PatchSnapshot).where(PatchSnapshot.id == post_id)
        )
        post = post_result.scalar_one_or_none()
        
        if not pre or not post:
            raise ValueError("One or both snapshots not found")
        
        # Compare packages
        pre_packages = {p["name"]: p["version"] for p in pre.system_state.get("packages", [])}
        post_packages = {p["name"]: p["version"] for p in post.system_state.get("packages", [])}
        
        package_changes = []
        for name in set(pre_packages.keys()) | set(post_packages.keys()):
            pre_ver = pre_packages.get(name)
            post_ver = post_packages.get(name)
            if pre_ver != post_ver:
                package_changes.append({
                    "package": name,
                    "before": pre_ver,
                    "after": post_ver,
                    "change_type": "added" if not pre_ver else "removed" if not post_ver else "updated"
                })
        
        # Compare configs
        pre_configs = pre.system_state.get("configs", {})
        post_configs = post.system_state.get("configs", {})
        
        config_changes = []
        for path in set(pre_configs.keys()) | set(post_configs.keys()):
            pre_hash = pre_configs.get(path)
            post_hash = post_configs.get(path)
            if pre_hash != post_hash:
                config_changes.append({
                    "path": path,
                    "before_hash": pre_hash,
                    "after_hash": post_hash,
                    "change_type": "added" if not pre_hash else "removed" if not post_hash else "modified"
                })
        
        # Compare services
        pre_services = {s["name"]: s for s in pre.system_state.get("services", [])}
        post_services = {s["name"]: s for s in post.system_state.get("services", [])}
        
        service_changes = []
        for name in set(pre_services.keys()) | set(post_services.keys()):
            pre_svc = pre_services.get(name, {})
            post_svc = post_services.get(name, {})
            if pre_svc != post_svc:
                service_changes.append({
                    "service": name,
                    "before_state": pre_svc.get("state"),
                    "after_state": post_svc.get("state"),
                    "state_changed": pre_svc.get("state") != post_svc.get("state")
                })
        
        return {
            "pre_snapshot_id": str(pre_id),
            "post_snapshot_id": str(post_id),
            "comparison_time": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "packages_changed": len(package_changes),
                "configs_changed": len(config_changes),
                "services_changed": len(service_changes),
                "kernel_changed": pre.system_state.get("kernel") != post.system_state.get("kernel")
            },
            "details": {
                "packages": package_changes,
                "configs": config_changes,
                "services": service_changes,
                "kernel": {
                    "before": pre.system_state.get("kernel"),
                    "after": post.system_state.get("kernel")
                }
            }
        }
    
    async def initiate_rollback(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        asset_id: UUID,
        tenant_id: UUID,
        trigger: str,
        reason: str
    ) -> RollbackRecord:
        """
        Initiate a rollback operation.
        
        Finds the pre-patch snapshot and starts rollback process.
        """
        # Find the pre-patch snapshot for this bundle/asset
        snapshot_result = await db.execute(
            select(PatchSnapshot).where(
                and_(
                    PatchSnapshot.bundle_id == bundle_id,
                    PatchSnapshot.asset_id == asset_id,
                    PatchSnapshot.tenant_id == tenant_id,
                    PatchSnapshot.snapshot_type == SnapshotType.PRE_PATCH
                )
            ).order_by(PatchSnapshot.created_at.desc())
        )
        snapshot = snapshot_result.scalar_one_or_none()
        
        if not snapshot:
            raise ValueError(f"No pre-patch snapshot found for bundle {bundle_id}, asset {asset_id}")
        
        # Create rollback record
        rollback = RollbackRecord(
            bundle_id=bundle_id,
            asset_id=asset_id,
            tenant_id=tenant_id,
            snapshot_id=snapshot.id,
            trigger=trigger,
            reason=reason,
            status=RollbackStatus.PENDING
        )
        
        db.add(rollback)
        await db.commit()
        await db.refresh(rollback)
        
        return rollback
    
    async def execute_rollback(
        self,
        db: AsyncSession,
        rollback_id: UUID
    ) -> RollbackRecord:
        """
        Execute a rollback operation.
        
        In production, this would communicate with agents to revert changes.
        For now, simulates the rollback process.
        """
        # Fetch rollback record
        result = await db.execute(
            select(RollbackRecord).where(RollbackRecord.id == rollback_id)
        )
        rollback = result.scalar_one_or_none()
        
        if not rollback:
            raise ValueError(f"Rollback {rollback_id} not found")
        
        if rollback.status != RollbackStatus.PENDING:
            raise ValueError(f"Rollback {rollback_id} is not in PENDING state")
        
        # Update status to IN_PROGRESS
        rollback.status = RollbackStatus.IN_PROGRESS
        await db.commit()
        
        try:
            # Fetch the snapshot
            snapshot_result = await db.execute(
                select(PatchSnapshot).where(PatchSnapshot.id == rollback.snapshot_id)
            )
            snapshot = snapshot_result.scalar_one()
            
            # Simulate rollback execution
            packages = snapshot.system_state.get("packages", [])
            configs = list(snapshot.system_state.get("configs", {}).keys())
            services = [s["name"] for s in snapshot.system_state.get("services", [])]
            
            rollback_details = {
                "packages_reverted": [p["name"] for p in packages[:3]],  # Simulate partial list
                "configs_restored": configs[:2],
                "services_restarted": services[:2],
                "actions_taken": [
                    f"apt-get install {packages[0]['name']}={packages[0]['version']}" if packages else "none"
                ],
                "verification_status": "success"
            }
            
            # Update rollback record
            rollback.status = RollbackStatus.COMPLETED
            rollback.completed_at = datetime.now(timezone.utc)
            rollback.rollback_details = rollback_details
            
        except Exception as e:
            # Handle failure
            rollback.status = RollbackStatus.FAILED
            rollback.completed_at = datetime.now(timezone.utc)
            rollback.error_message = str(e)
        
        await db.commit()
        await db.refresh(rollback)
        
        return rollback
    
    async def get_snapshot_history(
        self,
        db: AsyncSession,
        asset_id: UUID,
        tenant_id: UUID,
        limit: int = 50
    ) -> List[PatchSnapshot]:
        """
        Get snapshot history for an asset.
        """
        result = await db.execute(
            select(PatchSnapshot)
            .where(
                and_(
                    PatchSnapshot.asset_id == asset_id,
                    PatchSnapshot.tenant_id == tenant_id
                )
            )
            .order_by(PatchSnapshot.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def validate_snapshot_integrity(
        self,
        db: AsyncSession,
        snapshot_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate snapshot integrity by checking checksum.
        """
        result = await db.execute(
            select(PatchSnapshot).where(PatchSnapshot.id == snapshot_id)
        )
        snapshot = result.scalar_one_or_none()
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        is_valid = snapshot.validate_integrity()
        
        return {
            "snapshot_id": str(snapshot_id),
            "valid": is_valid,
            "stored_checksum": snapshot.checksum,
            "calculated_checksum": PatchSnapshot.calculate_checksum(snapshot.system_state),
            "validated_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
snapshot_service = SnapshotService()
