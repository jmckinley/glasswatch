"""
Base scanner interface for asset discovery.

All discovery scanners implement this interface for consistent behavior.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class ScannerType(Enum):
    """Types of discovery scanners."""
    CLOUD = "cloud"  # AWS, Azure, GCP APIs
    CONTAINER = "container"  # Docker, containerd images
    KUBERNETES = "kubernetes"  # K8s clusters
    NETWORK = "network"  # Nmap, network scanning
    AGENT = "agent"  # Osquery, Wazuh agents
    CMDB = "cmdb"  # ServiceNow, Jira Assets
    IAAS = "iaas"  # VM inventory
    SBOM = "sbom"  # Software Bill of Materials


class AssetType(Enum):
    """Standard asset types."""
    SERVER = "server"
    CONTAINER = "container"
    POD = "pod"
    VM = "vm"
    LAMBDA = "lambda"
    DATABASE = "database"
    LOAD_BALANCER = "load_balancer"
    STORAGE = "storage"
    NETWORK_DEVICE = "network_device"
    APPLICATION = "application"


@dataclass
class DiscoveredVulnerability:
    """Vulnerability found during asset scanning."""
    identifier: str  # CVE-2024-XXXXX
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    cvss_score: Optional[float] = None
    affected_component: Optional[str] = None
    fixed_version: Optional[str] = None
    description: Optional[str] = None
    source_scanner: Optional[str] = None


@dataclass
class DiscoveredAsset:
    """
    Normalized asset data from any scanner.
    
    This is the canonical format all scanners must produce.
    """
    # Required fields
    identifier: str  # Unique ID from source (hostname, instance-id, etc.)
    name: str  # Human-friendly name
    type: str  # AssetType value
    scanner_type: str  # ScannerType value
    source: str  # Scanner name (trivy, aws, kubescape, etc.)
    
    # Optional classification
    platform: Optional[str] = None  # aws, azure, gcp, k8s, on-prem
    environment: Optional[str] = None  # production, staging, development
    
    # Location and ownership
    location: Optional[str] = None  # region, datacenter, cluster
    owner_team: Optional[str] = None
    owner_email: Optional[str] = None
    business_unit: Optional[str] = None
    
    # Criticality (1-5 scale, 5 = most critical)
    criticality: int = 3
    exposure: str = "ISOLATED"  # INTERNET, INTRANET, ISOLATED
    
    # Technical details
    os_family: Optional[str] = None  # linux, windows, macos
    os_version: Optional[str] = None
    ip_addresses: List[str] = field(default_factory=list)
    fqdn: Optional[str] = None
    
    # Cloud metadata
    cloud_account_id: Optional[str] = None
    cloud_region: Optional[str] = None
    cloud_instance_type: Optional[str] = None
    cloud_tags: Dict[str, str] = field(default_factory=dict)
    
    # Software inventory
    installed_packages: List[Dict[str, str]] = field(default_factory=list)
    running_services: List[str] = field(default_factory=list)
    open_ports: List[int] = field(default_factory=list)
    
    # Compliance
    compliance_frameworks: List[str] = field(default_factory=list)
    compensating_controls: List[str] = field(default_factory=list)
    
    # Vulnerabilities (if scanner found any)
    vulnerabilities: List[DiscoveredVulnerability] = field(default_factory=list)
    
    # Metadata
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    last_scanned_at: datetime = field(default_factory=datetime.utcnow)
    
    # Integration references
    cmdb_id: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Original scanner output
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "identifier": self.identifier,
            "name": self.name,
            "type": self.type,
            "platform": self.platform,
            "environment": self.environment,
            "location": self.location,
            "owner_team": self.owner_team,
            "owner_email": self.owner_email,
            "business_unit": self.business_unit,
            "criticality": self.criticality,
            "exposure": self.exposure,
            "os_family": self.os_family,
            "os_version": self.os_version,
            "ip_addresses": self.ip_addresses,
            "fqdn": self.fqdn,
            "cloud_account_id": self.cloud_account_id,
            "cloud_region": self.cloud_region,
            "cloud_instance_type": self.cloud_instance_type,
            "cloud_tags": self.cloud_tags,
            "installed_packages": self.installed_packages,
            "running_services": self.running_services,
            "open_ports": self.open_ports,
            "compliance_frameworks": self.compliance_frameworks,
            "compensating_controls": self.compensating_controls,
            "last_scanned_at": self.last_scanned_at,
            "cmdb_id": self.cmdb_id,
        }


@dataclass
class ScanResult:
    """Result of a discovery scan."""
    scanner_name: str
    scanner_type: ScannerType
    assets: List[DiscoveredAsset]
    scan_duration_seconds: float
    scan_timestamp: datetime = field(default_factory=datetime.utcnow)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """Check if scan completed without critical errors."""
        return len(self.errors) == 0
    
    @property
    def asset_count(self) -> int:
        """Number of assets discovered."""
        return len(self.assets)


class BaseScanner(ABC):
    """
    Abstract base class for all asset discovery scanners.
    
    Implement this interface to add new discovery sources.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scanner with optional configuration.
        
        Args:
            config: Scanner-specific configuration (credentials, endpoints, etc.)
        """
        self.config = config or {}
        self.scanner_type: ScannerType = ScannerType.CLOUD  # Override in subclass
        self.scanner_name: str = "base"  # Override in subclass
    
    @abstractmethod
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Execute discovery scan.
        
        Args:
            target: Optional target specifier (region, cluster name, IP range, etc.)
            **kwargs: Scanner-specific arguments
            
        Returns:
            ScanResult with discovered assets
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if scanner can connect to the target system.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_config(self) -> List[str]:
        """
        Get list of required configuration keys.
        
        Returns:
            List of config keys needed for this scanner
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if config is valid, False otherwise
        """
        required = self.get_required_config()
        return all(key in self.config for key in required)
