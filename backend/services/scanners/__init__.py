"""
Scanner interfaces for PatchGuide.ai

Provides a unified interface for various security scanning tools.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import asyncio
import subprocess
import json


class ScanResult(BaseModel):
    """Unified scan result format"""
    scanner: str
    target: str
    scan_type: str  # container|kubernetes|cloud|iac|sbom
    started_at: datetime
    completed_at: datetime
    success: bool
    error: Optional[str] = None
    findings: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class ScannerInterface(ABC):
    """Base scanner interface"""
    
    @abstractmethod
    async def scan(self, target: str, options: Dict[str, Any] = None) -> ScanResult:
        """Execute scan on target"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if scanner is installed/accessible"""
        pass
    
    async def _run_command(self, cmd: List[str], timeout: int = 300) -> tuple[str, str, int]:
        """Run external command with timeout"""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=timeout
            )
            
            return (
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else "",
                proc.returncode or 0
            )
        except asyncio.TimeoutError:
            if proc:
                proc.kill()
            raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        except Exception as e:
            raise RuntimeError(f"Command failed: {str(e)}")


class TrivyScanner(ScannerInterface):
    """Trivy vulnerability scanner integration"""
    
    def __init__(self):
        self.scanner_name = "trivy"
        self.scan_type = "container"
    
    def is_available(self) -> bool:
        """Check if trivy is installed"""
        try:
            result = subprocess.run(
                ["trivy", "--version"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    async def scan(self, target: str, options: Dict[str, Any] = None) -> ScanResult:
        """Scan container image or kubernetes cluster"""
        started_at = datetime.now(timezone.utc)
        options = options or {}
        
        # Build command
        cmd = ["trivy"]
        
        # Determine scan type
        if options.get("scan_type") == "kubernetes":
            cmd.extend(["k8s", "--format", "json"])
            if options.get("namespace"):
                cmd.extend(["--namespace", options["namespace"]])
            cmd.append("cluster")
            scan_type = "kubernetes"
        else:
            # Default to image scan
            cmd.extend(["image", "--format", "json"])
            if options.get("severity"):
                cmd.extend(["--severity", options["severity"]])
            cmd.append(target)
            scan_type = "container"
        
        try:
            stdout, stderr, returncode = await self._run_command(cmd)
            
            if returncode != 0:
                return ScanResult(
                    scanner=self.scanner_name,
                    target=target,
                    scan_type=scan_type,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    success=False,
                    error=stderr or "Scan failed"
                )
            
            # Parse JSON output
            results = json.loads(stdout)
            
            # Normalize findings
            findings = []
            if scan_type == "container":
                for result in results.get("Results", []):
                    for vuln in result.get("Vulnerabilities", []):
                        findings.append({
                            "id": vuln.get("VulnerabilityID"),
                            "severity": vuln.get("Severity", "UNKNOWN"),
                            "package": vuln.get("PkgName"),
                            "version": vuln.get("InstalledVersion"),
                            "fixed_version": vuln.get("FixedVersion"),
                            "title": vuln.get("Title"),
                            "description": vuln.get("Description"),
                            "cvss": vuln.get("CVSS"),
                            "references": vuln.get("References", [])
                        })
            
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=scan_type,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                success=True,
                findings=findings,
                metadata={
                    "trivy_version": results.get("Version"),
                    "schema_version": results.get("SchemaVersion")
                }
            )
            
        except Exception as e:
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=scan_type,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                success=False,
                error=str(e)
            )