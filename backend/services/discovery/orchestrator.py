"""
Discovery orchestrator - coordinates multiple scanners.

Manages parallel scanning, deduplication, and database persistence.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.services.discovery.base import BaseScanner, ScanResult, DiscoveredAsset
from backend.models.asset import Asset
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    """
    Coordinates asset discovery across multiple scanners.
    
    Handles:
    - Parallel scanner execution
    - Asset deduplication
    - Database persistence
    - Progress tracking
    """
    
    def __init__(self, tenant_id: UUID):
        """
        Initialize orchestrator for a specific tenant.
        
        Args:
            tenant_id: UUID of the tenant to discover assets for
        """
        self.tenant_id = tenant_id
        self.scanners: List[BaseScanner] = []
    
    def register_scanner(self, scanner: BaseScanner):
        """
        Register a scanner for discovery.
        
        Args:
            scanner: Scanner instance to register
        """
        self.scanners.append(scanner)
    
    async def discover_all(
        self,
        db: AsyncSession,
        parallel: bool = True,
        update_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Run all registered scanners and persist results.
        
        Args:
            db: Database session
            parallel: Run scanners in parallel (faster but more resource intensive)
            update_existing: Update existing assets if found
            
        Returns:
            Summary of discovery operation
        """
        start_time = datetime.utcnow()
        
        # Run scanners
        if parallel:
            scan_results = await self._run_parallel(self.scanners)
        else:
            scan_results = await self._run_sequential(self.scanners)
        
        # Aggregate all discovered assets
        all_assets = []
        for result in scan_results:
            all_assets.extend(result.assets)
        
        # Deduplicate assets
        deduplicated = self._deduplicate_assets(all_assets)
        
        # Persist to database
        persist_result = await self._persist_assets(
            db,
            deduplicated,
            update_existing=update_existing
        )
        
        # Calculate summary
        total_errors = sum(len(result.errors) for result in scan_results)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        summary = {
            "status": "completed",
            "duration_seconds": duration,
            "scanners_executed": len(scan_results),
            "assets_discovered": len(all_assets),
            "assets_after_deduplication": len(deduplicated),
            "assets_created": persist_result["created"],
            "assets_updated": persist_result["updated"],
            "total_errors": total_errors,
            "scanner_results": [
                {
                    "scanner": result.scanner_name,
                    "assets": result.asset_count,
                    "duration": result.scan_duration_seconds,
                    "errors": len(result.errors)
                }
                for result in scan_results
            ]
        }
        
        logger.info(
            f"Discovery completed for tenant {self.tenant_id}: "
            f"{persist_result['created']} created, {persist_result['updated']} updated"
        )
        
        return summary
    
    async def _run_parallel(self, scanners: List[BaseScanner]) -> List[ScanResult]:
        """Run scanners in parallel."""
        tasks = [scanner.scan() for scanner in scanners]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        scan_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Scanner {scanners[idx].scanner_name} failed: {str(result)}")
                # Create error result
                scan_results.append(ScanResult(
                    scanner_name=scanners[idx].scanner_name,
                    scanner_type=scanners[idx].scanner_type,
                    assets=[],
                    scan_duration_seconds=0,
                    errors=[str(result)]
                ))
            else:
                scan_results.append(result)
        
        return scan_results
    
    async def _run_sequential(self, scanners: List[BaseScanner]) -> List[ScanResult]:
        """Run scanners sequentially."""
        results = []
        for scanner in scanners:
            try:
                result = await scanner.scan()
                results.append(result)
            except Exception as e:
                logger.error(f"Scanner {scanner.scanner_name} failed: {str(e)}")
                results.append(ScanResult(
                    scanner_name=scanner.scanner_name,
                    scanner_type=scanner.scanner_type,
                    assets=[],
                    scan_duration_seconds=0,
                    errors=[str(e)]
                ))
        
        return results
    
    def _deduplicate_assets(self, assets: List[DiscoveredAsset]) -> List[DiscoveredAsset]:
        """
        Deduplicate assets by identifier.
        
        When duplicates exist, prefer:
        1. Asset with more vulnerabilities
        2. Asset with more metadata
        3. Most recently scanned
        
        Args:
            assets: List of discovered assets
            
        Returns:
            Deduplicated list
        """
        asset_map: Dict[str, DiscoveredAsset] = {}
        
        for asset in assets:
            existing = asset_map.get(asset.identifier)
            
            if not existing:
                asset_map[asset.identifier] = asset
            else:
                # Choose the better asset
                if self._compare_assets(asset, existing) > 0:
                    asset_map[asset.identifier] = asset
        
        return list(asset_map.values())
    
    def _compare_assets(self, a: DiscoveredAsset, b: DiscoveredAsset) -> int:
        """
        Compare two assets to determine which is better.
        
        Returns:
            1 if a is better, -1 if b is better, 0 if equal
        """
        # More vulnerabilities is better (more complete scan)
        vuln_diff = len(a.vulnerabilities) - len(b.vulnerabilities)
        if vuln_diff != 0:
            return 1 if vuln_diff > 0 else -1
        
        # More installed packages is better
        pkg_diff = len(a.installed_packages) - len(b.installed_packages)
        if pkg_diff != 0:
            return 1 if pkg_diff > 0 else -1
        
        # More recent scan is better
        if a.last_scanned_at > b.last_scanned_at:
            return 1
        elif a.last_scanned_at < b.last_scanned_at:
            return -1
        
        return 0
    
    async def _persist_assets(
        self,
        db: AsyncSession,
        assets: List[DiscoveredAsset],
        update_existing: bool = True
    ) -> Dict[str, int]:
        """
        Persist assets to database.
        
        Args:
            db: Database session
            assets: Assets to persist
            update_existing: Update if asset already exists
            
        Returns:
            Dict with created and updated counts
        """
        created = 0
        updated = 0
        
        for discovered in assets:
            # Check if asset exists
            query = select(Asset).where(
                and_(
                    Asset.tenant_id == self.tenant_id,
                    Asset.identifier == discovered.identifier
                )
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                if update_existing:
                    # Update existing asset
                    asset_dict = discovered.to_dict()
                    for key, value in asset_dict.items():
                        if hasattr(existing, key) and value is not None:
                            setattr(existing, key, value)
                    
                    existing.updated_at = datetime.utcnow()
                    updated += 1
            else:
                # Create new asset
                asset_dict = discovered.to_dict()
                asset = Asset(
                    tenant_id=self.tenant_id,
                    **asset_dict
                )
                db.add(asset)
                created += 1
        
        # Commit all changes
        await db.commit()
        
        return {
            "created": created,
            "updated": updated
        }


class DiscoveryScheduler:
    """
    Schedule periodic discovery scans.
    
    Future: Integrate with cron jobs or background task queue.
    """
    
    def __init__(self):
        self.scheduled_scans: Dict[UUID, Dict[str, Any]] = {}
    
    def schedule_discovery(
        self,
        tenant_id: UUID,
        scanners: List[BaseScanner],
        interval_hours: int = 24
    ):
        """
        Schedule periodic discovery for a tenant.
        
        Args:
            tenant_id: Tenant to scan
            scanners: Scanners to run
            interval_hours: How often to run (default 24h)
        """
        self.scheduled_scans[tenant_id] = {
            "scanners": scanners,
            "interval_hours": interval_hours,
            "last_run": None,
            "next_run": None
        }
        
        logger.info(f"Scheduled discovery for tenant {tenant_id} every {interval_hours}h")
    
    async def run_scheduled_scans(self, db: AsyncSession):
        """
        Execute all scheduled scans that are due.
        
        Args:
            db: Database session
        """
        now = datetime.utcnow()
        
        for tenant_id, config in self.scheduled_scans.items():
            next_run = config.get("next_run")
            
            if next_run is None or now >= next_run:
                # Run discovery
                orchestrator = DiscoveryOrchestrator(tenant_id)
                for scanner in config["scanners"]:
                    orchestrator.register_scanner(scanner)
                
                try:
                    summary = await orchestrator.discover_all(db)
                    logger.info(f"Scheduled scan for {tenant_id}: {summary}")
                    
                    # Update schedule
                    config["last_run"] = now
                    config["next_run"] = now + timedelta(hours=config["interval_hours"])
                
                except Exception as e:
                    logger.error(f"Scheduled scan failed for {tenant_id}: {str(e)}")
