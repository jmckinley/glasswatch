"""
Nmap network scanner integration for asset discovery.

Discovers hosts, open ports, services, and OS detection on the network.
"""
import asyncio
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
import time
import tempfile
import os

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class NmapScanner(BaseScanner):
    """
    Nmap network discovery scanner.
    
    Requires: nmap binary in PATH or configured path
    Discovers: Network hosts, services, OS, open ports
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.NETWORK
        self.scanner_name = "nmap"
        self.nmap_path = config.get("nmap_path", "nmap") if config else "nmap"
        self.scan_options = config.get("scan_options", "-sV -O") if config else "-sV -O"
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Scan network for assets.
        
        Args:
            target: IP address, CIDR range, or hostname to scan
            **kwargs: scan_type (quick, normal, full), ports, etc.
            
        Returns:
            ScanResult with discovered network assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        if not target:
            errors.append("Nmap requires a target (IP, CIDR, or hostname)")
            return ScanResult(
                scanner_name=self.scanner_name,
                scanner_type=self.scanner_type,
                assets=[],
                scan_duration_seconds=0,
                errors=errors
            )
        
        try:
            scan_result = await self._run_nmap(target, **kwargs)
            assets = self._parse_nmap_xml(scan_result)
        except Exception as e:
            errors.append(f"Nmap scan failed: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "target": target,
                "scan_options": self.scan_options
            }
        )
    
    async def _run_nmap(self, target: str, **kwargs) -> str:
        """Execute nmap and return XML output."""
        # Create temp file for XML output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            xml_file = f.name
        
        try:
            # Build nmap command
            cmd = [
                self.nmap_path,
                target,
                "-oX", xml_file,  # XML output
            ]
            
            # Add scan options
            scan_type = kwargs.get("scan_type", "normal")
            if scan_type == "quick":
                cmd.extend(["-F"])  # Fast scan (100 common ports)
            elif scan_type == "full":
                cmd.extend(["-p-"])  # All ports
            else:
                # Normal scan with version detection and OS detection
                cmd.extend(self.scan_options.split())
            
            # Add custom ports if specified
            if "ports" in kwargs:
                cmd.extend(["-p", kwargs["ports"]])
            
            # Run nmap
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"Nmap failed: {stderr.decode()}")
            
            # Read XML output
            with open(xml_file, 'r') as f:
                xml_content = f.read()
            
            return xml_content
        
        finally:
            # Clean up temp file
            if os.path.exists(xml_file):
                os.unlink(xml_file)
    
    def _parse_nmap_xml(self, xml_content: str) -> List[DiscoveredAsset]:
        """Parse nmap XML output into assets."""
        assets = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for host in root.findall('host'):
                # Check if host is up
                status = host.find('status')
                if status is None or status.get('state') != 'up':
                    continue
                
                # Get IP address
                address_elem = host.find('address')
                if address_elem is None:
                    continue
                
                ip_address = address_elem.get('addr')
                
                # Get hostname
                hostname = None
                hostnames = host.find('hostnames')
                if hostnames is not None:
                    hostname_elem = hostnames.find('hostname')
                    if hostname_elem is not None:
                        hostname = hostname_elem.get('name')
                
                # Get OS detection
                os_family = None
                os_version = None
                os_elem = host.find('os')
                if os_elem is not None:
                    osmatch = os_elem.find('osmatch')
                    if osmatch is not None:
                        os_name = osmatch.get('name', '')
                        os_family = self._detect_os_family(os_name)
                        os_version = os_name
                
                # Get open ports and services
                open_ports = []
                running_services = []
                ports_elem = host.find('ports')
                if ports_elem is not None:
                    for port in ports_elem.findall('port'):
                        state = port.find('state')
                        if state is not None and state.get('state') == 'open':
                            port_num = int(port.get('portid'))
                            open_ports.append(port_num)
                            
                            # Get service info
                            service = port.find('service')
                            if service is not None:
                                service_name = service.get('name')
                                service_product = service.get('product')
                                service_version = service.get('version')
                                
                                if service_product and service_version:
                                    running_services.append(f"{service_product} {service_version}")
                                elif service_name:
                                    running_services.append(service_name)
                
                # Determine exposure based on open ports
                exposure = "INTRANET"
                internet_ports = [80, 443, 8080, 8443]
                if any(port in internet_ports for port in open_ports):
                    exposure = "INTERNET"
                
                # Determine criticality (heuristic based on services)
                criticality = 3
                critical_services = ['ssh', 'rdp', 'database', 'sql']
                if any(svc in ' '.join(running_services).lower() for svc in critical_services):
                    criticality = 4
                
                asset = DiscoveredAsset(
                    identifier=ip_address,
                    name=hostname or ip_address,
                    type=AssetType.SERVER.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="network",
                    criticality=criticality,
                    exposure=exposure,
                    os_family=os_family,
                    os_version=os_version,
                    ip_addresses=[ip_address],
                    fqdn=hostname,
                    open_ports=open_ports,
                    running_services=running_services,
                    raw_data={
                        "ip": ip_address,
                        "hostname": hostname,
                        "open_ports": open_ports
                    }
                )
                
                assets.append(asset)
        
        except ET.ParseError as e:
            raise RuntimeError(f"Failed to parse nmap XML: {str(e)}")
        
        return assets
    
    def _detect_os_family(self, os_name: str) -> Optional[str]:
        """Detect OS family from nmap OS detection."""
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
        """Test if nmap is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.nmap_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Nmap requires no configuration (uses local binary)."""
        return []  # Optional: nmap_path, scan_options
