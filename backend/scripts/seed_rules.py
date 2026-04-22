"""
Seed default deployment rules for all tenants.

Creates 6 standard governance rules for patch deployment control.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_session
from backend.models.tenant import Tenant
from backend.models.rule import DeploymentRule


DEFAULT_RULES = [
    {
        "name": "No month-end financial deployments",
        "description": "Block deployments to financial systems during month-end close (last 3 business days)",
        "scope_type": "tag",
        "scope_value": "system:financial",
        "scope_tags": None,
        "condition_type": "time_window",
        "condition_config": {"type": "month_end", "days_before": 3},
        "action_type": "block",
        "action_config": {
            "message": "Deployment blocked: financial systems frozen during month-end close (last 3 business days)"
        },
        "priority": 100,
    },
    {
        "name": "No Friday afternoon production deploys",
        "description": "Warn about deployments to production on Friday afternoons (after 3 PM)",
        "scope_type": "environment",
        "scope_value": "production",
        "scope_tags": None,
        "condition_type": "time_window",
        "condition_config": {"type": "day_of_week", "days": ["friday"], "after_hour": 15},
        "action_type": "warn",
        "action_config": {
            "message": "Warning: Friday afternoon production deployments carry elevated risk"
        },
        "priority": 80,
    },
    {
        "name": "PCI systems require 2+ approvers",
        "description": "Require at least 2 approvers for deployments to PCI-DSS systems",
        "scope_type": "tag",
        "scope_value": "compliance:pci-dss",
        "scope_tags": None,
        "condition_type": "always",
        "condition_config": {},
        "action_type": "require_approval",
        "action_config": {
            "min_approvers": 2,
            "approval_roles": ["manager", "admin"]
        },
        "priority": 90,
    },
    {
        "name": "No quarter-end financial deploys",
        "description": "Block deployments to financial systems during quarter-end close (last 5 business days)",
        "scope_type": "tag",
        "scope_value": "system:financial",
        "scope_tags": None,
        "condition_type": "time_window",
        "condition_config": {"type": "quarter_end", "days_before": 5},
        "action_type": "block",
        "action_config": {
            "message": "Deployment blocked: financial systems frozen during quarter-end close"
        },
        "priority": 100,
    },
    {
        "name": "Critical tier risk escalation",
        "description": "Escalate risk scores for critical tier systems by 20%",
        "scope_type": "tag",
        "scope_value": "tier:critical",
        "scope_tags": None,
        "condition_type": "always",
        "condition_config": {},
        "action_type": "escalate_risk",
        "action_config": {
            "score_multiplier": 1.2,
            "reason": "Critical tier system - elevated risk scoring"
        },
        "priority": 50,
    },
    {
        "name": "Holiday deployment freeze",
        "description": "Block all deployments during US holidays",
        "scope_type": "global",
        "scope_value": None,
        "scope_tags": None,
        "condition_type": "calendar",
        "condition_config": {"type": "holiday", "calendars": ["US"]},
        "action_type": "block",
        "action_config": {
            "message": "Deployment blocked: holiday change freeze in effect"
        },
        "priority": 95,
    },
]


async def seed_tenant_rules(db: AsyncSession, tenant: Tenant):
    """Seed default rules for a single tenant."""
    print(f"Seeding deployment rules for tenant: {tenant.name}")
    
    created_count = 0
    
    for rule_data in DEFAULT_RULES:
        # Check if rule already exists (by name)
        stmt = select(DeploymentRule).where(
            DeploymentRule.tenant_id == tenant.id,
            DeploymentRule.name == rule_data["name"],
        )
        existing = await db.scalar(stmt)
        
        if existing:
            print(f"  ⏭️  {rule_data['name']} (already exists)")
            continue
        
        # Create rule
        rule = DeploymentRule(
            tenant_id=tenant.id,
            name=rule_data["name"],
            description=rule_data["description"],
            scope_type=rule_data["scope_type"],
            scope_value=rule_data["scope_value"],
            scope_tags=rule_data["scope_tags"],
            condition_type=rule_data["condition_type"],
            condition_config=rule_data["condition_config"],
            action_type=rule_data["action_type"],
            action_config=rule_data["action_config"],
            priority=rule_data["priority"],
            enabled=True,
            is_default=True,
        )
        
        db.add(rule)
        created_count += 1
        print(f"  ✅ {rule_data['name']} (priority={rule_data['priority']})")
    
    await db.commit()
    print(f"Created {created_count} rules for {tenant.name}\n")


async def main():
    """Seed rules for all tenants."""
    async with async_session() as db:
        # Get all tenants
        stmt = select(Tenant)
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        if not tenants:
            print("No tenants found. Please create a tenant first.")
            return
        
        print(f"Found {len(tenants)} tenant(s)\n")
        
        for tenant in tenants:
            await seed_tenant_rules(db, tenant)
        
        print("✨ Deployment rule seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
