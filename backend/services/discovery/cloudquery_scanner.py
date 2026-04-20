"""
CloudQuery scanner integration for unified multi-cloud asset discovery.

CloudQuery provides a unified SQL-based interface to query cloud infrastructure.
Supports AWS, Azure, GCP, Kubernetes, and 100+ data sources.
"""
import asyncio
import json
import tempfile
import os
from typing import Optional, List, Dict, Any
import time

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class CloudQueryScanner(BaseScanner):
    """
    CloudQuery unified cloud asset discovery scanner.
    
    Requires: cloudquery CLI binary
    Discovers: Assets from multiple cloud providers via SQL queries
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CLOUD
        self.scanner_name = "cloudquery"
        self.cloudquery_path = config.get("cloudquery_path", "cloudquery") if config else "cloudquery"
        
        # CloudQuery configuration file path
        self.config_file = config.get("config_file") if config else None
        
        # Providers to scan (aws, azure, gcp, k8s, etc.)
        self.providers = config.get("providers", ["aws"]) if config else ["aws"]
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover assets using CloudQuery.
        
        Args:
            target: Optional provider to scan
            **kwargs: Additional CloudQuery options
            
        Returns:
            ScanResult with discovered assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        # Determine which providers to scan
        providers = [target] if target else self.providers
        
        try:
            # Run CloudQuery sync
            sync_result = await self._run_cloudquery_sync(providers)
            
            # Query assets from CloudQuery database
            assets = await self._query_assets(providers, errors)
            
        except Exception as e:
            errors.append(f"CloudQuery scan failed: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "providers": providers,
                "config_file": self.config_file
            }
        )
    
    async def _run_cloudquery_sync(self, providers: List[str]) -> Dict[str, Any]:
        """Execute CloudQuery sync to fetch data."""
        cmd = [self.cloudquery_path, "sync"]
        
        if self.config_file:
            cmd.append(self.config_file)
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"CloudQuery sync failed: {stderr.decode()}")
        
        return {"status": "completed"}
    
    async def _query_assets(self, providers: List[str], errors: List[str]) -> List[DiscoveredAsset]:
        """Query assets from CloudQuery PostgreSQL database."""
        assets = []
        
        # CloudQuery stores data in PostgreSQL
        # We'll use cloudquery CLI to export to JSON
        
        for provider in providers:
            try:
                if provider == "aws":
                    provider_assets = await self._query_aws_assets()
                    assets.extend(provider_assets)
                elif provider == "azure":
                    provider_assets = await self._query_azure_assets()
                    assets.extend(provider_assets)
                elif provider == "gcp":
                    provider_assets = await self._query_gcp_assets()
                    assets.extend(provider_assets)
                elif provider == "k8s":
                    provider_assets = await self._query_k8s_assets()
                    assets.extend(provider_assets)
            except Exception as e:
                errors.append(f"Failed to query {provider} assets: {str(e)}")
        
        return assets
    
    async def _query_aws_assets(self) -> List[DiscoveredAsset]:
        """Query AWS assets from CloudQuery."""
        assets = []
        
        # Query EC2 instances
        ec2_query = """
        SELECT 
            instance_id, 
            instance_type, 
            tags, 
            state, 
            public_ip_address,
            private_ip_address,
            region
        FROM aws_ec2_instances
        WHERE state = 'running'
        """
        
        ec2_results = await self._execute_query(ec2_query)
        
        for row in ec2_results:
            tags = row.get("tags", {})
            
            asset = DiscoveredAsset(
                identifier=row["instance_id"],
                name=tags.get("Name", row["instance_id"]),
                type=AssetType.SERVER.value,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="aws",
                environment=tags.get("Environment", "unknown").lower(),
                location=row.get("region"),
                criticality=self._parse_criticality_tag(tags.get("Criticality")),
                exposure="INTERNET" if row.get("public_ip_address") else "INTRANET",
                ip_addresses=[ip for ip in [row.get("public_ip_address"), row.get("private_ip_address")] if ip],
                cloud_account_id=row.get("account_id"),
                cloud_region=row.get("region"),
                cloud_instance_type=row.get("instance_type"),
                cloud_tags=tags,
                owner_team=tags.get("Owner"),
                raw_data=row
            )
            assets.append(asset)
        
        # Query RDS instances
        rds_query = """
        SELECT 
            db_instance_identifier,
            db_instance_class,
            engine,
            publicly_accessible,
            region,
            tags
        FROM aws_rds_instances
        WHERE db_instance_status = 'available'
        """
        
        rds_results = await self._execute_query(rds_query)
        
        for row in rds_results:
            tags = row.get("tags", {})
            
            asset = DiscoveredAsset(
                identifier=row["db_instance_identifier"],
                name=row["db_instance_identifier"],
                type=AssetType.DATABASE.value,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="aws",
                environment=tags.get("Environment", "unknown").lower(),
                location=row.get("region"),
                criticality=4,  # Databases are typically critical
                exposure="INTERNET" if row.get("publicly_accessible") else "INTRANET",
                cloud_account_id=row.get("account_id"),
                cloud_region=row.get("region"),
                cloud_tags=tags,
                owner_team=tags.get("Owner"),
                running_services=[row.get("engine")],
                raw_data=row
            )
            assets.append(asset)
        
        return assets
    
    async def _query_azure_assets(self) -> List[DiscoveredAsset]:
        """Query Azure assets from CloudQuery."""
        assets = []
        
        # Query Azure VMs
        vm_query = """
        SELECT 
            id,
            name,
            type,
            location,
            tags,
            properties
        FROM azure_compute_virtual_machines
        """
        
        vm_results = await self._execute_query(vm_query)
        
        for row in vm_results:
            tags = row.get("tags", {})
            
            asset = DiscoveredAsset(
                identifier=row["id"],
                name=row["name"],
                type=AssetType.VM.value,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="azure",
                environment=tags.get("Environment", "unknown").lower(),
                location=row.get("location"),
                criticality=self._parse_criticality_tag(tags.get("Criticality")),
                exposure="INTRANET",
                cloud_tags=tags,
                owner_team=tags.get("Owner"),
                raw_data=row
            )
            assets.append(asset)
        
        return assets
    
    async def _query_gcp_assets(self) -> List[DiscoveredAsset]:
        """Query GCP assets from CloudQuery."""
        assets = []
        
        # Query GCP Compute instances
        compute_query = """
        SELECT 
            id,
            name,
            machine_type,
            status,
            zone,
            labels
        FROM gcp_compute_instances
        WHERE status = 'RUNNING'
        """
        
        compute_results = await self._execute_query(compute_query)
        
        for row in compute_results:
            labels = row.get("labels", {})
            
            asset = DiscoveredAsset(
                identifier=str(row["id"]),
                name=row["name"],
                type=AssetType.SERVER.value,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="gcp",
                environment=labels.get("environment", "unknown").lower(),
                location=row.get("zone"),
                criticality=self._parse_criticality_tag(labels.get("criticality")),
                exposure="INTRANET",
                cloud_instance_type=row.get("machine_type"),
                cloud_tags=labels,
                owner_team=labels.get("owner"),
                raw_data=row
            )
            assets.append(asset)
        
        return assets
    
    async def _query_k8s_assets(self) -> List[DiscoveredAsset]:
        """Query Kubernetes assets from CloudQuery."""
        assets = []
        
        # Query K8s pods
        pods_query = """
        SELECT 
            uid,
            name,
            namespace,
            labels,
            status
        FROM k8s_core_pods
        WHERE status_phase = 'Running'
        """
        
        pods_results = await self._execute_query(pods_query)
        
        for row in pods_results:
            labels = row.get("labels", {})
            namespace = row.get("namespace", "default")
            
            asset = DiscoveredAsset(
                identifier=row["uid"],
                name=f"{namespace}/{row['name']}",
                type=AssetType.POD.value,
                scanner_type=ScannerType.KUBERNETES.value,
                source=self.scanner_name,
                platform="kubernetes",
                location=namespace,
                criticality=3,
                exposure="ISOLATED",
                cloud_tags=labels,
                raw_data=row
            )
            assets.append(asset)
        
        return assets
    
    async def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query against CloudQuery database."""
        # Create temp file for query
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(query)
            query_file = f.name
        
        try:
            # Use cloudquery CLI to execute query and output JSON
            cmd = [
                self.cloudquery_path,
                "query",
                query_file,
                "--output", "json"
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"Query failed: {stderr.decode()}")
            
            # Parse JSON output
            results = json.loads(stdout.decode())
            return results
        
        finally:
            if os.path.exists(query_file):
                os.unlink(query_file)
    
    def _parse_criticality_tag(self, criticality: Optional[str]) -> int:
        """Parse criticality tag to integer."""
        if not criticality:
            return 3
        
        criticality_map = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "dev": 1
        }
        return criticality_map.get(criticality.lower(), 3)
    
    async def test_connection(self) -> bool:
        """Test if CloudQuery is available and configured."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.cloudquery_path,
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """CloudQuery requires configuration file."""
        return ["config_file"]  # Optional: cloudquery_path, providers
