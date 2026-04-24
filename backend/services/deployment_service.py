"""
Deployment Service - Orchestrates patch bundle execution.

Handles bundle deployment workflow including:
- Approval validation
- Rule checking
- Status tracking
- Audit logging
- Notifications
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.bundle import Bundle
from backend.models.bundle_item import BundleItem
from backend.models.audit_log import AuditLog
from backend.services.rule_engine import rule_engine, RuleEvaluationResult


class DeploymentService:
    """
    Service for executing patch bundles.
    
    Orchestrates the entire deployment workflow from validation
    through execution and reporting.
    """
    
    async def execute_bundle(
        self,
        db: AsyncSession,
        bundle_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute a patch bundle.
        
        Workflow:
        1. Validate bundle is approved
        2. Check deployment rules
        3. Update bundle status to in_progress
        4. Execute each bundle item
        5. Update final status and metrics
        6. Create audit log
        7. Send notifications
        
        Args:
            db: Database session
            bundle_id: Bundle ID to execute
            tenant_id: Tenant ID (for security)
            user_id: User initiating deployment (optional)
        
        Returns:
            Execution result with status and metrics
        """
        # 1. Load bundle with items
        result = await db.execute(
            select(Bundle)
            .where(
                and_(
                    Bundle.id == bundle_id,
                    Bundle.tenant_id == tenant_id
                )
            )
        )
        bundle = result.scalar_one_or_none()
        
        if not bundle:
            return {
                "success": False,
                "error": "Bundle not found"
            }
        
        # 2. Validate bundle is approved
        if bundle.status != "approved":
            return {
                "success": False,
                "error": f"Bundle must be approved before execution (current status: {bundle.status})"
            }
        
        # 3. Check deployment rules
        rule_result = await self._check_deployment_rules(db, bundle, tenant_id)
        
        if rule_result.verdict == "block":
            # Log blocked deployment
            await self._create_audit_log(
                db,
                tenant_id,
                user_id,
                "bundle_deployment_blocked",
                {
                    "bundle_id": str(bundle_id),
                    "bundle_name": bundle.name,
                    "reason": "deployment_rules",
                    "rules": [m.rule_name for m in rule_result.matches]
                }
            )
            
            return {
                "success": False,
                "error": "Deployment blocked by rules",
                "blocked_by": [
                    {
                        "rule": m.rule_name,
                        "message": m.message
                    }
                    for m in rule_result.matches
                    if m.action_type == "block"
                ]
            }
        
        # 4. Update bundle status to in_progress
        bundle.status = "in_progress"
        bundle.started_at = datetime.now(timezone.utc)
        await db.commit()
        
        # 5. Load bundle items
        items_result = await db.execute(
            select(BundleItem)
            .where(BundleItem.bundle_id == bundle_id)
            .order_by(BundleItem.priority.asc().nullslast())
        )
        items = items_result.scalars().all()
        
        # 6. Execute each item
        success_count = 0
        failure_count = 0
        
        for item in items:
            item_result = await self._execute_bundle_item(db, item, bundle)
            
            if item_result["success"]:
                success_count += 1
            else:
                failure_count += 1
        
        # 7. Update final bundle status
        completed_at = datetime.now(timezone.utc)
        bundle.completed_at = completed_at
        bundle.success_count = success_count
        bundle.failure_count = failure_count
        
        if bundle.started_at:
            duration = (completed_at - bundle.started_at).total_seconds() / 60
            bundle.actual_duration_minutes = int(duration)
        
        # Set final status
        if failure_count == 0:
            bundle.status = "completed"
        elif success_count == 0:
            bundle.status = "failed"
        else:
            bundle.status = "completed"  # Partial success still marked as completed
        
        await db.commit()
        
        # 8. Create audit log
        await self._create_audit_log(
            db,
            tenant_id,
            user_id,
            "bundle_deployment_completed",
            {
                "bundle_id": str(bundle_id),
                "bundle_name": bundle.name,
                "status": bundle.status,
                "success_count": success_count,
                "failure_count": failure_count,
                "duration_minutes": bundle.actual_duration_minutes
            }
        )
        
        # 9. Send notifications (if configured)
        await self._send_notifications(db, bundle, success_count, failure_count)
        
        return {
            "success": True,
            "bundle_id": str(bundle_id),
            "status": bundle.status,
            "success_count": success_count,
            "failure_count": failure_count,
            "total_items": len(items),
            "duration_minutes": bundle.actual_duration_minutes
        }
    
    async def _check_deployment_rules(
        self,
        db: AsyncSession,
        bundle: Bundle,
        tenant_id: UUID
    ) -> RuleEvaluationResult:
        """
        Check deployment rules for the bundle.
        
        Args:
            db: Database session
            bundle: Bundle being deployed
            tenant_id: Tenant ID
        
        Returns:
            RuleEvaluationResult with verdict
        """
        # Evaluate rules using the rule engine
        result = await rule_engine.evaluate_deployment(
            db=db,
            tenant_id=str(tenant_id),
            bundle=bundle,
            # Could pass additional context here:
            # - assets involved
            # - tags from assets
            # - environment
            # - target maintenance window
        )
        
        return result
    
    async def _execute_bundle_item(
        self,
        db: AsyncSession,
        item: BundleItem,
        bundle: Bundle
    ) -> Dict[str, Any]:
        """
        Execute a single bundle item (patch one vulnerability on one asset).
        
        In production, this would integrate with actual patch deployment systems:
        - Ansible
        - AWS Systems Manager
        - SCCM
        - Puppet/Chef
        - Custom scripts
        
        For now, we simulate the execution with status tracking.
        
        Args:
            db: Database session
            item: BundleItem to execute
            bundle: Parent bundle
        
        Returns:
            Execution result
        """
        # Update item status
        item.status = "in_progress"
        item.started_at = datetime.now(timezone.utc)
        await db.commit()
        
        # SIMULATION: In production, this would actually deploy the patch
        # For now, we auto-succeed after recording the attempt
        
        # Simulate execution time (would be real deployment in production)
        import asyncio
        await asyncio.sleep(0.1)  # Simulate brief work
        
        # Mark as successful (in production, check actual deployment result)
        item.status = "success"
        item.completed_at = datetime.now(timezone.utc)
        
        if item.started_at:
            duration = (item.completed_at - item.started_at).total_seconds()
            item.duration_seconds = int(duration)
        
        # Record output (would be actual deployment logs in production)
        item.output = "Simulated patch deployment completed successfully"
        
        await db.commit()
        
        # Update bundle completion percentage
        await self._update_bundle_progress(db, bundle)
        
        return {
            "success": True,
            "item_id": str(item.id),
            "status": item.status
        }
    
    async def _update_bundle_progress(
        self,
        db: AsyncSession,
        bundle: Bundle
    ) -> None:
        """
        Update bundle completion percentage based on completed items.
        
        Args:
            db: Database session
            bundle: Bundle to update
        """
        # Count completed items
        result = await db.execute(
            select(BundleItem)
            .where(BundleItem.bundle_id == bundle.id)
        )
        items = result.scalars().all()
        
        if not items:
            return
        
        completed = sum(
            1 for item in items
            if item.status in ["success", "failed", "skipped"]
        )
        
        percentage = int((completed / len(items)) * 100)
        
        # Store in metadata
        if not bundle.execution_log:
            bundle.execution_log = {}
        
        bundle.execution_log["completion_percentage"] = percentage
        bundle.execution_log["completed_items"] = completed
        bundle.execution_log["total_items"] = len(items)
        
        await db.commit()
    
    async def _create_audit_log(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID],
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Create audit log entry.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            user_id: User ID (optional)
            event_type: Type of event
            details: Event details
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
        
        db.add(audit_log)
        await db.commit()
    
    async def _send_notifications(
        self,
        db: AsyncSession,
        bundle: Bundle,
        success_count: int,
        failure_count: int
    ) -> None:
        """
        Send notifications about deployment completion.

        Fires PATCH_COMPLETE or PATCH_FAILED notification via notification_service,
        which routes to Slack, Teams, email, and in-app based on tenant settings.
        """
        try:
            from backend.services.notifications import notification_service, NotificationType
            from backend.models.tenant import Tenant
            from sqlalchemy import select as _select

            # Load tenant for notification routing config
            result = await db.execute(
                _select(Tenant).where(Tenant.id == bundle.tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return

            if bundle.status in ("completed", "failed"):
                total = success_count + failure_count
                if bundle.status == "completed":
                    notif_type = NotificationType.PATCH_SUCCESS
                    title = f"✅ Bundle complete: {bundle.name}"
                    priority = "normal" if failure_count == 0 else "high"
                else:
                    notif_type = NotificationType.PATCH_FAILED
                    title = f"❌ Bundle failed: {bundle.name}"
                    priority = "high"

                message = (
                    f"{bundle.name}: {success_count}/{total} patches applied"
                    + (f", {failure_count} failed" if failure_count else "")
                    + "."
                )

                data = {
                    "bundle_id": str(bundle.id),
                    "link": f"/bundles/{bundle.id}",
                    "action_url": f"/bundles/{bundle.id}",
                    "action_text": "View Bundle",
                }

                await notification_service.send_notification(
                    tenant=tenant,
                    notification_type=notif_type,
                    title=title,
                    message=message,
                    data=data,
                    priority=priority,
                )
        except Exception as e:
            import logging
            logging.warning(f"Failed to send bundle completion notification: {e}")


# Global service instance
deployment_service = DeploymentService()
