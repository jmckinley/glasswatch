# Glasswatch — Scanning & Inventory Integrations

Glasswatch integrates with external scanners and inventory systems to ingest vulnerability and asset data. The three primary scanner integrations (Tenable, Qualys, Rapid7) are production-ready via inbound webhooks. Additional integrations below are planned.

> **Testing without real credentials?** Simulators are available for Tenable, Qualys, and Rapid7 (and 8 additional systems). Set `SIMULATOR_MODE=true` in your environment to enable mock API servers on port 8099. See [docs/SIMULATORS.md](SIMULATORS.md) for full usage.

---

Based on industry best practices and popular open-source tools, here are the scanning and inventory capabilities integrated or planned:

## 1. Container & Image Scanning

### Trivy (Priority: HIGH)
- **What**: All-in-one vulnerability scanner
- **Why**: Most popular, supports containers, filesystems, git repos, cloud resources
- **Integration**: 
  ```python
  # Run as subprocess or use REST API
  trivy image --format json <image:tag>
  trivy k8s --format json cluster
  ```
- **Data we get**: CVEs, misconfigurations, secrets, licenses

### Grype (Anchore)
- **What**: Fast vulnerability scanner focused on containers
- **Why**: Good alternative/complement to Trivy
- **Integration**: CLI or REST API
- **Data we get**: CVE matches with detailed metadata

## 2. Kubernetes Security Posture

### Kubescape
- **What**: CNCF-backed K8s security scanner
- **Why**: Comprehensive cluster security assessment
- **Integration**: 
  ```python
  kubescape scan framework nsa --format json
  kubescape scan framework cis-v1.23 --format json
  ```
- **Data we get**: Security posture score, failed controls, remediation steps

### kube-bench
- **What**: CIS Kubernetes Benchmark checker
- **Why**: Industry standard compliance checking
- **Integration**: Run as Job in cluster
- **Data we get**: CIS compliance status per component

## 3. Infrastructure as Code (IaC) Scanning

### Checkov
- **What**: Multi-cloud IaC scanner
- **Why**: Catches misconfigurations before deployment
- **Integration**: Python library or CLI
- **Supports**: Terraform, CloudFormation, K8s manifests, Helm
- **Data we get**: Policy violations, security best practice violations

### Terrascan
- **What**: IaC scanner with 500+ policies
- **Why**: Good policy coverage, admission webhook support
- **Integration**: REST API or admission controller
- **Data we get**: Policy violations with severity

## 4. Cloud Asset Inventory

### CloudQuery
- **What**: Open-source cloud asset inventory
- **Why**: Unified view across AWS, Azure, GCP, K8s
- **Integration**: PostgreSQL-compatible output
- **Data we get**: Complete asset inventory with relationships

### Prowler
- **What**: Multi-cloud security scanner
- **Why**: Comprehensive AWS/Azure/GCP/K8s checks
- **Integration**: CLI with JSON output
- **Data we get**: Security findings, compliance status

## 5. Runtime Security

### Falco
- **What**: Runtime security monitoring
- **Why**: Detect anomalous behavior in production
- **Integration**: gRPC API or webhook
- **Data we get**: Security events, behavioral anomalies

## 6. Software Bill of Materials (SBOM)

### Syft
- **What**: SBOM generator
- **Why**: Complete package inventory for containers
- **Integration**: CLI or library
- **Data we get**: Full dependency tree, versions, licenses

## 7. Network Security

### Cilium/Hubble
- **What**: eBPF-based network observability
- **Why**: Deep network visibility and security
- **Integration**: Hubble API
- **Data we get**: Network flows, DNS queries, HTTP traffic

## Integration Architecture

```python
# Scanner abstraction layer
class ScannerInterface:
    async def scan(self, target: str) -> ScanResult:
        pass

class TrivyScanner(ScannerInterface):
    async def scan(self, target: str) -> ScanResult:
        # Execute trivy, parse JSON, normalize results
        pass

class AssetDiscovery:
    def __init__(self):
        self.scanners = {
            "containers": TrivyScanner(),
            "kubernetes": KubescapeScanner(),
            "cloud": ProwlerScanner(),
            "iac": CheckovScanner(),
        }
    
    async def discover_all(self, tenant_id: str):
        # Parallel scanning across all environments
        results = await asyncio.gather(*[
            scanner.scan(target) 
            for scanner in self.scanners.values()
        ])
        return self.normalize_results(results)
```

## Priority Implementation Order

1. **Phase 1 - Core Scanning**
   - Trivy for container/image scanning
   - Kubescape for K8s posture
   - Basic AWS/Azure/GCP API inventory

2. **Phase 2 - Advanced Discovery**
   - CloudQuery for unified inventory
   - Checkov for IaC scanning
   - Syft for SBOM generation

3. **Phase 3 - Runtime & Network**
   - Falco integration
   - Cilium/Hubble for network visibility
   - Custom Snapper runtime integration

## Data Normalization

All scanners output different formats. We need a unified schema:

```python
class UnifiedVulnerability:
    id: str  # CVE-2024-XXXXX
    severity: str  # CRITICAL|HIGH|MEDIUM|LOW
    cvss_score: float
    epss_score: Optional[float]
    affected_component: str
    fixed_version: Optional[str]
    exploit_available: bool
    in_the_wild: bool
    patch_available: bool
    source_scanner: str  # trivy|grype|etc
    discovered_at: datetime
    
class UnifiedAsset:
    id: str
    type: str  # container|vm|k8s-pod|lambda|etc
    name: str
    environment: str  # prod|staging|dev
    cloud_provider: Optional[str]
    region: Optional[str]
    tags: Dict[str, str]
    vulnerabilities: List[UnifiedVulnerability]
    last_scanned: datetime
```

## Production Scanner Integrations (Current)

These integrations are fully implemented and production-ready:

| Scanner | Method | Webhook Path |
|---|---|---|
| Tenable (Nessus / Tenable.io) | Inbound webhook | `POST /api/v1/webhooks/scanner/tenable` |
| Qualys | Inbound webhook | `POST /api/v1/webhooks/scanner/qualys` |
| Rapid7 InsightVM | Inbound webhook | `POST /api/v1/webhooks/scanner/rapid7` |
| Any scanner | CSV import | **Vulnerabilities → Import** in the UI |

All webhooks require `Authorization: Bearer <api-key>` header. Glasswatch normalizes incoming data to its unified vulnerability and asset schema.

**CSV import** supports custom column mappings for scanners not listed above. Scanner-specific column presets are available for Tenable, Qualys, and Rapid7.

---

## External APIs Integrated (Current)

1. **NVD API** — CVE details and enrichment
2. **EPSS API** — Exploit prediction scores (daily refresh)
3. **CISA KEV** — Known exploited vulnerabilities catalog
4. **GitHub Security Advisories** — OSS vulnerability data
5. **Cloud provider APIs** — AWS Inspector, Azure Security Center, GCP Security Command Center

---

## Planned Scanner Integrations

These tools are on the roadmap but not yet in production: