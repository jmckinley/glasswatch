"""
Kubescape integration for Kubernetes security posture scanning
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
import json

from . import ScannerInterface, ScanResult


class KubescapeScanner(ScannerInterface):
    """Kubescape CNCF security scanner"""
    
    def __init__(self):
        self.scanner_name = "kubescape"
        self.scan_type = "kubernetes"
        self.frameworks = ["nsa", "mitre", "cis-v1.23", "pci-dss", "hipaa", "sox"]
    
    def is_available(self) -> bool:
        """Check if kubescape is installed"""
        try:
            import subprocess
            result = subprocess.run(
                ["kubescape", "version"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    async def scan(self, target: str = "cluster", options: Dict[str, Any] = None) -> ScanResult:
        """Scan Kubernetes cluster against security frameworks"""
        started_at = datetime.now(timezone.utc)
        options = options or {}
        
        # Get framework to scan
        framework = options.get("framework", "nsa")
        if framework not in self.frameworks:
            framework = "nsa"
        
        # Build command
        cmd = [
            "kubescape", "scan", "framework", framework,
            "--format", "json",
            "--output", "/tmp/kubescape-result.json"
        ]
        
        # Add namespace filter if specified
        if options.get("namespace"):
            cmd.extend(["--namespace", options["namespace"]])
        
        # Add exclude namespaces
        if options.get("exclude_namespaces"):
            cmd.extend(["--exclude-namespaces", ",".join(options["exclude_namespaces"])])
        
        try:
            stdout, stderr, returncode = await self._run_command(cmd)
            
            # Read result from file (kubescape outputs to file)
            try:
                with open("/tmp/kubescape-result.json", "r") as f:
                    results = json.load(f)
            except:
                return ScanResult(
                    scanner=self.scanner_name,
                    target=target,
                    scan_type=self.scan_type,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    success=False,
                    error="Failed to read scan results"
                )
            
            # Extract findings
            findings = []
            summary = results.get("summaryDetails", {})
            
            # Process failed controls
            for control in results.get("results", []):
                if control.get("status", {}).get("status") == "failed":
                    findings.append({
                        "control_id": control.get("controlID"),
                        "name": control.get("name"),
                        "severity": self._map_severity(control.get("scoreFactor", 1)),
                        "description": control.get("description"),
                        "remediation": control.get("remediation"),
                        "failed_resources": control.get("resourcesLen", {}).get("failedResources", 0),
                        "category": control.get("category", {}).get("name", "Unknown")
                    })
            
            # Calculate compliance score
            total_controls = summary.get("controls", {}).get("totalControls", 0)
            passed_controls = summary.get("controls", {}).get("passedControls", 0)
            compliance_score = (passed_controls / total_controls * 100) if total_controls > 0 else 0
            
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                success=True,
                findings=findings,
                metadata={
                    "framework": framework,
                    "compliance_score": round(compliance_score, 2),
                    "total_controls": total_controls,
                    "passed_controls": passed_controls,
                    "failed_controls": summary.get("controls", {}).get("failedControls", 0),
                    "resources_scanned": summary.get("resources", {}).get("totalResources", 0)
                }
            )
            
        except Exception as e:
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                success=False,
                error=str(e)
            )
    
    def _map_severity(self, score_factor: float) -> str:
        """Map Kubescape score factor to severity"""
        if score_factor >= 9:
            return "CRITICAL"
        elif score_factor >= 7:
            return "HIGH"
        elif score_factor >= 4:
            return "MEDIUM"
        else:
            return "LOW"