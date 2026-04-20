"""
ServiceNow CMDB integration for asset discovery.

Pulls Configuration Items (CIs) from ServiceNow CMDB.
Supports servers, databases, applications, network devices.
"""
import time
from typing import Optional, List, Dict, Any
import httpx

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class ServiceNowCMDBScanner(BaseScanner):
    """
    ServiceNow CMDB asset discovery scanner.
    
    Requires: ServiceNow instance URL, username, password (or OAuth token)
    Discovers: Servers, databases, applications, network devices
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CMDB
        self.scanner_name = "servicenow"
        
        if not config:
            raise ValueError("ServiceNow config required: instance_url, username, password")
        
        self.instance_url = config.get("instance_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.oauth_token = config.get("oauth_token")
        
        if not self.instance_url:
            raise ValueError("ServiceNow instance_url is required")
        
        if not (self.username and self.password) and not self.oauth_token:
            raise ValueError("ServiceNow credentials required (username/password or oauth_token)")
        
        # Base API URL
        self.api_base = f"{self.instance_url}/api/now/table"
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover assets from ServiceNow CMDB.
        
        Args:
            target: Optional CI class to scan (e.g., "cmdb_ci_server")
            **kwargs: Additional ServiceNow query parameters
            
        Returns:
            ScanResult with discovered assets from CMDB
        """
        start_time = time.time()
        assets = []
        errors = []
        
        # CI classes to scan
        if target:
            ci_classes = [target]
        else:
            ci_classes = [
                "cmdb_ci_server",
                "cmdb_ci_linux_server",
                "cmdb_ci_win_server",
                "cmdb_ci_database",
                "cmdb_ci_app_server",
                "cmdb_ci_netgear",
                "cmdb_ci_computer",
            ]
        
        for ci_class in ci_classes:
            try:
                ci_assets = await self._discover_ci_class(ci_class, errors)
                assets.extend(ci_assets)
            except Exception as e:
                errors.append(f"Failed to discover {ci_class}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "instance_url": self.instance_url,
                "ci_classes_scanned": ci_classes
            }
        )
    
    async def _discover_ci_class(self, ci_class: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover CIs from a specific class."""
        assets = []
        
        url = f"{self.api_base}/{ci_class}"
        
        # Build query parameters
        params = {
            "sysparm_limit": 1000,  # Adjust as needed
            "sysparm_query": "operational_status=1",  # Active CIs only
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Set authentication
                if self.oauth_token:
                    headers = {"Authorization": f"Bearer {self.oauth_token}"}
                    auth = None
                else:
                    headers = {}
                    auth = (self.username, self.password)
                
                response = await client.get(url, params=params, headers=headers, auth=auth, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                
                for ci in data.get("result", []):
                    asset = self._parse_ci(ci, ci_class)
                    if asset:
                        assets.append(asset)
        
        except httpx.HTTPError as e:
            errors.append(f"ServiceNow API error for {ci_class}: {str(e)}")
        
        return assets
    
    def _parse_ci(self, ci: Dict[str, Any], ci_class: str) -> Optional[DiscoveredAsset]:
        """Parse ServiceNow CI into DiscoveredAsset."""
        sys_id = ci.get("sys_id")
        name = ci.get("name") or ci.get("host_name") or sys_id
        
        # Map CI class to asset type
        asset_type = self._map_ci_class_to_asset_type(ci_class)
        
        # Extract common fields
        environment = ci.get("u_environment", "unknown").lower()  # Custom field
        location = ci.get("location", {}).get("name") if isinstance(ci.get("location"), dict) else None
        ip_address = ci.get("ip_address")
        fqdn = ci.get("fqdn")
        os_family = self._detect_os_family(ci_class, ci.get("os"))
        
        # Criticality mapping
        criticality_map = {
            "1 - Critical": 5,
            "2 - High": 4,
            "3 - Moderate": 3,
            "4 - Low": 2,
            "5 - Planning": 1
        }
        criticality = criticality_map.get(ci.get("business_criticality", "3 - Moderate"), 3)
        
        # Exposure (heuristic)
        exposure = "INTRANET"
        if ci.get("u_internet_facing") == "true":
            exposure = "INTERNET"
        
        # Owner info
        owner_team = None
        owner_email = None
        if ci.get("owned_by"):
            owner_data = ci.get("owned_by")
            if isinstance(owner_data, dict):
                owner_team = owner_data.get("name")
                owner_email = owner_data.get("email")
        
        asset = DiscoveredAsset(
            identifier=sys_id,
            name=name,
            type=asset_type,
            scanner_type=self.scanner_type.value,
            source=self.scanner_name,
            platform="servicenow",
            environment=environment,
            location=location,
            criticality=criticality,
            exposure=exposure,
            os_family=os_family,
            os_version=ci.get("os_version"),
            ip_addresses=[ip_address] if ip_address else [],
            fqdn=fqdn,
            owner_team=owner_team,
            owner_email=owner_email,
            cmdb_id=sys_id,
            raw_data=ci
        )
        
        return asset
    
    def _map_ci_class_to_asset_type(self, ci_class: str) -> str:
        """Map ServiceNow CI class to asset type."""
        if "server" in ci_class or "computer" in ci_class:
            return AssetType.SERVER.value
        elif "database" in ci_class:
            return AssetType.DATABASE.value
        elif "app" in ci_class:
            return AssetType.APPLICATION.value
        elif "netgear" in ci_class or "network" in ci_class:
            return AssetType.NETWORK_DEVICE.value
        else:
            return AssetType.SERVER.value
    
    def _detect_os_family(self, ci_class: str, os_name: Optional[str]) -> Optional[str]:
        """Detect OS family from CI class or OS name."""
        if "linux" in ci_class.lower():
            return "linux"
        elif "win" in ci_class.lower():
            return "windows"
        elif os_name:
            os_lower = os_name.lower()
            if "linux" in os_lower or "ubuntu" in os_lower or "centos" in os_lower or "rhel" in os_lower:
                return "linux"
            elif "windows" in os_lower:
                return "windows"
            elif "mac" in os_lower:
                return "macos"
        
        return None
    
    async def test_connection(self) -> bool:
        """Test ServiceNow API connectivity."""
        try:
            url = f"{self.api_base}/cmdb_ci_server"
            params = {"sysparm_limit": 1}
            
            async with httpx.AsyncClient() as client:
                if self.oauth_token:
                    headers = {"Authorization": f"Bearer {self.oauth_token}"}
                    auth = None
                else:
                    headers = {}
                    auth = (self.username, self.password)
                
                response = await client.get(url, params=params, headers=headers, auth=auth, timeout=10.0)
                return response.status_code == 200
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Required configuration for ServiceNow scanner."""
        return ["instance_url", "username", "password"]  # or oauth_token
