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
from backend.core.auth import get_current_tenant
from backend.services.discovery.orchestrator import DiscoveryOrchestrator
from backend.services.discovery.trivy_scanner import TrivyScanner
from backend.services.discovery.aws_scanner import AWSScanner


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
            
            elif scanner_type == "trivy":
                trivy_config = config.get("trivy_config", {})
                scanner = TrivyScanner(trivy_config)
                orchestrator.register_scanner(scanner)
            
            # Add more scanners here as they're implemented
            # elif scanner_type == "azure":
            #     scanner = AzureScanner(config.get("azure_config", {}))
            #     orchestrator.register_scanner(scanner)
            
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
    
    # Add more scanners as they're implemented
    
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
        elif scanner_type == "trivy":
            scanner = TrivyScanner(scanner_config)
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
        "interval_hours": 24,
        "scanners": ["aws", "trivy"],
        "aws_config": {...},
        "trivy_config": {...}
    }
    
    TODO: Integrate with job scheduler (Celery, cron, etc.)
    """
    enabled = config.get("enabled", False)
    interval_hours = config.get("interval_hours", 24)
    
    if interval_hours < 1:
        raise HTTPException(
            status_code=400,
            detail="Interval must be at least 1 hour"
        )
    
    # TODO: Store in database and integrate with scheduler
    
    return {
        "status": "configured",
        "enabled": enabled,
        "interval_hours": interval_hours,
        "message": "Auto-sync configuration saved (scheduler integration pending)"
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
