"""
Auto-sync scheduler for periodic asset discovery.

Manages scheduled discovery scans in the background.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

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


logger = logging.getLogger(__name__)


class AutoSyncScheduler:
    """
    Scheduler for automatic periodic asset discovery.
    
    Runs discovery scans on a schedule (hourly, daily, weekly, etc.)
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.configs: Dict[str, Dict[str, Any]] = {}  # tenant_id -> config
        self.scheduler.start()
    
    def configure(
        self,
        tenant_id: str,
        enabled: bool,
        scanners: list[str],
        schedule: Dict[str, Any],
        scanner_configs: Dict[str, Any]
    ):
        """
        Configure auto-sync for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            enabled: Whether auto-sync is enabled
            scanners: List of scanner types to run
            schedule: Schedule configuration
                {
                    "type": "interval" | "cron",
                    "interval_hours": 24,  # for interval
                    "cron_expr": "0 0 * * *"  # for cron
                }
            scanner_configs: Configuration for each scanner
        """
        job_id = f"discovery_autosync_{tenant_id}"
        
        # Remove existing job if it exists
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        if not enabled:
            self.configs.pop(tenant_id, None)
            logger.info(f"Auto-sync disabled for tenant {tenant_id}")
            return
        
        # Store config
        self.configs[tenant_id] = {
            "scanners": scanners,
            "scanner_configs": scanner_configs,
            "schedule": schedule
        }
        
        # Create trigger
        schedule_type = schedule.get("type", "interval")
        
        if schedule_type == "interval":
            interval_hours = schedule.get("interval_hours", 24)
            trigger = IntervalTrigger(hours=interval_hours)
        elif schedule_type == "cron":
            cron_expr = schedule.get("cron_expr", "0 0 * * *")
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
        
        # Schedule job
        self.scheduler.add_job(
            self._run_auto_sync,
            trigger=trigger,
            id=job_id,
            args=[tenant_id],
            replace_existing=True
        )
        
        logger.info(f"Auto-sync configured for tenant {tenant_id}: {schedule}")
    
    async def _run_auto_sync(self, tenant_id: str):
        """Run scheduled discovery scan."""
        config = self.configs.get(tenant_id)
        
        if not config:
            logger.warning(f"No config found for tenant {tenant_id}")
            return
        
        logger.info(f"Running auto-sync for tenant {tenant_id}")
        
        try:
            # Get database session (TODO: inject properly)
            from backend.db.session import async_session_maker
            
            async with async_session_maker() as db:
                # Initialize orchestrator
                orchestrator = DiscoveryOrchestrator(tenant_id)
                
                # Register scanners
                scanners = config["scanners"]
                scanner_configs = config["scanner_configs"]
                
                for scanner_type in scanners:
                    try:
                        scanner = self._create_scanner(
                            scanner_type,
                            scanner_configs.get(f"{scanner_type}_config", {})
                        )
                        orchestrator.register_scanner(scanner)
                    except Exception as e:
                        logger.error(f"Failed to register scanner {scanner_type}: {e}")
                
                # Run discovery
                result = await orchestrator.discover_all(db, parallel=True, update_existing=True)
                
                logger.info(
                    f"Auto-sync completed for tenant {tenant_id}: "
                    f"{result['assets_discovered']} assets discovered, "
                    f"{result['assets_created']} created, "
                    f"{result['assets_updated']} updated"
                )
        
        except Exception as e:
            logger.error(f"Auto-sync failed for tenant {tenant_id}: {e}", exc_info=True)
    
    def _create_scanner(self, scanner_type: str, config: Dict[str, Any]):
        """Create scanner instance."""
        scanner_map = {
            "aws": AWSScanner,
            "azure": AzureScanner,
            "gcp": GCPScanner,
            "trivy": TrivyScanner,
            "kubescape": KubescapeScanner,
            "servicenow": ServiceNowCMDBScanner,
            "nmap": NmapScanner,
            "cloudquery": CloudQueryScanner,
            "jira_assets": JiraAssetsScanner,
            "device42": Device42Scanner
        }
        
        scanner_class = scanner_map.get(scanner_type)
        if not scanner_class:
            raise ValueError(f"Unknown scanner type: {scanner_type}")
        
        return scanner_class(config)
    
    def get_next_run(self, tenant_id: str) -> Optional[datetime]:
        """Get next scheduled run time for a tenant."""
        job_id = f"discovery_autosync_{tenant_id}"
        job = self.scheduler.get_job(job_id)
        
        if job:
            return job.next_run_time
        
        return None
    
    def get_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get auto-sync configuration for a tenant."""
        return self.configs.get(tenant_id)
    
    def list_jobs(self) -> list[Dict[str, Any]]:
        """List all scheduled jobs."""
        jobs = []
        
        for job in self.scheduler.get_jobs():
            tenant_id = job.args[0] if job.args else None
            config = self.configs.get(tenant_id, {})
            
            jobs.append({
                "job_id": job.id,
                "tenant_id": tenant_id,
                "next_run": job.next_run_time,
                "scanners": config.get("scanners", []),
                "schedule": config.get("schedule", {})
            })
        
        return jobs
    
    def shutdown(self):
        """Shutdown scheduler."""
        self.scheduler.shutdown()


# Global scheduler instance
_auto_sync_scheduler: Optional[AutoSyncScheduler] = None


def get_auto_sync_scheduler() -> AutoSyncScheduler:
    """Get or create global auto-sync scheduler."""
    global _auto_sync_scheduler
    
    if _auto_sync_scheduler is None:
        _auto_sync_scheduler = AutoSyncScheduler()
    
    return _auto_sync_scheduler
