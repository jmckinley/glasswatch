"""
GCP asset discovery scanner.

Discovers Compute Engine VMs, Cloud SQL, GKE clusters, Cloud Run,
Cloud Functions, and other GCP resources.
"""
import time
from typing import Optional, List, Dict, Any

try:
    from google.cloud import compute_v1
    from google.cloud import sql_v1
    from google.cloud import container_v1
    from google.cloud import run_v2
    from google.cloud import functions_v1
    from google.cloud import resourcemanager_v3
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class GCPScanner(BaseScanner):
    """
    GCP infrastructure discovery scanner.
    
    Requires: google-cloud-compute, google-cloud-sql, google-cloud-container, etc.
    Discovers: Compute Engine, Cloud SQL, GKE, Cloud Run, Cloud Functions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CLOUD
        self.scanner_name = "gcp"
        
        if not GCP_AVAILABLE:
            raise ImportError(
                "GCP SDK is required for GCP scanning. "
                "Install: pip install google-cloud-compute google-cloud-sql "
                "google-cloud-container google-cloud-run google-cloud-functions "
                "google-cloud-resource-manager"
            )
        
        # GCP project ID from config or will discover all
        self.project_id = config.get("project_id") if config else None
        self.project_ids = config.get("project_ids", []) if config else []
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover GCP assets across projects.
        
        Args:
            target: Optional project ID to scan
            **kwargs: Additional options
            
        Returns:
            ScanResult with discovered GCP assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        # Determine which projects to scan
        if target:
            project_ids = [target]
        elif self.project_id:
            project_ids = [self.project_id]
        elif self.project_ids:
            project_ids = self.project_ids
        else:
            # Discover all accessible projects
            try:
                project_ids = await self._list_projects()
            except Exception as e:
                errors.append(f"Failed to list projects: {str(e)}")
                project_ids = []
        
        for project_id in project_ids:
            try:
                # Compute Engine VMs
                vm_assets = await self._discover_compute_vms(project_id, errors)
                assets.extend(vm_assets)
                
                # Cloud SQL
                sql_assets = await self._discover_cloud_sql(project_id, errors)
                assets.extend(sql_assets)
                
                # GKE Clusters
                gke_assets = await self._discover_gke(project_id, errors)
                assets.extend(gke_assets)
                
                # Cloud Run Services
                run_assets = await self._discover_cloud_run(project_id, errors)
                assets.extend(run_assets)
                
                # Cloud Functions
                function_assets = await self._discover_cloud_functions(project_id, errors)
                assets.extend(function_assets)
                
            except Exception as e:
                errors.append(f"Failed to scan project {project_id}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "projects_scanned": project_ids,
                "resource_types": ["compute", "sql", "gke", "cloud_run", "cloud_functions"]
            }
        )
    
    async def _list_projects(self) -> List[str]:
        """Discover all accessible GCP projects."""
        projects = []
        
        try:
            client = resourcemanager_v3.ProjectsClient()
            for project in client.search_projects():
                projects.append(project.project_id)
        except Exception:
            pass
        
        return projects
    
    async def _discover_compute_vms(self, project_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Compute Engine VMs."""
        assets = []
        
        try:
            instances_client = compute_v1.InstancesClient()
            
            # List all zones
            zones_client = compute_v1.ZonesClient()
            zones = zones_client.list(project=project_id)
            
            for zone in zones:
                zone_name = zone.name
                
                for instance in instances_client.list(project=project_id, zone=zone_name):
                    instance_id = instance.id
                    name = instance.name
                    
                    # Extract labels (GCP's version of tags)
                    labels = instance.labels or {}
                    environment = labels.get("environment", "unknown").lower()
                    
                    # Determine exposure
                    has_external_ip = any(
                        access_config.nat_i_p
                        for network_interface in instance.network_interfaces
                        for access_config in network_interface.access_configs
                    )
                    exposure = "INTERNET" if has_external_ip else "INTRANET"
                    
                    # Criticality from labels
                    criticality_map = {
                        "critical": 5,
                        "high": 4,
                        "medium": 3,
                        "low": 2,
                        "dev": 1
                    }
                    criticality = criticality_map.get(
                        labels.get("criticality", "medium").lower(),
                        3
                    )
                    
                    # Get IPs
                    ip_addresses = []
                    for ni in instance.network_interfaces:
                        if ni.network_i_p:
                            ip_addresses.append(ni.network_i_p)
                        for ac in ni.access_configs:
                            if ac.nat_i_p:
                                ip_addresses.append(ac.nat_i_p)
                    
                    # OS family (heuristic)
                    os_family = "linux"
                    for disk in instance.disks:
                        if "windows" in disk.source.lower():
                            os_family = "windows"
                            break
                    
                    asset = DiscoveredAsset(
                        identifier=str(instance_id),
                        name=name,
                        type=AssetType.SERVER.value,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="gcp",
                        environment=environment,
                        location=zone_name,
                        criticality=criticality,
                        exposure=exposure,
                        os_family=os_family,
                        ip_addresses=ip_addresses,
                        cloud_account_id=project_id,
                        cloud_region=zone.region,
                        cloud_instance_type=instance.machine_type.split("/")[-1],
                        cloud_tags=labels,
                        owner_team=labels.get("owner"),
                        raw_data={
                            "instance_id": str(instance_id),
                            "zone": zone_name,
                            "status": instance.status
                        }
                    )
                    
                    assets.append(asset)
        
        except Exception as e:
            errors.append(f"Compute Engine discovery failed in {project_id}: {str(e)}")
        
        return assets
    
    async def _discover_cloud_sql(self, project_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Cloud SQL instances."""
        assets = []
        
        try:
            sql_client = sql_v1.SqlInstancesServiceClient()
            
            request = sql_v1.SqlInstancesListRequest(project=project_id)
            instances = sql_client.list(request=request)
            
            for instance in instances.items:
                instance_name = instance.name
                
                # Extract labels
                labels = instance.settings.user_labels or {}
                environment = labels.get("environment", "unknown").lower()
                
                # Determine exposure
                has_public_ip = any(
                    ip.type_ == "PRIMARY" 
                    for ip in instance.ip_addresses
                )
                exposure = "INTERNET" if has_public_ip else "INTRANET"
                
                # Databases are typically critical
                criticality = 4
                
                asset = DiscoveredAsset(
                    identifier=instance_name,
                    name=instance_name,
                    type=AssetType.DATABASE.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="gcp",
                    environment=environment,
                    location=instance.region,
                    criticality=criticality,
                    exposure=exposure,
                    cloud_account_id=project_id,
                    cloud_region=instance.region,
                    cloud_tags=labels,
                    owner_team=labels.get("owner"),
                    running_services=[instance.database_version],
                    raw_data={
                        "instance_name": instance_name,
                        "tier": instance.settings.tier,
                        "state": instance.state
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"Cloud SQL discovery failed in {project_id}: {str(e)}")
        
        return assets
    
    async def _discover_gke(self, project_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover GKE clusters."""
        assets = []
        
        try:
            gke_client = container_v1.ClusterManagerClient()
            
            # List all locations
            parent = f"projects/{project_id}/locations/-"
            clusters = gke_client.list_clusters(parent=parent)
            
            for cluster in clusters.clusters:
                cluster_name = cluster.name
                location = cluster.location
                
                # Extract labels
                labels = cluster.resource_labels or {}
                environment = labels.get("environment", "unknown").lower()
                
                asset = DiscoveredAsset(
                    identifier=f"gke:{project_id}/{location}/{cluster_name}",
                    name=cluster_name,
                    type=AssetType.APPLICATION.value,
                    scanner_type=ScannerType.KUBERNETES.value,
                    source=self.scanner_name,
                    platform="gcp",
                    environment=environment,
                    location=location,
                    criticality=4,
                    exposure="INTRANET",
                    cloud_account_id=project_id,
                    cloud_region=location,
                    cloud_tags=labels,
                    owner_team=labels.get("owner"),
                    raw_data={
                        "cluster_name": cluster_name,
                        "current_master_version": cluster.current_master_version,
                        "status": cluster.status
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"GKE discovery failed in {project_id}: {str(e)}")
        
        return assets
    
    async def _discover_cloud_run(self, project_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Cloud Run services."""
        assets = []
        
        try:
            run_client = run_v2.ServicesClient()
            
            # List all regions
            parent = f"projects/{project_id}/locations/-"
            services = run_client.list_services(parent=parent)
            
            for service in services:
                service_name = service.name.split("/")[-1]
                location = service.name.split("/")[3]
                
                # Extract labels
                labels = service.labels or {}
                environment = labels.get("environment", "unknown").lower()
                
                # Cloud Run is typically internet-facing
                exposure = "INTERNET"
                
                asset = DiscoveredAsset(
                    identifier=service.name,
                    name=service_name,
                    type=AssetType.APPLICATION.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="gcp",
                    environment=environment,
                    location=location,
                    criticality=3,
                    exposure=exposure,
                    cloud_account_id=project_id,
                    cloud_region=location,
                    cloud_tags=labels,
                    owner_team=labels.get("owner"),
                    raw_data={
                        "service_name": service_name,
                        "uri": service.uri
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"Cloud Run discovery failed in {project_id}: {str(e)}")
        
        return assets
    
    async def _discover_cloud_functions(self, project_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Cloud Functions."""
        assets = []
        
        try:
            functions_client = functions_v1.CloudFunctionsServiceClient()
            
            # List all locations
            parent = f"projects/{project_id}/locations/-"
            functions = functions_client.list_functions(parent=parent)
            
            for function in functions:
                function_name = function.name.split("/")[-1]
                location = function.name.split("/")[3]
                
                # Extract labels
                labels = function.labels or {}
                environment = labels.get("environment", "unknown").lower()
                
                # Functions exposure depends on trigger
                exposure = "ISOLATED"
                if function.https_trigger:
                    exposure = "INTERNET"
                
                asset = DiscoveredAsset(
                    identifier=function.name,
                    name=function_name,
                    type=AssetType.LAMBDA.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="gcp",
                    environment=environment,
                    location=location,
                    criticality=3,
                    exposure=exposure,
                    cloud_account_id=project_id,
                    cloud_region=location,
                    cloud_tags=labels,
                    owner_team=labels.get("owner"),
                    raw_data={
                        "function_name": function_name,
                        "runtime": function.runtime,
                        "status": function.status
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"Cloud Functions discovery failed in {project_id}: {str(e)}")
        
        return assets
    
    async def test_connection(self) -> bool:
        """Test GCP credentials and connectivity."""
        try:
            client = resourcemanager_v3.ProjectsClient()
            # Try to search projects
            list(client.search_projects(query=""))
            return True
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """GCP scanner uses Application Default Credentials (env var, service account)."""
        return []  # Optional: project_id, project_ids
