"""
Device42 DCIM/IPAM integration for asset discovery.

Device42 provides Data Center Infrastructure Management (DCIM),
IP Address Management (IPAM), and comprehensive IT asset management.
"""
import time
from typing import Optional, List, Dict, Any
import httpx

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class Device42Scanner(BaseScanner):
    """
    Device42 DCIM/IPAM asset discovery scanner.
    
    Requires: Device42 instance URL, username, password
    Discovers: Devices, servers, network equipment, IP addresses
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CMDB
        self.scanner_name = "device42"
        
        if not config:
            raise ValueError("Device42 config required: instance_url, username, password")
        
        self.instance_url = config.get("instance_url")
        self.username = config.get("username")
        self.password = config.get("password")
        
        if not all([self.instance_url, self.username, self.password]):
            raise ValueError("Missing required Device42 configuration")
        
        # Base API URL
        self.api_base = f"{self.instance_url}/api/1.0"
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover assets from Device42.
        
        Args:
            target: Optional device type to scan ("devices", "ips", "racks", etc.)
            **kwargs: Additional query parameters
            
        Returns:
            ScanResult with discovered assets from Device42
        """
        start_time = time.time()
        assets = []
        errors = []
        
        # Determine what to scan
        scan_types = [target] if target else ["devices", "ips", "racks"]
        
        for scan_type in scan_types:
            try:
                if scan_type == "devices":
                    type_assets = await self._discover_devices(errors)
                    assets.extend(type_assets)
                elif scan_type == "ips":
                    type_assets = await self._discover_ip_addresses(errors)
                    assets.extend(type_assets)
                elif scan_type == "racks":
                    type_assets = await self._discover_rack_devices(errors)
                    assets.extend(type_assets)
            except Exception as e:
                errors.append(f"Failed to discover {scan_type}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "instance_url": self.instance_url,
                "scan_types": scan_types
            }
        )
    
    async def _discover_devices(self, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover devices from Device42."""
        assets = []
        
        url = f"{self.api_base}/devices"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.username, self.password),
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                for device in data.get("Devices", []):
                    device_id = device.get("device_id")
                    name = device.get("name")
                    device_type = device.get("type", "").lower()
                    
                    # Map device type to asset type
                    asset_type = self._map_device_type(device_type)
                    
                    # Extract device info
                    os_name = device.get("os")
                    os_family = self._detect_os_family(os_name)
                    
                    # Service level (criticality)
                    service_level = device.get("service_level", "Production").lower()
                    criticality_map = {
                        "critical": 5,
                        "production": 4,
                        "staging": 3,
                        "development": 2,
                        "test": 1
                    }
                    criticality = criticality_map.get(service_level, 3)
                    
                    # Location
                    location = device.get("building") or device.get("room")
                    
                    # Tags and custom fields
                    tags = device.get("tags", [])
                    custom_fields = device.get("custom_fields", {})
                    
                    # Owner
                    owner_team = custom_fields.get("owner_team") or device.get("customer")
                    owner_email = custom_fields.get("owner_email")
                    
                    # IP addresses
                    ip_addresses = []
                    for ip_info in device.get("ip_addresses", []):
                        ip = ip_info.get("ip")
                        if ip:
                            ip_addresses.append(ip)
                    
                    asset = DiscoveredAsset(
                        identifier=str(device_id),
                        name=name,
                        type=asset_type,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="device42",
                        environment=service_level,
                        location=location,
                        criticality=criticality,
                        exposure="INTRANET",  # Device42 tracks internal assets
                        os_family=os_family,
                        os_version=device.get("os_version"),
                        ip_addresses=ip_addresses,
                        owner_team=owner_team,
                        owner_email=owner_email,
                        cmdb_id=str(device_id),
                        cloud_tags={
                            "device_type": device_type,
                            "tags": tags,
                            **custom_fields
                        },
                        raw_data=device
                    )
                    
                    assets.append(asset)
        
        except httpx.HTTPError as e:
            errors.append(f"Device discovery failed: {str(e)}")
        
        return assets
    
    async def _discover_ip_addresses(self, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover IP addresses and associated devices."""
        assets = []
        
        url = f"{self.api_base}/ips"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.username, self.password),
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                for ip_entry in data.get("ips", []):
                    # Only create assets for IPs with associated devices
                    device_name = ip_entry.get("device")
                    if not device_name:
                        continue
                    
                    ip_address = ip_entry.get("ip")
                    subnet = ip_entry.get("subnet")
                    
                    # These are network-level assets
                    asset = DiscoveredAsset(
                        identifier=f"ip-{ip_address}",
                        name=device_name,
                        type=AssetType.SERVER.value,
                        scanner_type=ScannerType.NETWORK.value,
                        source=self.scanner_name,
                        platform="device42",
                        criticality=3,
                        exposure="INTRANET",
                        ip_addresses=[ip_address],
                        cloud_tags={
                            "subnet": subnet,
                            "ip_type": ip_entry.get("type")
                        },
                        raw_data=ip_entry
                    )
                    
                    assets.append(asset)
        
        except httpx.HTTPError as e:
            errors.append(f"IP address discovery failed: {str(e)}")
        
        return assets
    
    async def _discover_rack_devices(self, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover rack-mounted devices."""
        assets = []
        
        url = f"{self.api_base}/racks"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.username, self.password),
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                for rack in data.get("racks", []):
                    rack_name = rack.get("name")
                    building = rack.get("building")
                    room = rack.get("room")
                    
                    # Get devices in this rack
                    for device in rack.get("devices", []):
                        device_name = device.get("name")
                        
                        asset = DiscoveredAsset(
                            identifier=f"rack-{rack_name}-{device_name}",
                            name=device_name,
                            type=AssetType.SERVER.value,
                            scanner_type=self.scanner_type.value,
                            source=self.scanner_name,
                            platform="device42",
                            location=f"{building}/{room}/{rack_name}",
                            criticality=4,  # Rack devices are typically important
                            exposure="INTRANET",
                            cloud_tags={
                                "rack": rack_name,
                                "building": building,
                                "room": room,
                                "start_u": device.get("start_u"),
                                "size_u": device.get("size")
                            },
                            raw_data=device
                        )
                        
                        assets.append(asset)
        
        except httpx.HTTPError as e:
            errors.append(f"Rack device discovery failed: {str(e)}")
        
        return assets
    
    def _map_device_type(self, device_type: str) -> str:
        """Map Device42 device type to asset type."""
        if "server" in device_type or "virtual" in device_type:
            return AssetType.SERVER.value
        elif "network" in device_type or "switch" in device_type or "router" in device_type:
            return AssetType.NETWORK_DEVICE.value
        elif "storage" in device_type:
            return AssetType.STORAGE.value
        elif "database" in device_type:
            return AssetType.DATABASE.value
        else:
            return AssetType.SERVER.value
    
    def _detect_os_family(self, os_name: Optional[str]) -> Optional[str]:
        """Detect OS family from OS name."""
        if not os_name:
            return None
        
        os_lower = os_name.lower()
        
        if any(keyword in os_lower for keyword in ['linux', 'ubuntu', 'centos', 'rhel', 'debian']):
            return 'linux'
        elif 'windows' in os_lower:
            return 'windows'
        elif any(keyword in os_lower for keyword in ['mac', 'darwin', 'osx']):
            return 'macos'
        elif any(keyword in os_lower for keyword in ['cisco', 'juniper', 'palo alto']):
            return 'network_os'
        
        return None
    
    async def test_connection(self) -> bool:
        """Test Device42 API connectivity."""
        try:
            url = f"{self.api_base}/devices"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.username, self.password),
                    params={"limit": 1},
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Required configuration for Device42 scanner."""
        return ["instance_url", "username", "password"]
