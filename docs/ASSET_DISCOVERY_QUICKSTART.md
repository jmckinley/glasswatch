# Asset Discovery Quick Start Guide

Glasswatch provides comprehensive automated asset discovery across cloud providers, containers, Kubernetes, network infrastructure, and commercial CMDBs.

## Overview

**Supported Discovery Sources:**
- ☁️ **Cloud Providers:** AWS, Azure, GCP
- 🐳 **Containers:** Trivy (Docker, containerd, filesystems)
- ☸️ **Kubernetes:** Trivy K8s, Kubescape (security posture)
- 🌐 **Network:** Nmap (hosts, ports, services, OS detection)
- 📊 **CMDB:** ServiceNow, Jira Assets (coming soon), Device42 (coming soon)

**Discovery Features:**
- ✅ Parallel scanning across multiple sources
- ✅ Automatic deduplication
- ✅ Asset enrichment (criticality, exposure, environment)
- ✅ Vulnerability detection (where supported)
- ✅ Database persistence with update/create logic
- ✅ Scheduled auto-sync (coming soon)

---

## Quick Start: Single Scanner

### 1. AWS Discovery

**Prerequisites:**
```bash
pip install boto3
# Configure AWS credentials (one of):
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
# OR use ~/.aws/credentials
# OR use IAM role (for EC2/Lambda)
```

**Scan AWS:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["aws"],
    "aws_config": {
      "regions": ["us-east-1", "us-west-2"]
    },
    "parallel": true,
    "update_existing": true
  }'
```

**What it discovers:**
- EC2 instances (with tags, IPs, OS, exposure)
- RDS databases (with public accessibility)
- Lambda functions
- ECS services
- EKS clusters

---

### 2. Azure Discovery

**Prerequisites:**
```bash
pip install azure-identity azure-mgmt-compute azure-mgmt-sql \
    azure-mgmt-containerinstance azure-mgmt-containerservice \
    azure-mgmt-web azure-mgmt-resource

# Configure Azure credentials (one of):
az login  # Azure CLI
# OR set environment variables for service principal:
export AZURE_CLIENT_ID="your-client-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_SECRET="your-secret"
```

**Scan Azure:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["azure"],
    "azure_config": {
      "subscription_ids": ["your-subscription-id"]
    }
  }'
```

**What it discovers:**
- Virtual Machines (with tags, IPs, OS)
- SQL Databases
- Container Instances
- AKS clusters
- App Services

---

### 3. GCP Discovery

**Prerequisites:**
```bash
pip install google-cloud-compute google-cloud-sql google-cloud-container \
    google-cloud-run google-cloud-functions google-cloud-resource-manager

# Configure GCP credentials:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
# OR use: gcloud auth application-default login
```

**Scan GCP:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["gcp"],
    "gcp_config": {
      "project_ids": ["your-project-id"]
    }
  }'
```

**What it discovers:**
- Compute Engine VMs
- Cloud SQL instances
- GKE clusters
- Cloud Run services
- Cloud Functions

---

### 4. Container Scanning (Trivy)

**Prerequisites:**
```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

**Scan Container Images:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["trivy"],
    "trivy_config": {
      "scan_type": "image",
      "target": "nginx:latest"
    }
  }'
```

**Scan Kubernetes Cluster:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["trivy"],
    "trivy_config": {
      "scan_type": "k8s"
    }
  }'
```

**What it discovers:**
- Container images with vulnerabilities
- Kubernetes pods/deployments with CVEs
- Installed packages and versions
- Misconfiguration findings

---

### 5. Kubernetes Security Posture (Kubescape)

**Prerequisites:**
```bash
# Install Kubescape
curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash
```

**Scan Kubernetes:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["kubescape"],
    "kubescape_config": {
      "frameworks": ["nsa", "mitre", "cis-v1.23"]
    }
  }'
```

**What it discovers:**
- K8s resources (pods, deployments, services)
- Security control failures (NSA/CISA guidelines)
- CIS Kubernetes Benchmark violations
- MITRE ATT&CK framework mappings

---

### 6. Network Discovery (Nmap)

**Prerequisites:**
```bash
# Install Nmap
sudo apt-get install nmap  # Debian/Ubuntu
# OR
brew install nmap  # macOS
```

**Scan Network:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["nmap"],
    "nmap_config": {
      "target": "192.168.1.0/24",
      "scan_type": "normal"
    }
  }'
```

**Scan Single Host:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["nmap"],
    "nmap_config": {
      "target": "example.com",
      "scan_type": "quick"
    }
  }'
```

**What it discovers:**
- Network hosts (alive/down)
- Open ports and services
- OS detection
- Service versions

---

### 7. ServiceNow CMDB Integration

**Prerequisites:**
- ServiceNow instance with CMDB
- API credentials or OAuth token

**Scan ServiceNow CMDB:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["servicenow"],
    "servicenow_config": {
      "instance_url": "https://your-instance.service-now.com",
      "username": "api_user",
      "password": "api_password"
    }
  }'
```

**What it discovers:**
- Servers (Linux/Windows)
- Databases
- Applications
- Network devices
- All CMDB Configuration Items (CIs)

---

## Multi-Scanner Discovery

**Scan Everything at Once:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scanners": ["aws", "azure", "gcp", "trivy", "kubescape"],
    "aws_config": {
      "regions": ["us-east-1", "us-west-2"]
    },
    "azure_config": {
      "subscription_ids": ["azure-sub-id"]
    },
    "gcp_config": {
      "project_ids": ["gcp-project-id"]
    },
    "parallel": true,
    "update_existing": true
  }'
```

**Response:**
```json
{
  "status": "started",
  "tenant_id": "uuid",
  "scanners": ["aws", "azure", "gcp", "trivy", "kubescape"],
  "message": "Discovery scan started. Check /discovery/status for progress."
}
```

---

## Check Discovery Status

```bash
curl http://localhost:8000/api/v1/discovery/status
```

**Response:**
```json
{
  "status": "completed",
  "started_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:05:23",
  "summary": {
    "status": "completed",
    "duration_seconds": 323.5,
    "scanners_executed": 5,
    "assets_discovered": 1247,
    "assets_after_deduplication": 1189,
    "assets_created": 983,
    "assets_updated": 206,
    "total_errors": 2,
    "scanner_results": [
      {
        "scanner": "aws",
        "assets": 456,
        "duration": 89.2,
        "errors": 0
      },
      {
        "scanner": "azure",
        "assets": 234,
        "duration": 67.8,
        "errors": 1
      }
    ]
  }
}
```

---

## List Available Scanners

```bash
curl http://localhost:8000/api/v1/discovery/scanners
```

**Response:**
```json
{
  "scanners": [
    {
      "name": "trivy",
      "type": "container",
      "available": true,
      "description": "Container and Kubernetes vulnerability scanner",
      "requires": []
    },
    {
      "name": "aws",
      "type": "cloud",
      "available": true,
      "description": "AWS infrastructure discovery (EC2, RDS, Lambda, ECS, EKS)",
      "requires": ["boto3", "AWS credentials"]
    },
    {
      "name": "azure",
      "type": "cloud",
      "available": false,
      "description": "Azure infrastructure discovery",
      "error": "Azure SDK not installed"
    }
  ],
  "total": 7,
  "available": 4
}
```

---

## Test Scanner Configuration

```bash
curl -X POST http://localhost:8000/api/v1/discovery/test-scanner \
  -H "Content-Type: application/json" \
  -d '{
    "scanner": "aws",
    "config": {
      "region": "us-east-1"
    }
  }'
```

**Response:**
```json
{
  "scanner": "aws",
  "connection": "success",
  "message": "Connection test completed"
}
```

---

## Auto-Sync Configuration (Coming Soon)

**Schedule Daily Discovery:**
```bash
curl -X POST http://localhost:8000/api/v1/discovery/auto-sync/configure \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "interval_hours": 24,
    "scanners": ["aws", "azure", "trivy"],
    "aws_config": {
      "regions": ["us-east-1"]
    }
  }'
```

---

## Asset Enrichment

All discovered assets are automatically enriched with:

**Criticality Score (1-5):**
- Extracted from cloud tags (`Criticality: critical/high/medium/low`)
- Heuristic based on asset type (databases = 4, production servers = 5)
- Default: 3

**Exposure Level:**
- `INTERNET`: Public IP, internet-facing load balancer
- `INTRANET`: Private network, VPN-only
- `ISOLATED`: No network access, air-gapped

**Environment:**
- Extracted from tags (`Environment: production/staging/dev`)
- Default: `unknown`

**Owner Information:**
- Team: `Owner` tag
- Email: `OwnerEmail` tag or CMDB contact

---

## Best Practices

### 1. Start Small
Begin with a single scanner and small scope:
```bash
# Test with 1 region first
"aws_config": {"regions": ["us-east-1"]}
```

### 2. Use Parallel Scanning
Enable parallel scanning for faster discovery:
```bash
"parallel": true
```

### 3. Update Existing Assets
Keep your inventory fresh:
```bash
"update_existing": true
```

### 4. Tag Your Resources
Use consistent cloud tags for better enrichment:
```yaml
# AWS/Azure/GCP tags
Environment: production
Criticality: high
Owner: security-team
OwnerEmail: security@example.com
```

### 5. Schedule Regular Scans
Run discovery daily or weekly to keep inventory current.

---

## Troubleshooting

### Scanner Not Available
**Problem:** Scanner shows `"available": false` in `/discovery/scanners`

**Solution:**
1. Install required dependencies (see Prerequisites above)
2. Test scanner: `POST /discovery/test-scanner`
3. Check error message in response

### AWS: No Credentials
**Error:** `"Failed to scan region us-east-1: No credentials found"`

**Solution:**
```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Option 2: AWS credentials file
aws configure

# Option 3: IAM role (when running on EC2)
# No action needed - automatic
```

### Azure: Authentication Failed
**Error:** `"Azure SDK authentication failed"`

**Solution:**
```bash
# Option 1: Azure CLI
az login

# Option 2: Service principal
export AZURE_CLIENT_ID="..."
export AZURE_TENANT_ID="..."
export AZURE_CLIENT_SECRET="..."
```

### Trivy: Command Not Found
**Error:** `"Trivy scan failed: trivy: command not found"`

**Solution:**
```bash
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

### Nmap: Permission Denied
**Error:** `"Nmap requires root for OS detection"`

**Solution:**
```bash
# Run as root (not recommended for production)
sudo python main.py

# OR disable OS detection:
"nmap_config": {
  "scan_options": "-sV"  # Remove -O flag
}
```

---

## API Reference

### POST /api/v1/discovery/scan
Trigger asset discovery scan

**Request Body:**
```typescript
{
  scanners: string[];  // ["aws", "azure", "trivy", etc.]
  parallel?: boolean;  // default: true
  update_existing?: boolean;  // default: true
  aws_config?: {...};
  azure_config?: {...};
  gcp_config?: {...};
  // ... other scanner configs
}
```

### GET /api/v1/discovery/status
Get status of most recent discovery scan

### GET /api/v1/discovery/scanners
List all available scanners and their status

### POST /api/v1/discovery/test-scanner
Test scanner configuration without running full scan

### GET /api/v1/discovery/history
Get history of discovery scans (coming soon)

### POST /api/v1/discovery/auto-sync/configure
Configure automatic periodic discovery (coming soon)

---

## Next Steps

1. **Review discovered assets:** `GET /api/v1/assets`
2. **Enrich assets:** Add custom tags, criticality, owner info
3. **Configure patch goals:** Create goals based on discovered vulnerabilities
4. **Schedule maintenance windows:** Plan patching for discovered assets
5. **Enable auto-sync:** Keep inventory fresh automatically

For more details, see:
- [Asset Management API](./API_REFERENCE.md#assets)
- [Vulnerability Management](./VULNERABILITY_MANAGEMENT.md)
- [Patch Goals & Bundling](./PATCH_GOALS.md)
