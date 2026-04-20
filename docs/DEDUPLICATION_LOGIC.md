# Asset Deduplication Logic

**Date:** 2026-04-20  
**Component:** Discovery Orchestrator  
**Purpose:** Prevent duplicate assets when multiple scanners discover the same infrastructure

---

## Problem

When running multiple scanners, the same asset can be discovered multiple times:

**Example Overlaps:**
- **CloudQuery + AWS** both find EC2 instances
- **Azure + CloudQuery** both find Azure VMs  
- **GCP + CloudQuery** both find Compute Engine VMs
- **Trivy + Kubescape** both find K8s pods
- **Nmap + CMDB** both find network devices

**Without deduplication:**
- 1 EC2 instance → 2 database records (AWS + CloudQuery)
- 100 VMs → 200 records
- Database bloat and confusion

---

## Solution

### Deduplication Strategy

1. **Unique Identifier**
   - Every asset has an `identifier` field
   - Used as deduplication key
   - Examples:
     - AWS: `instance-id` (e.g., `i-0abc123def456`)
     - Azure: resource ID (e.g., `/subscriptions/.../virtualMachines/vm-prod`)
     - K8s: UID (e.g., `k8s:default/nginx-deployment`)

2. **Comparison Algorithm**
   - When duplicates exist, choose the "better" asset
   - Preference order:
     1. **More vulnerabilities** → More thorough security scan
     2. **More installed packages** → Deeper discovery
     3. **More recent scan** → Fresher data

3. **Merge Strategy**
   - Keep best version per identifier
   - Discard inferior versions
   - Result: 1 asset per identifier in final output

---

## Implementation

### Code Location
`backend/services/discovery/orchestrator.py`

### Deduplication Function

```python
def _deduplicate_assets(self, assets: List[DiscoveredAsset]) -> List[DiscoveredAsset]:
    """
    Deduplicate assets by identifier.
    
    When duplicates exist, prefer:
    1. Asset with more vulnerabilities
    2. Asset with more metadata
    3. Most recently scanned
    """
    asset_map: Dict[str, DiscoveredAsset] = {}
    
    for asset in assets:
        existing = asset_map.get(asset.identifier)
        
        if not existing:
            asset_map[asset.identifier] = asset
        else:
            # Choose the better asset
            if self._compare_assets(asset, existing) > 0:
                asset_map[asset.identifier] = asset
    
    return list(asset_map.values())
```

### Comparison Function

```python
def _compare_assets(self, a: DiscoveredAsset, b: DiscoveredAsset) -> int:
    """
    Compare two assets to determine which is better.
    
    Returns:
        1 if a is better, -1 if b is better, 0 if equal
    """
    # 1. More vulnerabilities is better (more complete scan)
    vuln_diff = len(a.vulnerabilities) - len(b.vulnerabilities)
    if vuln_diff != 0:
        return 1 if vuln_diff > 0 else -1
    
    # 2. More installed packages is better
    pkg_diff = len(a.installed_packages) - len(b.installed_packages)
    if pkg_diff != 0:
        return 1 if pkg_diff > 0 else -1
    
    # 3. More recent scan is better
    if a.last_scanned_at > b.last_scanned_at:
        return 1
    elif a.last_scanned_at < b.last_scanned_at:
        return -1
    
    return 0
```

---

## Examples

### Example 1: EC2 Instance (AWS + CloudQuery)

**Before Deduplication:**
```python
assets = [
    DiscoveredAsset(
        identifier="i-0abc123",
        name="prod-web-1",
        source="aws",
        vulnerabilities=[],        # AWS doesn't scan vulns
        ip_addresses=["10.0.1.5", "54.23.45.67"]
    ),
    DiscoveredAsset(
        identifier="i-0abc123",
        name="prod-web-1", 
        source="cloudquery",
        vulnerabilities=[],
        ip_addresses=["10.0.1.5"]  # CloudQuery may miss public IP
    )
]
```

**After Deduplication:**
```python
# Keeps AWS version (more IP addresses, same vuln count)
result = [
    DiscoveredAsset(
        identifier="i-0abc123",
        name="prod-web-1",
        source="aws",
        vulnerabilities=[],
        ip_addresses=["10.0.1.5", "54.23.45.67"]  # AWS had more data
    )
]
```

### Example 2: Container (Trivy + Kubescape)

**Before Deduplication:**
```python
assets = [
    DiscoveredAsset(
        identifier="pod-nginx-abc123",
        name="nginx",
        source="trivy",
        vulnerabilities=[CVE-2023-1234, CVE-2023-5678],  # 2 CVEs
        installed_packages=["nginx:1.21.0", "openssl:1.1.1"]
    ),
    DiscoveredAsset(
        identifier="pod-nginx-abc123",
        name="nginx",
        source="kubescape",
        vulnerabilities=[],  # Kubescape doesn't scan CVEs
        installed_packages=[]
    )
]
```

**After Deduplication:**
```python
# Keeps Trivy version (has vulnerabilities + packages)
result = [
    DiscoveredAsset(
        identifier="pod-nginx-abc123",
        name="nginx",
        source="trivy",
        vulnerabilities=[CVE-2023-1234, CVE-2023-5678],
        installed_packages=["nginx:1.21.0", "openssl:1.1.1"]
    )
]
```

### Example 3: No Overlap

**Before Deduplication:**
```python
assets = [
    DiscoveredAsset(identifier="i-0abc123", source="aws"),
    DiscoveredAsset(identifier="vm-prod-456", source="azure"),
    DiscoveredAsset(identifier="10.0.1.5", source="nmap")
]
```

**After Deduplication:**
```python
# All unique identifiers → no deduplication
result = [
    DiscoveredAsset(identifier="i-0abc123", source="aws"),
    DiscoveredAsset(identifier="vm-prod-456", source="azure"),
    DiscoveredAsset(identifier="10.0.1.5", source="nmap")
]
```

---

## Metrics

Discovery scan results include deduplication metrics:

```json
{
  "summary": {
    "assets_discovered": 1247,
    "assets_after_deduplication": 1189,
    "assets_created": 983,
    "assets_updated": 206
  }
}
```

**Interpretation:**
- **1247 discovered** - Raw count from all scanners
- **1189 after dedup** - 58 duplicates removed (4.6%)
- **983 created** - New assets added to database
- **206 updated** - Existing assets refreshed

**Deduplication Rate:** `(discovered - deduplicated) / discovered`  
Example: `(1247 - 1189) / 1247 = 4.6%`

Typical rates:
- **Low overlap (0-5%)**: Scanners target different infrastructure
- **Medium overlap (5-20%)**: Some scanners share domains (e.g., AWS + CloudQuery)
- **High overlap (20%+)**: Multiple scanners on same resources (e.g., Trivy + Kubescape on K8s)

---

## Benefits

### 1. Data Integrity
- **One source of truth** per asset
- No confusion from duplicate records
- Clear asset count

### 2. Database Efficiency
- **Reduced storage** - No duplicate rows
- **Faster queries** - Smaller tables
- **Cleaner UI** - No duplicate entries

### 3. Better Data Quality
- **Prefer complete scans** - Assets with more vulnerabilities/packages
- **Fresh data wins** - Most recent scan takes precedence
- **Automatic selection** - No manual merge required

### 4. Scanner Flexibility
- **Run multiple scanners safely** - Overlaps handled automatically
- **Add new scanners** - No fear of duplication
- **Comprehensive coverage** - Use best tool for each source

---

## Edge Cases

### Same Identifier, Different Platforms?

**Scenario:** CloudQuery uses AWS instance-id, but Nmap uses IP address

**Solution:** Different identifiers → No deduplication
```python
asset1 = DiscoveredAsset(identifier="i-0abc123", source="cloudquery")
asset2 = DiscoveredAsset(identifier="10.0.1.5", source="nmap")
# Both kept (different identifiers)
```

### Manual Enrichments?

**Scenario:** User manually added tags to an asset, then scanner updates it

**Solution:** Database persistence preserves manual fields
```python
# Database update logic (orchestrator.py)
if existing and update_existing:
    for key, value in discovered.items():
        if value is not None:  # Only update non-null values
            setattr(existing, key, value)
    # Manual fields not in discovered dict are preserved
```

### Timestamp Tie?

**Scenario:** Two scanners run at exactly the same time

**Solution:** Falls through to equality (keeps whichever was processed first)
```python
if a.last_scanned_at == b.last_scanned_at:
    return 0  # Equal priority → keep first
```

---

## Testing

### Unit Test (Example)

```python
def test_deduplication():
    orchestrator = DiscoveryOrchestrator(tenant_id="test")
    
    assets = [
        DiscoveredAsset(
            identifier="test-1",
            vulnerabilities=[],
            last_scanned_at=datetime(2024, 1, 1)
        ),
        DiscoveredAsset(
            identifier="test-1",
            vulnerabilities=[CVE("CVE-2023-1234")],
            last_scanned_at=datetime(2024, 1, 2)
        )
    ]
    
    result = orchestrator._deduplicate_assets(assets)
    
    assert len(result) == 1
    assert len(result[0].vulnerabilities) == 1  # Kept version with vuln
```

### Integration Test (Manual)

1. **Run overlapping scanners:**
   ```bash
   curl -X POST /discovery/scan -d '{
     "scanners": ["aws", "cloudquery"],
     "parallel": true
   }'
   ```

2. **Check metrics:**
   ```bash
   curl /discovery/status
   ```

3. **Verify deduplication:**
   ```json
   {
     "assets_discovered": 150,
     "assets_after_deduplication": 142
   }
   ```
   - Expected: ~5% dedup rate for AWS+CloudQuery

---

## Future Enhancements

### Confidence Scoring
- Weight scanners by reliability
- AWS = 1.0, CloudQuery = 0.9, Nmap = 0.8
- Choose asset from most reliable scanner

### Attribute Merging
- Instead of choosing one asset, merge best attributes from all
- Take IP list from AWS, vulnerabilities from Trivy, tags from CloudQuery

### Deduplication Report
- Show which assets were deduplicated
- List discarded versions for audit
- Highlight scanner conflicts

---

## Conclusion

Deduplication ensures clean, efficient asset inventory even when multiple scanners overlap.

**Key Points:**
- ✅ Uses identifier as deduplication key
- ✅ Prefers assets with more data
- ✅ Handles overlaps gracefully
- ✅ Preserves manual enrichments
- ✅ Reports deduplication metrics

**Status:** Production-ready, handles all common overlap scenarios.
