"""
Kubescape scanner integration for Kubernetes security posture assessment.

Kubescape is a CNCF-backed tool for K8s security scanning.
Scans against NSA, CIS, MITRE ATT&CK frameworks.
"""
import json
import asyncio
from typing import Optional, List, Dict, Any
import time

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset, DiscoveredVulnerability,
    ScannerType, AssetType
)


class KubescapeScanner(BaseScanner):
    """
    Kubescape Kubernetes security scanner.
    
    Requires kubescape binary in PATH or configured path.
    Scans K8s clusters for security misconfigurations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.KUBERNETES
        self.scanner_name = "kubescape"
        self.kubescape_path = config.get("kubescape_path", "kubescape") if config else "kubescape"
        self.frameworks = config.get("frameworks", ["nsa", "mitre", "cis-v1.23"]) if config else ["nsa", "mitre", "cis-v1.23"]
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Scan Kubernetes cluster for security posture.
        
        Args:
            target: Optional kubeconfig context
            **kwargs: framework (override default frameworks)
            
        Returns:
            ScanResult with K8s security findings
        """
        start_time = time.time()
        assets = []
        errors = []
        
        frameworks = kwargs.get("frameworks", self.frameworks)
        
        for framework in frameworks:
            try:
                framework_assets = await self._scan_framework(framework, target, errors)
                assets.extend(framework_assets)
            except Exception as e:
                errors.append(f"Kubescape scan failed for framework {framework}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "frameworks": frameworks,
                "context": target
            }
        )
    
    async def _scan_framework(
        self,
        framework: str,
        context: Optional[str],
        errors: List[str]
    ) -> List[DiscoveredAsset]:
        """Scan a specific security framework."""
        cmd = [
            self.kubescape_path,
            "scan",
            "framework",
            framework,
            "--format", "json",
            "--verbose"
        ]
        
        if context:
            cmd.extend(["--kubeconfig-context", context])
        
        try:
            result = await self._run_command(cmd)
            return self._parse_results(result, framework)
        except Exception as e:
            errors.append(f"Framework scan failed for {framework}: {str(e)}")
            return []
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute kubescape command asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Kubescape failed: {stderr.decode()}")
        
        return json.loads(stdout.decode())
    
    def _parse_results(self, results: Dict[str, Any], framework: str) -> List[DiscoveredAsset]:
        """Parse kubescape JSON output."""
        assets = []
        
        # Kubescape returns resources with control failures
        for resource in results.get("resources", []):
            resource_kind = resource.get("kind", "")
            resource_name = resource.get("name", "")
            namespace = resource.get("namespace", "default")
            
            # Extract failed controls as vulnerabilities
            vulns = []
            for control in resource.get("controlsFailures", []):
                control_id = control.get("controlID", "")
                control_name = control.get("name", "")
                severity = control.get("severity", "MEDIUM")
                
                vuln = DiscoveredVulnerability(
                    identifier=control_id,
                    severity=self._map_severity(severity),
                    cvss_score=self._severity_to_cvss(severity),
                    affected_component=f"{resource_kind}/{resource_name}",
                    description=control_name,
                    source_scanner="kubescape"
                )
                vulns.append(vuln)
            
            if not vulns:
                continue  # Skip resources with no findings
            
            # Map K8s kind to asset type
            asset_type_map = {
                "Pod": AssetType.POD,
                "Deployment": AssetType.APPLICATION,
                "StatefulSet": AssetType.APPLICATION,
                "DaemonSet": AssetType.APPLICATION,
                "Service": AssetType.APPLICATION,
                "Ingress": AssetType.LOAD_BALANCER,
            }
            asset_type = asset_type_map.get(resource_kind, AssetType.POD).value
            
            asset = DiscoveredAsset(
                identifier=f"k8s:{namespace}/{resource_kind}/{resource_name}",
                name=f"{namespace}/{resource_name}",
                type=asset_type,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="kubernetes",
                location=namespace,
                criticality=self._calculate_criticality(vulns),
                exposure="ISOLATED",
                cloud_tags={
                    "namespace": namespace,
                    "kind": resource_kind,
                    "framework": framework
                },
                vulnerabilities=vulns,
                raw_data=resource
            )
            
            assets.append(asset)
        
        return assets
    
    def _map_severity(self, kubescape_severity: str) -> str:
        """Map Kubescape severity to standard severity."""
        severity_map = {
            "Critical": "CRITICAL",
            "High": "HIGH",
            "Medium": "MEDIUM",
            "Low": "LOW"
        }
        return severity_map.get(kubescape_severity, "MEDIUM")
    
    def _severity_to_cvss(self, severity: str) -> float:
        """Convert severity to approximate CVSS score."""
        severity_scores = {
            "Critical": 9.0,
            "High": 7.5,
            "Medium": 5.0,
            "Low": 3.0
        }
        return severity_scores.get(severity, 5.0)
    
    def _calculate_criticality(self, vulns: List[DiscoveredVulnerability]) -> int:
        """Calculate asset criticality based on vulnerabilities."""
        if not vulns:
            return 3
        
        # Count by severity
        critical_count = sum(1 for v in vulns if v.severity == "CRITICAL")
        high_count = sum(1 for v in vulns if v.severity == "HIGH")
        
        if critical_count > 0:
            return 5
        elif high_count >= 3:
            return 4
        elif high_count > 0:
            return 3
        else:
            return 2
    
    async def test_connection(self) -> bool:
        """Test if kubescape is available and can connect to cluster."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.kubescape_path,
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Kubescape requires kubeconfig (defaults to ~/.kube/config)."""
        return []  # Optional: kubescape_path, frameworks
