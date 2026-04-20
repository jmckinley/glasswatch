"""
Trivy scanner integration for container and Kubernetes vulnerability scanning.

Trivy is the industry standard for container security scanning.
Supports: Docker images, Kubernetes clusters, filesystems, git repos.
"""
import json
import asyncio
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset, DiscoveredVulnerability,
    ScannerType, AssetType
)


class TrivyScanner(BaseScanner):
    """
    Trivy container and Kubernetes vulnerability scanner.
    
    Requires trivy binary in PATH or configured path.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CONTAINER
        self.scanner_name = "trivy"
        self.trivy_path = config.get("trivy_path", "trivy") if config else "trivy"
    
    async def scan(self, target: Optional[str] = None, scan_type: str = "image", **kwargs) -> ScanResult:
        """
        Scan container images or Kubernetes clusters.
        
        Args:
            target: Image name (for image scan) or cluster context (for k8s scan)
            scan_type: "image", "filesystem", "k8s"
            **kwargs: Additional trivy options
            
        Returns:
            ScanResult with discovered vulnerabilities
        """
        start_time = time.time()
        assets = []
        errors = []
        
        try:
            if scan_type == "image":
                assets = await self._scan_image(target, errors)
            elif scan_type == "k8s":
                assets = await self._scan_k8s_cluster(target, errors)
            elif scan_type == "filesystem":
                assets = await self._scan_filesystem(target, errors)
            else:
                errors.append(f"Unknown scan type: {scan_type}")
        
        except Exception as e:
            errors.append(f"Trivy scan failed: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "scan_type": scan_type,
                "target": target,
            }
        )
    
    async def _scan_image(self, image_name: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Scan a container image."""
        cmd = [
            self.trivy_path,
            "image",
            "--format", "json",
            "--quiet",
            image_name
        ]
        
        try:
            result = await self._run_command(cmd)
            return self._parse_image_results(result, image_name)
        except Exception as e:
            errors.append(f"Image scan failed for {image_name}: {str(e)}")
            return []
    
    async def _scan_k8s_cluster(self, context: Optional[str], errors: List[str]) -> List[DiscoveredAsset]:
        """Scan Kubernetes cluster for vulnerabilities."""
        cmd = [
            self.trivy_path,
            "k8s",
            "--format", "json",
            "--report", "all",
        ]
        
        if context:
            cmd.extend(["--context", context])
        
        try:
            result = await self._run_command(cmd)
            return self._parse_k8s_results(result)
        except Exception as e:
            errors.append(f"K8s scan failed: {str(e)}")
            return []
    
    async def _scan_filesystem(self, path: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Scan filesystem for vulnerabilities."""
        cmd = [
            self.trivy_path,
            "fs",
            "--format", "json",
            "--quiet",
            path
        ]
        
        try:
            result = await self._run_command(cmd)
            return self._parse_filesystem_results(result, path)
        except Exception as e:
            errors.append(f"Filesystem scan failed for {path}: {str(e)}")
            return []
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute trivy command asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Trivy failed: {stderr.decode()}")
        
        return json.loads(stdout.decode())
    
    def _parse_image_results(self, results: Dict[str, Any], image_name: str) -> List[DiscoveredAsset]:
        """Parse trivy image scan JSON output."""
        assets = []
        
        # Trivy returns results for each "Result" (layer/target)
        for result in results.get("Results", []):
            target = result.get("Target", image_name)
            vulns = []
            packages = []
            
            # Extract vulnerabilities
            for vuln_data in result.get("Vulnerabilities", []):
                vuln = DiscoveredVulnerability(
                    identifier=vuln_data.get("VulnerabilityID"),
                    severity=vuln_data.get("Severity", "UNKNOWN"),
                    cvss_score=self._extract_cvss(vuln_data),
                    affected_component=vuln_data.get("PkgName"),
                    fixed_version=vuln_data.get("FixedVersion"),
                    description=vuln_data.get("Description"),
                    source_scanner="trivy"
                )
                vulns.append(vuln)
            
            # Extract installed packages
            for vuln_data in result.get("Vulnerabilities", []):
                pkg_name = vuln_data.get("PkgName")
                pkg_version = vuln_data.get("InstalledVersion")
                if pkg_name and pkg_version:
                    packages.append({
                        "name": pkg_name,
                        "version": pkg_version
                    })
            
            # Deduplicate packages
            packages = [dict(t) for t in {tuple(d.items()) for d in packages}]
            
            # Determine exposure based on image name (heuristic)
            exposure = "INTERNET" if any(
                keyword in image_name.lower() 
                for keyword in ["web", "api", "frontend", "nginx", "httpd"]
            ) else "INTRANET"
            
            asset = DiscoveredAsset(
                identifier=f"container:{image_name}",
                name=image_name,
                type=AssetType.CONTAINER.value,
                scanner_type=self.scanner_type.value,
                source=self.scanner_name,
                platform="container",
                exposure=exposure,
                installed_packages=packages,
                vulnerabilities=vulns,
                raw_data=result
            )
            
            assets.append(asset)
        
        return assets
    
    def _parse_k8s_results(self, results: Dict[str, Any]) -> List[DiscoveredAsset]:
        """Parse trivy k8s scan JSON output."""
        assets = []
        
        # K8s scan returns resources with vulnerabilities
        for resource in results.get("Resources", []):
            namespace = resource.get("Namespace", "default")
            kind = resource.get("Kind", "")
            name = resource.get("Name", "")
            
            vulns = []
            for result in resource.get("Results", []):
                for vuln_data in result.get("Vulnerabilities", []):
                    vuln = DiscoveredVulnerability(
                        identifier=vuln_data.get("VulnerabilityID"),
                        severity=vuln_data.get("Severity", "UNKNOWN"),
                        cvss_score=self._extract_cvss(vuln_data),
                        affected_component=vuln_data.get("PkgName"),
                        fixed_version=vuln_data.get("FixedVersion"),
                        description=vuln_data.get("Description"),
                        source_scanner="trivy"
                    )
                    vulns.append(vuln)
            
            # Determine asset type from K8s kind
            asset_type_map = {
                "Pod": AssetType.POD,
                "Deployment": AssetType.APPLICATION,
                "StatefulSet": AssetType.APPLICATION,
                "DaemonSet": AssetType.APPLICATION,
            }
            asset_type = asset_type_map.get(kind, AssetType.POD).value
            
            # Determine exposure based on service type (if available)
            exposure = "ISOLATED"  # Default for k8s resources
            
            asset = DiscoveredAsset(
                identifier=f"k8s:{namespace}/{kind}/{name}",
                name=f"{namespace}/{name}",
                type=asset_type,
                scanner_type=ScannerType.KUBERNETES.value,
                source=self.scanner_name,
                platform="kubernetes",
                location=namespace,
                exposure=exposure,
                cloud_tags={"namespace": namespace, "kind": kind},
                vulnerabilities=vulns,
                raw_data=resource
            )
            
            assets.append(asset)
        
        return assets
    
    def _parse_filesystem_results(self, results: Dict[str, Any], path: str) -> List[DiscoveredAsset]:
        """Parse trivy filesystem scan JSON output."""
        # Similar to image scan, but for filesystem
        return self._parse_image_results(results, f"filesystem:{path}")
    
    def _extract_cvss(self, vuln_data: Dict[str, Any]) -> Optional[float]:
        """Extract CVSS score from vulnerability data."""
        # Trivy provides CVSS in multiple formats
        if "CVSS" in vuln_data:
            cvss_data = vuln_data["CVSS"]
            # Try different CVSS versions
            for version in ["nvd", "redhat", "vendor"]:
                if version in cvss_data:
                    score = cvss_data[version].get("V3Score") or cvss_data[version].get("V2Score")
                    if score:
                        return float(score)
        
        return None
    
    async def test_connection(self) -> bool:
        """Test if trivy is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.trivy_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """Trivy requires no configuration (uses local binary)."""
        return []
