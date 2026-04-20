"""
OpenAPI/Swagger configuration for Glasswatch API.

Provides enhanced API documentation with security schemes, tags, and examples.
"""
from typing import Dict, Any, List


def get_openapi_config() -> Dict[str, Any]:
    """
    Get custom OpenAPI configuration.
    
    Returns:
        Dictionary with OpenAPI metadata and configuration
    """
    return {
        "title": "Glasswatch API",
        "version": "1.0.0",
        "description": """
# Glasswatch API

**Transform vulnerability chaos into organized, evidence-backed patch operations.**

Glasswatch is an AI-powered patch decision platform that converts business objectives into 
optimized patch schedules using constraint solving and intelligent risk scoring.

## Key Features

- 🎯 **Goal-Based Optimization**: Convert business objectives into patch schedules
- 🧮 **8-Factor Scoring**: Intelligent risk scoring beyond CVSS
- 🔄 **Runtime Context**: Snapper integration for actual code execution data
- 📊 **Patch Weather™**: Community-driven patch success metrics
- ✅ **Approval Workflows**: Multi-level approval with policy management
- 🔍 **Asset Discovery**: Automated vulnerability scanning
- 📝 **Audit Trail**: Complete activity and audit logging

## Authentication

All endpoints (except `/auth/login` and `/auth/demo-login`) require authentication:

- **JWT Bearer Token**: Pass in `Authorization: Bearer <token>` header
- **API Key**: Pass in `X-API-Key: <key>` header (for programmatic access)

To obtain a token:
1. Call `POST /api/v1/auth/login` with your organization
2. Follow SSO redirect flow
3. Receive JWT token in callback response
4. For demo/testing: Use `GET /api/v1/auth/demo-login` (no SSO required)

## Multi-Tenancy

Glasswatch is built for multi-tenant SaaS:
- Each organization is a separate tenant with isolated data
- All API operations are automatically scoped to the authenticated user's tenant
- No cross-tenant data access is possible

## Rate Limiting

API rate limits (applied per tenant):
- **Standard endpoints**: 1000 requests/hour
- **Optimization endpoints**: 10 requests/hour (computationally expensive)
- **Search endpoints**: 500 requests/hour

## Pagination

List endpoints support pagination with `skip` and `limit` query parameters:
- Default limit: 100 items
- Maximum limit: 500 items
- Response includes `total`, `skip`, and `limit` fields

## Error Responses

All errors follow this structure:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common status codes:
- `400`: Bad Request - Invalid input
- `401`: Unauthorized - Missing or invalid token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource doesn't exist
- `409`: Conflict - Resource already exists
- `422`: Validation Error - Pydantic validation failed
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error

## Webhooks

Subscribe to real-time events:
- `vulnerability.discovered`
- `bundle.created`
- `bundle.approved`
- `bundle.executed`
- `goal.completed`
- `approval.requested`

Configure webhooks at `POST /api/v1/webhooks/subscriptions`
        """,
        "contact": {
            "name": "Glasswatch Support",
            "email": "support@glasswatch.ai",
            "url": "https://glasswatch.ai/support",
        },
        "license_info": {
            "name": "Proprietary",
            "url": "https://glasswatch.ai/terms",
        },
    }


def get_openapi_tags() -> List[Dict[str, str]]:
    """
    Get API endpoint tags with descriptions.
    
    Tags organize endpoints into logical groups in the API documentation.
    """
    return [
        {
            "name": "authentication",
            "description": "User authentication, SSO login, API key management, and profile operations",
        },
        {
            "name": "vulnerabilities",
            "description": "Vulnerability data from NVD, GHSA, and other sources. Search, filter, and get enriched context.",
        },
        {
            "name": "assets",
            "description": "Infrastructure assets (servers, containers, cloud instances). CRUD operations and bulk import.",
        },
        {
            "name": "goals",
            "description": "Business objectives converted into optimized patch schedules. The core optimization engine.",
        },
        {
            "name": "bundles",
            "description": "Optimized patch bundles created by the goal engine. Track status and execution.",
        },
        {
            "name": "maintenance-windows",
            "description": "Approved time windows for patching. Define schedules and blackout periods.",
        },
        {
            "name": "approvals",
            "description": "Multi-level approval workflows for patch bundles. Policies, requests, and actions.",
        },
        {
            "name": "discovery",
            "description": "Automated asset and vulnerability discovery scanning. Schedule and trigger scans.",
        },
        {
            "name": "simulator",
            "description": "Patch impact prediction and dry-run simulation. Analyze risk before execution.",
        },
        {
            "name": "comments",
            "description": "Team collaboration via comments on vulnerabilities, assets, and bundles. @mentions supported.",
        },
        {
            "name": "activities",
            "description": "Activity feed for all tenant actions. Real-time updates and historical timeline.",
        },
        {
            "name": "audit",
            "description": "Comprehensive audit logging for compliance and security. Query by resource, action, and time.",
        },
        {
            "name": "users",
            "description": "User management (admin only). Roles, permissions, and invitations.",
        },
        {
            "name": "snapshots",
            "description": "Point-in-time snapshots for rollback and compliance reporting.",
        },
    ]


def get_openapi_servers(env: str = "development") -> List[Dict[str, str]]:
    """
    Get server URLs for different environments.
    
    Args:
        env: Environment name (development, staging, production)
        
    Returns:
        List of server configurations
    """
    servers = {
        "development": [
            {
                "url": "http://localhost:8000",
                "description": "Local development server",
            },
        ],
        "staging": [
            {
                "url": "https://api-staging.glasswatch.ai",
                "description": "Staging environment",
            },
        ],
        "production": [
            {
                "url": "https://api.glasswatch.ai",
                "description": "Production environment",
            },
        ],
    }
    
    return servers.get(env, servers["development"])


def get_openapi_security_schemes() -> Dict[str, Any]:
    """
    Get security scheme definitions.
    
    Defines authentication methods available in the API.
    """
    return {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from `/api/v1/auth/login` or `/api/v1/auth/demo-login`",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for programmatic access. Generate at `POST /api/v1/auth/api-key`",
        },
    }


def get_openapi_examples() -> Dict[str, Dict[str, Any]]:
    """
    Get common response examples for reuse across endpoints.
    
    Returns:
        Dictionary of named examples
    """
    return {
        "vulnerability_example": {
            "summary": "Critical vulnerability example",
            "value": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "identifier": "CVE-2024-1234",
                "source": "nvd",
                "title": "Remote Code Execution in Apache Commons",
                "severity": "CRITICAL",
                "cvss_score": 9.8,
                "epss_score": 0.89,
                "kev_listed": True,
                "exploit_available": True,
                "patch_available": True,
                "published_at": "2024-01-15T10:00:00Z",
                "is_critical": True,
            }
        },
        "asset_example": {
            "summary": "Production server example",
            "value": {
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
                "is_internet_facing": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
        },
        "bundle_example": {
            "summary": "Patch bundle example",
            "value": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "name": "Q1 Critical Patches - Production",
                "description": "Critical patches for production environment",
                "status": "approved",
                "scheduled_for": "2024-04-30T02:00:00Z",
                "estimated_downtime_minutes": 45,
                "approval_required": True,
                "created_at": "2024-04-20T10:00:00Z",
                "items_count": 8,
                "total_risk_score": 720,
            }
        },
        "error_400": {
            "summary": "Bad Request",
            "value": {"detail": "Invalid input: field 'name' is required"}
        },
        "error_401": {
            "summary": "Unauthorized",
            "value": {"detail": "Not authenticated"}
        },
        "error_403": {
            "summary": "Forbidden",
            "value": {"detail": "Insufficient permissions. Admin role required."}
        },
        "error_404": {
            "summary": "Not Found",
            "value": {"detail": "Resource not found"}
        },
        "error_409": {
            "summary": "Conflict",
            "value": {"detail": "Asset with identifier 'prod-web-01' already exists"}
        },
    }
