"""
Jira Assets (formerly Insight) CMDB integration.

Atlassian's asset and configuration management solution.
Discovers assets from Jira Service Management Asset Management.
"""
import time
from typing import Optional, List, Dict, Any
import httpx

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class JiraAssetsScanner(BaseScanner):
    """
    Jira Assets (Insight) CMDB scanner.
    
    Requires: Jira instance URL, API token, workspace ID
    Discovers: Assets from Jira Service Management Asset Management
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CMDB
        self.scanner_name = "jira_assets"
        
        if not config:
            raise ValueError("Jira Assets config required: instance_url, email, api_token, workspace_id")
        
        self.instance_url = config.get("instance_url")
        self.email = config.get("email")
        self.api_token = config.get("api_token")
        self.workspace_id = config.get("workspace_id")
        
        if not all([self.instance_url, self.email, self.api_token, self.workspace_id]):
            raise ValueError("Missing required Jira Assets configuration")
        
        # Base API URL (Jira Assets uses /jsm/assets/workspace/{workspaceId}/v1/)
        self.api_base = f"{self.instance_url}/rest/assets/1.0"
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover assets from Jira Assets.
        
        Args:
            target: Optional object schema ID to scan
            **kwargs: Additional query parameters
            
        Returns:
            ScanResult with discovered assets from Jira Assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        try:
            # Get object schemas (asset types)
            schemas = await self._get_object_schemas()
            
            # If target specified, filter to that schema
            if target:
                schemas = [s for s in schemas if s["id"] == target]
            
            # Scan each schema
            for schema in schemas:
                schema_id = schema["id"]
                schema_name = schema["name"]
                
                try:
                    schema_assets = await self._scan_object_schema(schema_id, schema_name, errors)
                    assets.extend(schema_assets)
                except Exception as e:
                    errors.append(f"Failed to scan schema {schema_name}: {str(e)}")
        
        except Exception as e:
            errors.append(f"Failed to list object schemas: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "instance_url": self.instance_url,
                "workspace_id": self.workspace_id
            }
        )
    
    async def _get_object_schemas(self) -> List[Dict[str, Any]]:
        """Get all object schemas (asset types) in the workspace."""
        url = f"{self.api_base}/objectschema/list"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.email, self.api_token),
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("objectschemas", [])
    
    async def _scan_object_schema(
        self,
        schema_id: str,
        schema_name: str,
        errors: List[str]
    ) -> List[DiscoveredAsset]:
        """Scan all objects in an object schema."""
        assets = []
        
        # Get object types in this schema
        object_types = await self._get_object_types(schema_id)
        
        for object_type in object_types:
            type_id = object_type["id"]
            type_name = object_type["name"]
            
            try:
                # Query objects of this type
                objects = await self._get_objects_by_type(schema_id, type_id)
                
                for obj in objects:
                    asset = self._parse_object(obj, schema_name, type_name)
                    if asset:
                        assets.append(asset)
            
            except Exception as e:
                errors.append(f"Failed to scan {schema_name}/{type_name}: {str(e)}")
        
        return assets
    
    async def _get_object_types(self, schema_id: str) -> List[Dict[str, Any]]:
        """Get all object types in a schema."""
        url = f"{self.api_base}/objectschema/{schema_id}/objecttypes/flat"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.email, self.api_token),
                timeout=30.0
            )
            response.raise_for_status()
            
            return response.json()
    
    async def _get_objects_by_type(
        self,
        schema_id: str,
        type_id: str
    ) -> List[Dict[str, Any]]:
        """Get all objects of a specific type."""
        url = f"{self.api_base}/aql/objects"
        
        # AQL query to get all objects of this type
        aql = f"objectType = {type_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(self.email, self.api_token),
                json={"qlQuery": aql, "page": 1, "pageSize": 100},
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("objectEntries", [])
    
    def _parse_object(
        self,
        obj: Dict[str, Any],
        schema_name: str,
        type_name: str
    ) -> Optional[DiscoveredAsset]:
        """Parse Jira Assets object into DiscoveredAsset."""
        obj_id = obj.get("id")
        obj_key = obj.get("objectKey")
        label = obj.get("label", obj_key)
        
        # Extract attributes
        attributes = {}
        for attr in obj.get("attributes", []):
            attr_name = attr.get("objectTypeAttribute", {}).get("name")
            attr_values = attr.get("objectAttributeValues", [])
            
            if attr_values:
                # Take first value (multi-value attributes exist)
                value = attr_values[0].get("value")
                if value:
                    attributes[attr_name] = value
        
        # Map type to asset type
        asset_type = self._map_type_to_asset_type(type_name)
        
        # Extract common fields
        environment = attributes.get("Environment", "unknown").lower()
        location = attributes.get("Location")
        ip_address = attributes.get("IP Address")
        fqdn = attributes.get("FQDN") or attributes.get("Hostname")
        os_family = self._detect_os_family(attributes.get("Operating System"))
        
        # Criticality
        criticality_map = {
            "Critical": 5,
            "High": 4,
            "Medium": 3,
            "Low": 2,
            "None": 1
        }
        criticality = criticality_map.get(attributes.get("Criticality", "Medium"), 3)
        
        # Exposure
        exposure = "INTRANET"
        if attributes.get("Internet Facing") == "Yes":
            exposure = "INTERNET"
        
        # Owner
        owner_team = attributes.get("Owner") or attributes.get("Team")
        owner_email = attributes.get("Owner Email")
        
        asset = DiscoveredAsset(
            identifier=str(obj_id),
            name=label,
            type=asset_type,
            scanner_type=self.scanner_type.value,
            source=self.scanner_name,
            platform="jira_assets",
            environment=environment,
            location=location,
            criticality=criticality,
            exposure=exposure,
            os_family=os_family,
            os_version=attributes.get("OS Version"),
            ip_addresses=[ip_address] if ip_address else [],
            fqdn=fqdn,
            owner_team=owner_team,
            owner_email=owner_email,
            cmdb_id=obj_key,
            cloud_tags={
                "schema": schema_name,
                "type": type_name,
                **attributes
            },
            raw_data=obj
        )
        
        return asset
    
    def _map_type_to_asset_type(self, type_name: str) -> str:
        """Map Jira Assets object type to asset type."""
        type_lower = type_name.lower()
        
        if "server" in type_lower or "vm" in type_lower or "host" in type_lower:
            return AssetType.SERVER.value
        elif "database" in type_lower or "db" in type_lower:
            return AssetType.DATABASE.value
        elif "application" in type_lower or "app" in type_lower or "software" in type_lower:
            return AssetType.APPLICATION.value
        elif "network" in type_lower or "switch" in type_lower or "router" in type_lower:
            return AssetType.NETWORK_DEVICE.value
        elif "container" in type_lower or "docker" in type_lower:
            return AssetType.CONTAINER.value
        elif "laptop" in type_lower or "workstation" in type_lower or "desktop" in type_lower:
            return AssetType.SERVER.value
        else:
            return AssetType.APPLICATION.value
    
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
        
        return None
    
    async def test_connection(self) -> bool:
        """Test Jira Assets API connectivity."""
        try:
            url = f"{self.api_base}/objectschema/list"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.email, self.api_token),
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Required configuration for Jira Assets scanner."""
        return ["instance_url", "email", "api_token", "workspace_id"]
