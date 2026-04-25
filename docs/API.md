# Glasswatch API Reference

Complete API documentation for the Glasswatch patch decision platform.

**Base URL**: `/api/v1`

**Version**: 1.0.0

---

## Table of Contents

- [Authentication](#authentication)
- [Vulnerabilities](#vulnerabilities)
- [Assets](#assets)
- [Goals](#goals)
- [Bundles](#bundles)
- [Maintenance Windows](#maintenance-windows)
- [Approvals](#approvals)
- [Discovery](#discovery)
- [Simulator](#simulator)
- [Comments](#comments)
- [Activities](#activities)
- [Audit Logs](#audit-logs)
- [Users](#users)
- [Snapshots](#snapshots)

---

## Authentication

### POST /auth/login

Initiate SSO login flow.

**Auth Required**: No

**Request Body**:
```json
{
  "organization": "acme-corp",
  "redirect_uri": "https://app.glasswatch.ai/callback"
}
```

**Response** (200 OK):
```json
{
  "authorization_url": "https://workos.com/sso/authorize?..."
}
```

**Demo Mode**: If WorkOS is not configured, returns `/api/v1/auth/demo-login` URL.

---

### GET /auth/demo-login

Demo login without SSO (development/testing only).

**Auth Required**: No

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "demo@patchguide.ai",
    "name": "Demo User",
    "role": "admin",
    "avatar_url": null
  },
  "redirect_to": "/dashboard"
}
```

---

### GET /auth/callback

Handle SSO callback from WorkOS.

**Auth Required**: No

**Query Parameters**:
- `code` (required): Authorization code from WorkOS
- `state` (optional): CSRF token

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "email": "alice@acme.com",
    "name": "Alice Smith",
    "role": "admin",
    "avatar_url": "https://gravatar.com/..."
  },
  "redirect_to": "/dashboard"
}
```

---

### GET /auth/me

Get current user's profile.

**Auth Required**: Yes (Bearer token)

**Response** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "email": "alice@acme.com",
  "name": "Alice Smith",
  "role": "admin",
  "avatar_url": "https://gravatar.com/...",
  "tenant_id": "770e8400-e29b-41d4-a716-446655440000",
  "tenant_name": "Acme Corporation",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-04-20T10:00:00Z",
  "preferences": {
    "theme": "dark",
    "notifications_enabled": true
  }
}
```

---

### PATCH /auth/me/preferences

Update user preferences.

**Auth Required**: Yes

**Request Body**:
```json
{
  "preferences": {
    "theme": "dark",
    "notifications_enabled": false,
    "email_digest": "daily"
  }
}
```

**Response** (200 OK): Returns updated user profile.

---

### POST /auth/api-key

Generate new API key for programmatic access.

**Auth Required**: Yes

**Response** (200 OK):
```json
{
  "api_key": "gw_live_abc123...",
  "message": "Store this key securely. It won't be shown again."
}
```

**Note**: Invalidates any existing API key for the user.

---

### POST /auth/logout

Logout current user.

**Auth Required**: Yes

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

## Vulnerabilities

### GET /vulnerabilities

List vulnerabilities with filtering and search.

**Auth Required**: Yes

**Query Parameters**:
- `severity` (string): Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
- `kev_only` (boolean): Only show KEV-listed vulnerabilities (default: false)
- `source` (string): Filter by source (nvd, ghsa, etc.)
- `search` (string): Search in identifier, title, description
- `skip` (integer): Pagination offset (default: 0)
- `limit` (integer): Max results (default: 100, max: 500)

**Response** (200 OK):
```json
{
  "vulnerabilities": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "identifier": "CVE-2024-1234",
      "source": "nvd",
      "title": "Remote Code Execution in Apache Commons",
      "severity": "CRITICAL",
      "cvss_score": 9.8,
      "epss_score": 0.89,
      "kev_listed": true,
      "exploit_available": true,
      "patch_available": true,
      "published_at": "2024-01-15T10:00:00Z",
      "is_critical": true
    }
  ],
  "total": 1247,
  "skip": 0,
  "limit": 100
}
```

---

### GET /vulnerabilities/{vulnerability_id}

Get detailed vulnerability information.

**Auth Required**: Yes

**Path Parameters**:
- `vulnerability_id` (UUID): Vulnerability ID

**Response** (200 OK):
```json
{
  "vulnerability": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "identifier": "CVE-2024-1234",
    "source": "nvd",
    "title": "Remote Code Execution in Apache Commons",
    "description": "A critical vulnerability allowing remote code execution...",
    "severity": "CRITICAL",
    "cvss_score": 9.8,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "epss_score": 0.89,
    "kev_listed": true,
    "exploit_available": true,
    "exploit_maturity": "functional",
    "patch_available": true,
    "patch_released_at": "2024-01-20T00:00:00Z",
    "vendor_advisory_url": "https://apache.org/security/CVE-2024-1234",
    "affected_products": ["apache-commons:*:*:*:*:*:*:*"],
    "cpe_list": ["cpe:2.3:a:apache:commons:2.0:*:*:*:*:*:*:*"],
    "published_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-04-15T10:00:00Z",
    "days_since_published": 95
  },
  "affected_assets": [
    {
      "asset_id": "660e8400-e29b-41d4-a716-446655440000",
      "asset_name": "Production Web Server 01",
      "asset_type": "server",
      "environment": "production",
      "criticality": 5,
      "exposure": "internet",
      "risk_score": 95,
      "recommended_action": "PATCH_IMMEDIATELY",
      "patch_scheduled": "2024-04-30T02:00:00Z",
      "mitigation_applied": false,
      "code_executed": true,
      "library_loaded": true
    }
  ],
  "affected_asset_count": 1
}
```

**Error Responses**:
- `404`: Vulnerability not found

---

### POST /vulnerabilities/search

Advanced vulnerability search with multiple criteria.

**Auth Required**: Yes

**Request Body**:
```json
{
  "identifiers": ["CVE-2024-1234", "CVE-2024-5678"],
  "min_cvss": 7.0,
  "max_cvss": 10.0,
  "min_epss": 0.5,
  "published_after": "2024-01-01T00:00:00Z",
  "published_before": "2024-12-31T23:59:59Z",
  "has_exploit": true,
  "has_patch": true,
  "skip": 0,
  "limit": 100
}
```

**Response** (200 OK):
```json
{
  "vulnerabilities": [...],
  "total": 42,
  "skip": 0,
  "limit": 100,
  "search_criteria": {
    "identifiers": ["CVE-2024-1234", "CVE-2024-5678"],
    "min_cvss": 7.0,
    "max_cvss": 10.0,
    "min_epss": 0.5,
    "published_after": "2024-01-01T00:00:00Z",
    "published_before": "2024-12-31T23:59:59Z",
    "has_exploit": true,
    "has_patch": true
  }
}
```

---

### GET /vulnerabilities/stats

Get vulnerability statistics for the tenant.

**Auth Required**: Yes

**Response** (200 OK):
```json
{
  "total_vulnerabilities": 1247,
  "severity_distribution": {
    "CRITICAL": 42,
    "HIGH": 185,
    "MEDIUM": 620,
    "LOW": 400
  },
  "kev_listed_count": 28,
  "exploits_available_count": 156,
  "patches_available_count": 892,
  "recent_vulnerabilities_7d": 15,
  "timestamp": "2024-04-20T10:00:00Z"
}
```

---

## Assets

### GET /assets

List assets with filtering and search.

**Auth Required**: Yes

**Query Parameters**:
- `type` (string): Filter by asset type (server, container, cloud_instance, etc.)
- `platform` (string): Filter by platform (linux, windows, kubernetes, etc.)
- `environment` (string): Filter by environment (production, staging, development)
- `criticality` (integer): Filter by criticality (1-5)
- `exposure` (string): Filter by exposure level (internet, internal, isolated)
- `search` (string): Search in name, identifier, fqdn
- `skip` (integer): Pagination offset
- `limit` (integer): Max results

**Response** (200 OK):
```json
{
  "assets": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "identifier": "prod-web-01",
      "name": "Production Web Server 01",
      "type": "server",
      "platform": "linux",
      "environment": "production",
      "criticality": 5,
      "exposure": "internet",
      "location": "us-east-1a",
      "owner_team": "platform-engineering",
      "risk_score": 85,
      "is_internet_facing": true,
      "last_scanned_at": "2024-04-20T08:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 432,
  "skip": 0,
  "limit": 100
}
```

---

### GET /assets/{asset_id}

Get detailed asset information including vulnerabilities.

**Auth Required**: Yes

**Path Parameters**:
- `asset_id` (UUID): Asset ID

**Response** (200 OK):
```json
{
  "asset": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "identifier": "prod-web-01",
    "name": "Production Web Server 01",
    "type": "server",
    "platform": "linux",
    "environment": "production",
    "location": "us-east-1a",
    "criticality": 5,
    "exposure": "internet",
    "owner_team": "platform-engineering",
    "owner_email": "platform@acme.com",
    "business_unit": "Core Product",
    "os_family": "ubuntu",
    "os_version": "22.04 LTS",
    "ip_addresses": ["10.0.1.50", "52.1.2.3"],
    "fqdn": "web01.prod.acme.com",
    "cloud_account_id": "123456789012",
    "cloud_region": "us-east-1",
    "cloud_instance_type": "t3.large",
    "cloud_tags": {"Environment": "production", "Team": "platform"},
    "compliance_frameworks": ["SOC2", "PCI-DSS"],
    "compensating_controls": ["WAF", "IDS"],
    "patch_group": "production-week1",
    "maintenance_window": "Saturday 02:00-06:00 UTC",
    "risk_score": 85,
    "last_scanned_at": "2024-04-20T08:00:00Z",
    "last_patched_at": "2024-04-01T02:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-04-20T08:00:00Z"
  },
  "vulnerabilities": [
    {
      "vulnerability_id": "550e8400-e29b-41d4-a716-446655440000",
      "identifier": "CVE-2024-1234",
      "title": "Remote Code Execution in Apache Commons",
      "severity": "CRITICAL",
      "risk_score": 95,
      "code_executed": true,
      "library_loaded": true,
      "recommended_action": "PATCH_IMMEDIATELY",
      "patch_available": true,
      "mitigation_applied": false,
      "discovered_at": "2024-04-15T10:00:00Z"
    }
  ],
  "vulnerability_count": 1,
  "critical_vulnerability_count": 1
}
```

**Error Responses**:
- `404`: Asset not found

---

### POST /assets

Create a new asset.

**Auth Required**: Yes

**Request Body**:
```json
{
  "identifier": "prod-web-02",
  "name": "Production Web Server 02",
  "type": "server",
  "platform": "linux",
  "environment": "production",
  "criticality": 5,
  "exposure": "internet",
  "location": "us-east-1a",
  "owner_team": "platform-engineering",
  "owner_email": "platform@acme.com",
  "os_family": "ubuntu",
  "os_version": "22.04 LTS",
  "ip_addresses": ["10.0.1.51"],
  "fqdn": "web02.prod.acme.com"
}
```

**Response** (200 OK):
```json
{
  "asset": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "identifier": "prod-web-02",
    "name": "Production Web Server 02",
    "type": "server",
    "created_at": "2024-04-20T10:00:00Z"
  }
}
```

**Error Responses**:
- `400`: Missing required fields
- `409`: Asset with identifier already exists

---

### PUT /assets/{asset_id}

Update an existing asset.

**Auth Required**: Yes

**Path Parameters**:
- `asset_id` (UUID): Asset ID

**Request Body**: Partial asset object (only fields to update)

**Response** (200 OK): Returns updated asset summary

**Error Responses**:
- `404`: Asset not found

---

### DELETE /assets/{asset_id}

Delete an asset and its vulnerability associations.

**Auth Required**: Yes (Admin role required)

**Path Parameters**:
- `asset_id` (UUID): Asset ID

**Response** (200 OK):
```json
{
  "status": "deleted",
  "asset_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses**:
- `404`: Asset not found
- `403`: Insufficient permissions

---

### POST /assets/bulk-import

Bulk import assets from JSON or CSV file.

**Auth Required**: Yes

**Query Parameters**:
- `format` (string): File format (`json` or `csv`)

**Request Body**: multipart/form-data with file upload

**JSON Format**:
```json
[
  {
    "identifier": "server-001",
    "name": "Server 001",
    "type": "server",
    "environment": "production",
    "criticality": 4
  },
  ...
]
```

**CSV Format**:
```csv
identifier,name,type,environment,criticality
server-001,Server 001,server,production,4
server-002,Server 002,server,staging,3
```

**Response** (200 OK):
```json
{
  "status": "completed",
  "created": 42,
  "updated": 8,
  "errors": [
    "Row 15: Missing required field 'identifier'"
  ],
  "total_processed": 50
}
```

**Error Responses**:
- `400`: Failed to parse file

---

### GET /assets/{asset_id}/vulnerabilities

Get all vulnerabilities for a specific asset.

**Auth Required**: Yes

**Path Parameters**:
- `asset_id` (UUID): Asset ID

**Query Parameters**:
- `status` (string): Filter by status (ACTIVE, PATCHED, ACCEPTED_RISK) - default: ACTIVE
- `min_score` (integer): Minimum risk score (0-100)

**Response** (200 OK):
```json
{
  "asset": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "name": "Production Web Server 01",
    "type": "server"
  },
  "vulnerabilities": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "vulnerability_id": "550e8400-e29b-41d4-a716-446655440000",
      "identifier": "CVE-2024-1234",
      "title": "Remote Code Execution in Apache Commons",
      "severity": "CRITICAL",
      "risk_score": 95,
      "score_factors": {
        "cvss_contribution": 40,
        "epss_contribution": 20,
        "kev_boost": 15,
        "snapper_boost": 20
      },
      "status": "ACTIVE",
      "code_executed": true,
      "library_loaded": true,
      "execution_frequency": "high",
      "recommended_action": "PATCH_IMMEDIATELY",
      "patch_available": true,
      "mitigation_applied": false,
      "discovered_at": "2024-04-15T10:00:00Z",
      "last_reviewed_at": null
    }
  ],
  "total": 1,
  "risk_summary": {
    "critical": 1,
    "high": 0,
    "medium": 0,
    "low": 0
  }
}
```

**Error Responses**:
- `404`: Asset not found

---

## Goals

Goals are the core of Glasswatch - they convert business objectives into optimized patch schedules.

### GET /goals

List goals with filtering.

**Auth Required**: Yes

**Query Parameters**:
- `type` (string): Filter by goal type
- `active_only` (boolean): Only show active goals
- `skip` (integer): Pagination offset
- `limit` (integer): Max results

**Response** (200 OK):
```json
{
  "goals": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "name": "Q2 Compliance Deadline",
      "type": "compliance_deadline",
      "description": "Achieve SOC 2 compliance by June 30",
      "active": true,
      "target_date": "2024-06-30T23:59:59Z",
      "progress_percentage": 65.5,
      "vulnerabilities_total": 200,
      "vulnerabilities_resolved": 131,
      "bundles_created": 8,
      "bundles_completed": 5,
      "risk_reduction_achieved": 4200,
      "created_at": "2024-04-01T00:00:00Z"
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 100
}
```

---

### POST /goals

Create a new goal.

**Auth Required**: Yes

**Request Body**:
```json
{
  "name": "Eliminate Critical Internet-Facing Vulnerabilities",
  "type": "zero_critical",
  "description": "Zero critical vulnerabilities on internet-facing assets",
  "target_date": "2024-07-01T00:00:00Z",
  "target_metric": "critical_count",
  "target_value": 0,
  "risk_tolerance": "balanced",
  "max_vulns_per_window": 10,
  "max_downtime_hours": 4.0,
  "require_vendor_approval": false,
  "min_patch_weather_score": 70,
  "asset_filters": {
    "exposure": "internet",
    "environment": ["production", "staging"]
  },
  "vulnerability_filters": {
    "severity": ["CRITICAL"]
  }
}
```

**Response** (200 OK): Returns created goal object

**Error Responses**:
- `400`: Validation error (target_date in past, etc.)

---

### GET /goals/{goal_id}

Get detailed goal information.

**Auth Required**: Yes

**Response** includes full goal details, progress metrics, and associated bundles.

---

### PATCH /goals/{goal_id}

Update goal configuration.

**Auth Required**: Yes

**Request Body**: Partial goal object

---

### DELETE /goals/{goal_id}

Delete a goal and its associated bundles.

**Auth Required**: Yes (Admin role)

---

### POST /goals/{goal_id}/optimize

Run optimization to generate patch bundles.

**Auth Required**: Yes

**Request Body**:
```json
{
  "maintenance_window_count": 12,
  "start_date": "2024-05-01T00:00:00Z",
  "force_reoptimize": false
}
```

**Response** (200 OK):
```json
{
  "status": "completed",
  "bundles_created": 8,
  "total_vulnerabilities": 156,
  "estimated_risk_reduction": 8420,
  "estimated_total_downtime_hours": 24,
  "optimization_time_seconds": 12.5,
  "bundles": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440000",
      "name": "Bundle 1 - Production Critical",
      "scheduled_for": "2024-05-04T02:00:00Z",
      "vulnerabilities_count": 12,
      "risk_score": 1140
    }
  ]
}
```

**Note**: This is a computationally expensive operation (rate limit: 10/hour)

---

### GET /goals/{goal_id}/preview

Preview optimization without creating bundles.

**Auth Required**: Yes

**Query Parameters**:
- `maintenance_window_count` (integer): Number of windows to schedule

**Response**: Similar to `/optimize` but doesn't create actual bundles

---

## Bundles

Patch bundles are optimized groups of patches created by the goal engine.

### GET /bundles

List patch bundles with filtering.

**Auth Required**: Yes

**Query Parameters**:
- `status` (string): Filter by status (draft, scheduled, approved, in_progress, completed, failed, cancelled)
- `goal_id` (UUID): Filter by goal
- `scheduled_after` (datetime): Scheduled after date
- `scheduled_before` (datetime): Scheduled before date
- `skip` (integer): Pagination offset
- `limit` (integer): Max results

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440000",
      "name": "Bundle 1 - Production Critical",
      "description": "Critical patches for production web servers",
      "status": "approved",
      "scheduled_for": "2024-05-04T02:00:00Z",
      "estimated_downtime_minutes": 45,
      "approval_required": true,
      "approved_by": "alice@acme.com",
      "approved_at": "2024-04-20T14:00:00Z",
      "created_at": "2024-04-20T10:00:00Z",
      "items_count": 12,
      "total_risk_score": 1140
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 100
}
```

---

### GET /bundles/{bundle_id}

Get detailed bundle information with all items.

**Auth Required**: Yes

**Response** (200 OK):
```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440000",
  "name": "Bundle 1 - Production Critical",
  "description": "Critical patches for production web servers",
  "status": "approved",
  "scheduled_for": "2024-05-04T02:00:00Z",
  "estimated_downtime_minutes": 45,
  "approval_required": true,
  "approved_by": "alice@acme.com",
  "approved_at": "2024-04-20T14:00:00Z",
  "items": [
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440000",
      "vulnerability": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "identifier": "CVE-2024-1234",
        "severity": "CRITICAL",
        "description": "Remote Code Execution..."
      },
      "asset": {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "name": "Production Web Server 01",
        "identifier": "prod-web-01",
        "type": "server",
        "criticality": 5
      },
      "risk_score": 95,
      "patch_available": true,
      "estimated_patch_time_minutes": 15
    }
  ]
}
```

---

### PATCH /bundles/{bundle_id}/status

Update bundle status.

**Auth Required**: Yes

**Request Body**:
```json
{
  "status": "approved",
  "approved_by": "alice@acme.com"
}
```

**Valid Status Transitions**:
- `draft` → `scheduled`
- `scheduled` → `approved` (requires approval permission)
- `approved` → `in_progress`
- `in_progress` → `completed` or `failed`
- Any → `cancelled`

**Response** (200 OK): Returns updated bundle

---

### POST /bundles/{bundle_id}/execute

Start bundle execution.

**Auth Required**: Yes (requires approved bundle)

**Response** (200 OK):
```json
{
  "message": "Bundle 'Bundle 1 - Production Critical' execution started",
  "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress"
}
```

**Error Responses**:
- `400`: Bundle must be approved before execution
- `404`: Bundle not found

**Note**: This endpoint would integrate with actual patch deployment systems (Ansible, SCCM, AWS Systems Manager, etc.)

---

### GET /bundles/stats

Get bundle statistics for dashboard.

**Auth Required**: Yes

**Response** (200 OK):
```json
{
  "total": 42,
  "by_status": {
    "draft": 2,
    "scheduled": 5,
    "approved": 8,
    "in_progress": 1,
    "completed": 24,
    "failed": 2,
    "cancelled": 0
  },
  "pending_approval": 5,
  "next_scheduled": {
    "id": "aa0e8400-e29b-41d4-a716-446655440000",
    "name": "Bundle 1 - Production Critical",
    "scheduled_for": "2024-05-04T02:00:00Z"
  }
}
```

---

## Maintenance Windows

### GET /maintenance-windows

List maintenance windows.

**Auth Required**: Yes

**Query Parameters**:
- `type` (string): Filter by type (scheduled, emergency, blackout)
- `environment` (string): Filter by environment
- `active_only` (boolean): Only active windows
- `future_only` (boolean): Only future windows
- `approved_only` (boolean): Only approved windows
- `skip`, `limit`: Pagination

**Response** (200 OK): Returns list of maintenance windows

---

### POST /maintenance-windows

Create a maintenance window.

**Auth Required**: Yes

**Request Body**:
```json
{
  "name": "Production Saturday Maintenance",
  "description": "Weekly production maintenance window",
  "type": "scheduled",
  "start_time": "2024-05-04T02:00:00Z",
  "end_time": "2024-05-04T06:00:00Z",
  "timezone": "UTC",
  "environment": "production",
  "max_duration_hours": 4.0,
  "max_assets": 20,
  "approved_activities": ["patching", "updates", "restarts"]
}
```

---

### GET /maintenance-windows/{window_id}

Get window details.

---

### PUT /maintenance-windows/{window_id}

Update window configuration.

---

### DELETE /maintenance-windows/{window_id}

Delete a maintenance window.

---

### POST /maintenance-windows/{window_id}/freeze

Activate change freeze (prevent patching).

**Request Body**:
```json
{
  "reason": "Critical incident in progress"
}
```

---

### POST /maintenance-windows/{window_id}/unfreeze

Deactivate change freeze.

---

## Approvals

### GET /approvals/requests

List approval requests.

**Auth Required**: Yes

**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected, expired)
- `assigned_to_me` (boolean): Only show requests assigned to current user
- `skip`, `limit`: Pagination

---

### POST /approvals/requests

Create approval request for a bundle.

**Auth Required**: Yes

**Request Body**:
```json
{
  "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "title": "Approve Q2 Critical Patches",
  "description": "12 critical vulnerabilities on production servers",
  "risk_level": "high",
  "impact_summary": {
    "assets_affected": 12,
    "estimated_downtime": "45 minutes",
    "services_impacted": ["web-api", "frontend"]
  }
}
```

---

### GET /approvals/requests/{request_id}

Get approval request details.

---

### POST /approvals/requests/{request_id}/approve

Approve a request.

**Auth Required**: Yes (requires approver permission)

**Request Body**:
```json
{
  "comment": "Approved for Saturday maintenance window"
}
```

---

### POST /approvals/requests/{request_id}/reject

Reject a request.

**Auth Required**: Yes

**Request Body**:
```json
{
  "comment": "Insufficient testing, please add rollback plan"
}
```

---

### GET /approvals/policies

List approval policies.

**Auth Required**: Yes

---

### POST /approvals/policies

Create approval policy (Admin only).

**Request Body**:
```json
{
  "name": "Production Critical Patches",
  "description": "Requires 2 approvals for critical production patches",
  "required_approvals": 2,
  "auto_approve_threshold": null,
  "approval_timeout_hours": 48,
  "conditions": {
    "environment": ["production"],
    "risk_level": ["high", "critical"]
  },
  "approver_roles": ["admin", "security_lead"]
}
```

---

## Discovery

Automated asset and vulnerability discovery scanning.

### GET /discovery/scans

List discovery scans.

**Auth Required**: Yes

---

### POST /discovery/scans

Trigger a new discovery scan.

**Auth Required**: Yes

**Request Body**:
```json
{
  "name": "Production Network Scan",
  "scan_type": "network",
  "targets": ["10.0.0.0/16", "172.16.0.0/12"],
  "scan_config": {
    "port_scan": true,
    "service_detection": true,
    "vulnerability_detection": true
  }
}
```

---

### GET /discovery/scans/{scan_id}

Get scan details and results.

---

### GET /discovery/scans/{scan_id}/results

Get detailed scan results.

---

### DELETE /discovery/scans/{scan_id}

Cancel or delete a scan.

---

## Simulator

Patch impact prediction and dry-run simulation.

> **Note on External API Simulators:** There are two distinct simulator concepts in Glasswatch:
> 1. **Patch Impact Simulator** (this section) — production API endpoints for predicting the risk and downtime impact of applying a bundle. Available in all environments.
> 2. **External API Simulators** — dev/testing-only mock servers that mimic Tenable, Qualys, Rapid7, and other external APIs. Enabled via `SIMULATOR_MODE=true`; runs on port 8099. These are **not** production API endpoints. See [docs/SIMULATORS.md](SIMULATORS.md).

### POST /simulator/predict

Predict patch impact for a bundle.

**Auth Required**: Yes

**Request Body**:
```json
{
  "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "id": "cc0e8400-e29b-41d4-a716-446655440000",
  "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "risk_score": 35,
  "risk_level": "medium",
  "impact_summary": {
    "assets_affected": 12,
    "services_impacted": ["web-api", "frontend"],
    "estimated_downtime_minutes": 45,
    "rollback_plan_available": true
  },
  "is_safe_to_proceed": true,
  "created_at": "2024-04-20T10:00:00Z",
  "completed_at": "2024-04-20T10:00:15Z"
}
```

---

### POST /simulator/dry-run

Run full dry-run simulation (includes validation checks).

**Auth Required**: Yes

**Request Body**:
```json
{
  "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000"
}
```

**Response**: Includes impact prediction plus pre-flight validation (package availability, disk space, connectivity, maintenance window conflicts)

---

## Comments

### POST /comments

Add comment to a resource.

**Auth Required**: Yes

**Request Body**:
```json
{
  "resource_type": "vulnerability",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "This is affecting our payment processing system. @alice please review."
}
```

**Note**: Supports @mentions for notifications

---

### GET /comments

List comments for a resource.

**Query Parameters**:
- `resource_type` (required): vulnerability, asset, bundle, goal
- `resource_id` (required): UUID of the resource

---

### PUT /comments/{comment_id}

Update comment content.

---

### DELETE /comments/{comment_id}

Delete a comment.

---

## Activities

Real-time activity feed for all tenant actions.

### GET /activities

List recent activities.

**Auth Required**: Yes

**Query Parameters**:
- `resource_type`: Filter by resource type
- `resource_id`: Filter by specific resource
- `user_id`: Filter by user
- `action_type`: Filter by action type
- `since`: Activity since timestamp
- `skip`, `limit`: Pagination

**Response** (200 OK):
```json
{
  "activities": [
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440000",
      "user_id": "660e8400-e29b-41d4-a716-446655440000",
      "user_name": "Alice Smith",
      "action": "bundle.approved",
      "resource_type": "bundle",
      "resource_id": "aa0e8400-e29b-41d4-a716-446655440000",
      "resource_name": "Bundle 1 - Production Critical",
      "description": "Approved bundle for execution",
      "metadata": {
        "comment": "Approved for Saturday maintenance"
      },
      "timestamp": "2024-04-20T14:00:00Z"
    }
  ],
  "total": 1247,
  "skip": 0,
  "limit": 100
}
```

---

### GET /activities/stream

WebSocket endpoint for real-time activity stream.

**Auth Required**: Yes (WebSocket upgrade)

---

## Audit Logs

Comprehensive audit logging for compliance. Every action taken in Glasswatch is recorded — goal creation, bundle approvals, user role changes, rule edits, and more.

### GET /api/v1/audit-log

Query audit logs.

**Auth Required**: Yes (Admin role)

**Query Parameters**:
- `action` (string): Filter by action type (e.g., `bundle.approved`, `goal.created`)
- `resource_type` (string): Filter by resource type (e.g., `bundle`, `goal`, `user`)
- `user_id` (UUID): Filter by user
- `since` (datetime): Start of time range (ISO 8601)
- `until` (datetime): End of time range (ISO 8601)
- `limit` (integer): Max results (default: 100)
- `offset` (integer): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "logs": [
    {
      "id": "ee0e8400-e29b-41d4-a716-446655440000",
      "action": "bundle.approved",
      "resource_type": "bundle",
      "resource_id": "aa0e8400-e29b-41d4-a716-446655440000",
      "resource_name": "Bundle 1 - Production Critical",
      "details": {
        "approval_comment": "Approved for Saturday maintenance"
      },
      "ip_address": "203.0.113.42",
      "success": true,
      "error_message": null,
      "created_at": "2024-04-20T14:00:00Z",
      "user": {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "email": "alice@acme.com",
        "name": "Alice Smith"
      }
    }
  ],
  "total": 52847,
  "limit": 100,
  "offset": 0
}
```

**Log entry fields**:
- `id` — unique log entry UUID
- `action` — dot-notation action string (e.g., `bundle.approved`, `user.role_changed`)
- `resource_type` — type of resource affected
- `resource_id` — UUID of the affected resource
- `resource_name` — human-readable name of the resource at time of action
- `details` — action-specific metadata object
- `ip_address` — originating IP address
- `success` — whether the action completed successfully
- `error_message` — error detail if `success` is false, otherwise null
- `created_at` — ISO 8601 timestamp
- `user` — `{id, email, name}` of the acting user, or null for system actions

---

### GET /api/v1/audit-log/export

Export audit logs as a CSV download.

**Auth Required**: Yes (Admin role)

**Query Parameters**: Same as `GET /api/v1/audit-log` (`action`, `resource_type`, `user_id`, `since`, `until`, `limit`, `offset`)

**Response**: CSV file download (`Content-Disposition: attachment; filename="audit-log.csv"`)

**Use case**: Compliance reporting, SOC 2 audits, external log archival.

---

## Users

User management (Admin only).

### GET /users

List all users in tenant.

**Auth Required**: Yes (Admin role)

---

### POST /users/invite

Invite new user.

**Auth Required**: Yes (Admin role)

**Request Body**:
```json
{
  "email": "bob@acme.com",
  "name": "Bob Johnson",
  "role": "analyst",
  "permissions": {}
}
```

---

### GET /users/{user_id}

Get user details.

---

### PATCH /users/{user_id}

Update user (role, permissions).

---

### DELETE /users/{user_id}

Deactivate user.

---

## Snapshots

Point-in-time snapshots for rollback and compliance reporting.

### POST /snapshots

Create snapshot.

**Auth Required**: Yes

**Request Body**:
```json
{
  "name": "Pre-Q2-Patching",
  "description": "Snapshot before Q2 critical patches",
  "include_assets": true,
  "include_vulnerabilities": true,
  "include_bundles": true
}
```

---

### GET /snapshots

List snapshots.

---

### GET /snapshots/{snapshot_id}

Get snapshot details.

---

### POST /snapshots/{snapshot_id}/restore

Restore from snapshot (creates new bundles to revert).

---

### DELETE /snapshots/{snapshot_id}

Delete snapshot.

---

## Common HTTP Status Codes

- **200 OK**: Request succeeded
- **201 Created**: Resource created successfully
- **204 No Content**: Success with no response body
- **400 Bad Request**: Invalid input or validation error
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource already exists or state conflict
- **422 Unprocessable Entity**: Validation error (Pydantic)
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

---

## Rate Limits

| Endpoint Category | Limit |
|------------------|-------|
| Standard endpoints | 1000/hour |
| Optimization (`/goals/*/optimize`) | 10/hour |
| Search endpoints | 500/hour |
| Bulk operations | 100/hour |

Rate limit headers included in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time (Unix timestamp)

---

## Webhooks

Subscribe to events at `POST /api/v1/webhooks/subscriptions`

Available events:
- `vulnerability.discovered`
- `asset.created`
- `bundle.created`
- `bundle.approved`
- `bundle.executed`
- `bundle.completed`
- `goal.created`
- `goal.completed`
- `approval.requested`
- `approval.approved`
- `approval.rejected`

Webhook payload format:
```json
{
  "event": "bundle.approved",
  "timestamp": "2024-04-20T14:00:00Z",
  "data": {
    "bundle_id": "aa0e8400-e29b-41d4-a716-446655440000",
    "bundle_name": "Bundle 1 - Production Critical",
    "approved_by": "alice@acme.com"
  }
}
```

---

**Version**: 1.0.0  
**Last Updated**: 2024-04-20  
**Interactive API Docs**: `/docs` (Swagger UI) or `/redoc` (ReDoc)
