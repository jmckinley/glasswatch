"""
Azure asset discovery scanner.

Discovers VMs, Container Instances, App Services, SQL Databases,
AKS clusters, and other Azure resources.
"""
import time
from typing import Optional, List, Dict, Any

try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.containerinstance import ContainerInstanceManagementClient
    from azure.mgmt.containerservice import ContainerServiceClient
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.resource import SubscriptionClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class AzureScanner(BaseScanner):
    """
    Azure infrastructure discovery scanner.
    
    Requires: azure-identity, azure-mgmt-* packages
    Discovers: VMs, Container Instances, App Services, SQL, AKS
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CLOUD
        self.scanner_name = "azure"
        
        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure SDK is required for Azure scanning. "
                "Install: pip install azure-identity azure-mgmt-compute "
                "azure-mgmt-sql azure-mgmt-containerinstance "
                "azure-mgmt-containerservice azure-mgmt-web azure-mgmt-resource"
            )
        
        # Azure credentials (uses DefaultAzureCredential - env vars, managed identity, CLI)
        self.credential = DefaultAzureCredential()
        
        # Subscription ID from config or will discover all
        self.subscription_id = config.get("subscription_id") if config else None
        self.subscription_ids = config.get("subscription_ids", []) if config else []
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover Azure assets across subscriptions.
        
        Args:
            target: Optional subscription ID to scan
            **kwargs: Additional options
            
        Returns:
            ScanResult with discovered Azure assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        # Determine which subscriptions to scan
        if target:
            subscription_ids = [target]
        elif self.subscription_id:
            subscription_ids = [self.subscription_id]
        elif self.subscription_ids:
            subscription_ids = self.subscription_ids
        else:
            # Discover all accessible subscriptions
            try:
                subscription_ids = await self._list_subscriptions()
            except Exception as e:
                errors.append(f"Failed to list subscriptions: {str(e)}")
                subscription_ids = []
        
        for subscription_id in subscription_ids:
            try:
                # VMs
                vm_assets = await self._discover_vms(subscription_id, errors)
                assets.extend(vm_assets)
                
                # SQL Databases
                sql_assets = await self._discover_sql(subscription_id, errors)
                assets.extend(sql_assets)
                
                # Container Instances
                aci_assets = await self._discover_container_instances(subscription_id, errors)
                assets.extend(aci_assets)
                
                # AKS Clusters
                aks_assets = await self._discover_aks(subscription_id, errors)
                assets.extend(aks_assets)
                
                # App Services
                app_assets = await self._discover_app_services(subscription_id, errors)
                assets.extend(app_assets)
                
            except Exception as e:
                errors.append(f"Failed to scan subscription {subscription_id}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "subscriptions_scanned": subscription_ids,
                "resource_types": ["vm", "sql", "container_instance", "aks", "app_service"]
            }
        )
    
    async def _list_subscriptions(self) -> List[str]:
        """Discover all accessible Azure subscriptions."""
        subscription_client = SubscriptionClient(self.credential)
        subscriptions = []
        
        for sub in subscription_client.subscriptions.list():
            subscriptions.append(sub.subscription_id)
        
        return subscriptions
    
    async def _discover_vms(self, subscription_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Azure VMs."""
        assets = []
        
        try:
            compute_client = ComputeManagementClient(self.credential, subscription_id)
            
            for vm in compute_client.virtual_machines.list_all():
                vm_id = vm.id
                name = vm.name
                location = vm.location
                
                # Extract tags
                tags = vm.tags or {}
                environment = tags.get("Environment", "unknown").lower()
                
                # Get instance details
                instance_view = compute_client.virtual_machines.instance_view(
                    vm.id.split("/")[4],  # resource group
                    vm.name
                )
                
                # Determine exposure (heuristic based on public IP)
                has_public_ip = any(
                    nic.primary for nic in vm.network_profile.network_interfaces
                )
                exposure = "INTERNET" if has_public_ip else "INTRANET"
                
                # Criticality from tags
                criticality_map = {
                    "critical": 5,
                    "high": 4,
                    "medium": 3,
                    "low": 2,
                    "dev": 1
                }
                criticality = criticality_map.get(
                    tags.get("Criticality", "medium").lower(),
                    3
                )
                
                # OS info
                os_family = "linux"
                if vm.storage_profile.os_disk.os_type:
                    os_family = vm.storage_profile.os_disk.os_type.lower()
                
                asset = DiscoveredAsset(
                    identifier=vm_id,
                    name=name,
                    type=AssetType.VM.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="azure",
                    environment=environment,
                    location=location,
                    criticality=criticality,
                    exposure=exposure,
                    os_family=os_family,
                    cloud_account_id=subscription_id,
                    cloud_region=location,
                    cloud_instance_type=vm.hardware_profile.vm_size,
                    cloud_tags=tags,
                    owner_team=tags.get("Owner"),
                    raw_data={
                        "vm_id": vm_id,
                        "resource_group": vm.id.split("/")[4]
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"VM discovery failed in {subscription_id}: {str(e)}")
        
        return assets
    
    async def _discover_sql(self, subscription_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Azure SQL databases."""
        assets = []
        
        try:
            sql_client = SqlManagementClient(self.credential, subscription_id)
            
            for server in sql_client.servers.list():
                for db in sql_client.databases.list_by_server(
                    server.id.split("/")[4],  # resource group
                    server.name
                ):
                    if db.name == "master":
                        continue  # Skip system database
                    
                    db_id = db.id
                    name = f"{server.name}/{db.name}"
                    location = db.location
                    
                    tags = db.tags or {}
                    environment = tags.get("Environment", "unknown").lower()
                    
                    # SQL databases are typically critical
                    criticality = 4
                    
                    # Exposure depends on firewall rules (default INTRANET)
                    exposure = "INTRANET"
                    
                    asset = DiscoveredAsset(
                        identifier=db_id,
                        name=name,
                        type=AssetType.DATABASE.value,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="azure",
                        environment=environment,
                        location=location,
                        criticality=criticality,
                        exposure=exposure,
                        cloud_account_id=subscription_id,
                        cloud_region=location,
                        cloud_tags=tags,
                        owner_team=tags.get("Owner"),
                        running_services=["azure-sql"],
                        raw_data={
                            "database_id": db_id,
                            "server": server.name,
                            "sku": db.sku.name if db.sku else None
                        }
                    )
                    
                    assets.append(asset)
        
        except Exception as e:
            errors.append(f"SQL discovery failed in {subscription_id}: {str(e)}")
        
        return assets
    
    async def _discover_container_instances(self, subscription_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Azure Container Instances."""
        assets = []
        
        try:
            aci_client = ContainerInstanceManagementClient(self.credential, subscription_id)
            
            for container_group in aci_client.container_groups.list():
                cg_id = container_group.id
                name = container_group.name
                location = container_group.location
                
                tags = container_group.tags or {}
                environment = tags.get("Environment", "unknown").lower()
                
                # Check if internet-facing
                has_public_ip = container_group.ip_address and container_group.ip_address.type == "Public"
                exposure = "INTERNET" if has_public_ip else "INTRANET"
                
                asset = DiscoveredAsset(
                    identifier=cg_id,
                    name=name,
                    type=AssetType.CONTAINER.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="azure",
                    environment=environment,
                    location=location,
                    criticality=3,
                    exposure=exposure,
                    cloud_account_id=subscription_id,
                    cloud_region=location,
                    cloud_tags=tags,
                    owner_team=tags.get("Owner"),
                    raw_data={
                        "container_group_id": cg_id,
                        "containers": [c.name for c in container_group.containers]
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"Container Instance discovery failed in {subscription_id}: {str(e)}")
        
        return assets
    
    async def _discover_aks(self, subscription_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Azure Kubernetes Service clusters."""
        assets = []
        
        try:
            aks_client = ContainerServiceClient(self.credential, subscription_id)
            
            for cluster in aks_client.managed_clusters.list():
                cluster_id = cluster.id
                name = cluster.name
                location = cluster.location
                
                tags = cluster.tags or {}
                environment = tags.get("Environment", "unknown").lower()
                
                asset = DiscoveredAsset(
                    identifier=cluster_id,
                    name=name,
                    type=AssetType.APPLICATION.value,
                    scanner_type=ScannerType.KUBERNETES.value,
                    source=self.scanner_name,
                    platform="azure",
                    environment=environment,
                    location=location,
                    criticality=4,
                    exposure="INTRANET",
                    cloud_account_id=subscription_id,
                    cloud_region=location,
                    cloud_tags=tags,
                    owner_team=tags.get("Owner"),
                    raw_data={
                        "cluster_id": cluster_id,
                        "kubernetes_version": cluster.kubernetes_version
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"AKS discovery failed in {subscription_id}: {str(e)}")
        
        return assets
    
    async def _discover_app_services(self, subscription_id: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Azure App Services."""
        assets = []
        
        try:
            web_client = WebSiteManagementClient(self.credential, subscription_id)
            
            for app in web_client.web_apps.list():
                app_id = app.id
                name = app.name
                location = app.location
                
                tags = app.tags or {}
                environment = tags.get("Environment", "unknown").lower()
                
                # App Services are typically internet-facing
                exposure = "INTERNET"
                
                asset = DiscoveredAsset(
                    identifier=app_id,
                    name=name,
                    type=AssetType.APPLICATION.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="azure",
                    environment=environment,
                    location=location,
                    criticality=3,
                    exposure=exposure,
                    cloud_account_id=subscription_id,
                    cloud_region=location,
                    cloud_tags=tags,
                    owner_team=tags.get("Owner"),
                    raw_data={
                        "app_id": app_id,
                        "default_host_name": app.default_host_name,
                        "state": app.state
                    }
                )
                
                assets.append(asset)
        
        except Exception as e:
            errors.append(f"App Service discovery failed in {subscription_id}: {str(e)}")
        
        return assets
    
    async def test_connection(self) -> bool:
        """Test Azure credentials and connectivity."""
        try:
            subscription_client = SubscriptionClient(self.credential)
            # Try to list subscriptions
            list(subscription_client.subscriptions.list())
            return True
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Azure scanner uses DefaultAzureCredential (env vars, managed identity, CLI)."""
        return []  # Optional: subscription_id, subscription_ids
