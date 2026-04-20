"""
Asset Discovery API endpoints.

Trigger discovery scans, view progress, and configure auto-sync.
"""
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.services.discovery.orchestrator import DiscoveryOrchestrator
from backend.services.discovery.trivy_scanner import TrivyScanner
from backend.services.discovery.aws_scanner import AWSScanner
from backend.services.discovery.azure_scanner import AzureScanner
from backend.services.discovery.gcp_scanner import GCPScanner
from backend.services.discovery.kubescape_scanner import KubescapeScanner
from backend.services.discovery.servicenow_cmdb import ServiceNowCMDBScanner
from backend.services.discovery.nmap_scanner import NmapScanner
from backend.services.discovery.cloudquery_scanner import CloudQueryScanner
from backend.services.discovery.jira_assets_scanner import JiraAssetsScanner
from backend.services.discovery.device42_scanner import Device42Scanner


router = APIRouter()


# In-memory discovery status tracking (TODO: move to Redis/DB)
_discovery_status: Dict[UUID, Dict[str, Any]] = {}


@router.post("/discovery/scan")
async def trigger_discovery(
    background_tasks: BackgroundTasks,
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Trigger an asset discovery scan.
    
    Request body:
    {
        "scanners": ["aws", "trivy", "azure"],
        "aws_config": {"regions": ["us-east-1", "us-west-2"]},
        "parallel": true,
        "update_existing": true
    }
    """
    scanner_types = config.get("scanners", [])
    if not scanner_types:
        raise HTTPException(
            status_code=400,
            detail="No scanners specified. Provide 'scanners' array in request body."
        )
    
    # Initialize orchestrator
    orchestrator = DiscoveryOrchestrator(tenant.id)
    
    # Register requested scanners
    for scanner_type in scanner_types:
        try:
            if scanner_type == "aws":
                aws_config = config.get("aws_config", {})
                scanner = AWSScanner(aws_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "azure":
                azure_config = config.get("azure_config", {})
                scanner = AzureScanner(azure_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "gcp":
                gcp_config = config.get("gcp_config", {})
                scanner = GCPScanner(gcp_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "trivy":
                trivy_config = config.get("trivy_config", {})
                scanner = TrivyScanner(trivy_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "kubescape":
                kubescape_config = config.get("kubescape_config", {})
                scanner = KubescapeScanner(kubescape_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "servicenow":
                servicenow_config = config.get("servicenow_config", {})
                scanner = ServiceNowCMDBScanner(servicenow_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "nmap":
                nmap_config = config.get("nmap_config", {})
                scanner = NmapScanner(nmap_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "cloudquery":
                cloudquery_config = config.get("cloudquery_config", {})
                scanner = CloudQueryScanner(cloudquery_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "jira_assets":
                jira_config = config.get("jira_assets_config", {})
                scanner = JiraAssetsScanner(jira_config)
                orchestrator.register_scanner(scanner)
            
            elif scanner_type == "device42":
                device42_config = config.get("device42_config", {})
                scanner = Device42Scanner(device42_config)
                orchestrator.register_scanner(scanner)
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown scanner type: {scanner_type}"
                )
        
        except ImportError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Scanner {scanner_type} not available: {str(e)}"
            )
    
    # Set initial status
    _discovery_status[tenant.id] = {
        "status": "running",
        "started_at": None,
        "completed_at": None,
        "summary": None
    }
    
    # Run discovery in background
    parallel = config.get("parallel", True)
    update_existing = config.get("update_existing", True)
    
    background_tasks.add_task(
        _run_discovery,
        orchestrator,
        db,
        tenant.id,
        parallel,
        update_existing
    )
    
    return {
        "status": "started",
        "tenant_id": str(tenant.id),
        "scanners": scanner_types,
        "message": "Discovery scan started. Check /discovery/status for progress."
    }


async def _run_discovery(
    orchestrator: DiscoveryOrchestrator,
    db: AsyncSession,
    tenant_id: UUID,
    parallel: bool,
    update_existing: bool
):
    """Background task to run discovery."""
    from datetime import datetime
    
    try:
        _discovery_status[tenant_id]["started_at"] = datetime.utcnow().isoformat()
        
        summary = await orchestrator.discover_all(
            db,
            parallel=parallel,
            update_existing=update_existing
        )
        
        _discovery_status[tenant_id].update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "summary": summary
        })
    
    except Exception as e:
        _discovery_status[tenant_id].update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e)
        })


@router.get("/discovery/status")
async def get_discovery_status(
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get status of the most recent discovery scan.
    
    Returns:
    {
        "status": "running|completed|failed",
        "started_at": "2024-01-01T00:00:00",
        "completed_at": "2024-01-01T00:05:00",
        "summary": {...}
    }
    """
    status = _discovery_status.get(tenant.id)
    
    if not status:
        return {
            "status": "no_scan",
            "message": "No discovery scans have been run yet"
        }
    
    return status


@router.get("/discovery/scanners")
async def list_available_scanners(
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    List available discovery scanners and their status.
    
    Returns information about which scanners are installed and configured.
    """
    scanners = []
    
    # Check Trivy
    try:
        trivy = TrivyScanner()
        available = await trivy.test_connection()
        scanners.append({
            "name": "trivy",
            "type": "container",
            "available": available,
            "description": "Container and Kubernetes vulnerability scanner",
            "requires": []
        })
    except Exception as e:
        scanners.append({
            "name": "trivy",
            "type": "container",
            "available": False,
            "description": "Container and Kubernetes vulnerability scanner",
            "error": str(e)
        })
    
    # Check AWS
    try:
        aws = AWSScanner()
        available = await aws.test_connection()
        scanners.append({
            "name": "aws",
            "type": "cloud",
            "available": available,
            "description": "AWS infrastructure discovery (EC2, RDS, Lambda, ECS, EKS)",
            "requires": ["boto3", "AWS credentials"]
        })
    except Exception as e:
        scanners.append({
            "name": "aws",
            "type": "cloud",
            "available": False,
            "description": "AWS infrastructure discovery",
            "error": str(e)
        })
    
    # Check Azure
    try:
        azure = AzureScanner()
        available = await azure.test_connection()
        scanners.append({
            "name": "azure",
            "type": "cloud",
            "available": available,
            "description": "Azure infrastructure discovery (VMs, SQL, AKS, App Services)",
            "requires": ["azure-identity", "azure-mgmt-*"]
        })
    except Exception as e:
        scanners.append({
            "name": "azure",
            "type": "cloud",
            "available": False,
            "description": "Azure infrastructure discovery",
            "error": str(e)
        })
    
    # Check GCP
    try:
        gcp = GCPScanner()
        available = await gcp.test_connection()
        scanners.append({
            "name": "gcp",
            "type": "cloud",
            "available": available,
            "description": "GCP infrastructure discovery (Compute Engine, Cloud SQL, GKE)",
            "requires": ["google-cloud-compute", "google-cloud-*"]
        })
    except Exception as e:
        scanners.append({
            "name": "gcp",
            "type": "cloud",
            "available": False,
            "description": "GCP infrastructure discovery",
            "error": str(e)
        })
    
    # Check Kubescape
    try:
        kubescape = KubescapeScanner()
        available = await kubescape.test_connection()
        scanners.append({
            "name": "kubescape",
            "type": "kubernetes",
            "available": available,
            "description": "Kubernetes security posture scanner (NSA, CIS, MITRE frameworks)",
            "requires": ["kubescape binary"]
        })
    except Exception as e:
        scanners.append({
            "name": "kubescape",
            "type": "kubernetes",
            "available": False,
            "description": "Kubernetes security posture scanner",
            "error": str(e)
        })
    
    # Check Nmap
    try:
        nmap = NmapScanner()
        available = await nmap.test_connection()
        scanners.append({
            "name": "nmap",
            "type": "network",
            "available": available,
            "description": "Network discovery scanner (hosts, ports, services, OS detection)",
            "requires": ["nmap binary"]
        })
    except Exception as e:
        scanners.append({
            "name": "nmap",
            "type": "network",
            "available": False,
            "description": "Network discovery scanner",
            "error": str(e)
        })
    
    # Check CloudQuery
    try:
        cloudquery = CloudQueryScanner()
        available = await cloudquery.test_connection()
        scanners.append({
            "name": "cloudquery",
            "type": "cloud",
            "available": available,
            "description": "Unified multi-cloud asset inventory via SQL",
            "requires": ["cloudquery binary", "config file"]
        })
    except Exception as e:
        scanners.append({
            "name": "cloudquery",
            "type": "cloud",
            "available": False,
            "description": "Unified multi-cloud asset inventory",
            "error": str(e)
        })
    
    # CMDB scanners (require configuration)
    scanners.append({
        "name": "servicenow",
        "type": "cmdb",
        "available": False,
        "description": "ServiceNow CMDB integration",
        "requires": ["instance_url", "username", "password or oauth_token"]
    })
    
    scanners.append({
        "name": "jira_assets",
        "type": "cmdb",
        "available": False,
        "description": "Jira Assets (Insight) CMDB integration",
        "requires": ["instance_url", "email", "api_token", "workspace_id"]
    })
    
    scanners.append({
        "name": "device42",
        "type": "cmdb",
        "available": False,
        "description": "Device42 DCIM/IPAM integration",
        "requires": ["instance_url", "username", "password"]
    })
    
    return {
        "scanners": scanners,
        "total": len(scanners),
        "available": sum(1 for s in scanners if s.get("available", False))
    }


@router.post("/discovery/test-scanner")
async def test_scanner(
    config: Dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Test a scanner configuration without running a full scan.
    
    Request body:
    {
        "scanner": "aws",
        "config": {"region": "us-east-1", ...}
    }
    """
    scanner_type = config.get("scanner")
    scanner_config = config.get("config", {})
    
    if not scanner_type:
        raise HTTPException(
            status_code=400,
            detail="Missing 'scanner' field"
        )
    
    try:
        if scanner_type == "aws":
            scanner = AWSScanner(scanner_config)
        elif scanner_type == "azure":
            scanner = AzureScanner(scanner_config)
        elif scanner_type == "gcp":
            scanner = GCPScanner(scanner_config)
        elif scanner_type == "trivy":
            scanner = TrivyScanner(scanner_config)
        elif scanner_type == "kubescape":
            scanner = KubescapeScanner(scanner_config)
        elif scanner_type == "servicenow":
            scanner = ServiceNowCMDBScanner(scanner_config)
        elif scanner_type == "nmap":
            scanner = NmapScanner(scanner_config)
        elif scanner_type == "cloudquery":
            scanner = CloudQueryScanner(scanner_config)
        elif scanner_type == "jira_assets":
            scanner = JiraAssetsScanner(scanner_config)
        elif scanner_type == "device42":
            scanner = Device42Scanner(scanner_config)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scanner: {scanner_type}"
            )
        
        # Test connection
        success = await scanner.test_connection()
        
        return {
            "scanner": scanner_type,
            "connection": "success" if success else "failed",
            "message": "Connection test completed"
        }
    
    except Exception as e:
        return {
            "scanner": scanner_type,
            "connection": "failed",
            "error": str(e)
        }


@router.post("/discovery/auto-sync/configure")
async def configure_auto_sync(
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Configure automatic discovery sync.
    
    Request body:
    {
        "enabled": true,
        "schedule": {
            "type": "interval",
            "interval_hours": 24
        },
        "scanners": ["aws", "trivy"],
        "aws_config": {...},
        "trivy_config": {...}
    }
    """
    from backend.services.discovery.auto_sync import get_auto_sync_scheduler
    
    enabled = config.get("enabled", False)
    scanners = config.get("scanners", [])
    schedule = config.get("schedule", {"type": "interval", "interval_hours": 24})
    
    # Validate schedule
    schedule_type = schedule.get("type", "interval")
    
    if schedule_type == "interval":
        interval_hours = schedule.get("interval_hours", 24)
        if interval_hours < 1:
            raise HTTPException(
                status_code=400,
                detail="Interval must be at least 1 hour"
            )
    elif schedule_type == "cron":
        if not schedule.get("cron_expr"):
            raise HTTPException(
                status_code=400,
                detail="cron_expr required for cron schedule"
            )
    
    # Extract scanner configs
    scanner_configs = {}
    for scanner in scanners:
        config_key = f"{scanner}_config"
        if config_key in config:
            scanner_configs[config_key] = config[config_key]
    
    # Configure scheduler
    scheduler = get_auto_sync_scheduler()
    scheduler.configure(
        tenant_id=str(tenant.id),
        enabled=enabled,
        scanners=scanners,
        schedule=schedule,
        scanner_configs=scanner_configs
    )
    
    # Get next run time
    next_run = scheduler.get_next_run(str(tenant.id))
    
    return {
        "status": "configured",
        "enabled": enabled,
        "scanners": scanners,
        "schedule": schedule,
        "next_run": next_run.isoformat() if next_run else None,
        "message": "Auto-sync configured successfully"
    }


@router.get("/discovery/auto-sync/status")
async def get_auto_sync_status(
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Get auto-sync configuration and status.
    """
    from backend.services.discovery.auto_sync import get_auto_sync_scheduler
    
    scheduler = get_auto_sync_scheduler()
    config = scheduler.get_config(str(tenant.id))
    next_run = scheduler.get_next_run(str(tenant.id))
    
    if not config:
        return {
            "enabled": False,
            "message": "Auto-sync not configured"
        }
    
    return {
        "enabled": True,
        "scanners": config.get("scanners", []),
        "schedule": config.get("schedule", {}),
        "next_run": next_run.isoformat() if next_run else None
    }


@router.get("/discovery/auto-sync/jobs")
async def list_auto_sync_jobs(
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    List all scheduled auto-sync jobs.
    
    (Admin-only in production - shows all tenants' jobs)
    """
    from backend.services.discovery.auto_sync import get_auto_sync_scheduler
    
    scheduler = get_auto_sync_scheduler()
    jobs = scheduler.list_jobs()
    
    # Filter to current tenant (remove this for admin view)
    tenant_jobs = [j for j in jobs if j["tenant_id"] == str(tenant.id)]
    
    return {
        "jobs": tenant_jobs,
        "total": len(tenant_jobs)
    }


@router.get("/discovery/history")
async def get_discovery_history(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get history of discovery scans.
    
    TODO: Store scan history in database
    """
    # Placeholder - return current status
    current_status = _discovery_status.get(tenant.id)
    
    return {
        "scans": [current_status] if current_status else [],
        "total": 1 if current_status else 0
    }
