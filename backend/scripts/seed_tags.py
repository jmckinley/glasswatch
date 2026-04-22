"""
Seed default tags for all tenants.

Creates standard tag taxonomy across system, compliance, env, tier, and team namespaces.
"""
import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_session
from backend.models.tenant import Tenant
from backend.models.tag import Tag


DEFAULT_TAGS = {
    "system": [
        ("financial", "Financial systems and transactions", "#10B981"),
        ("payment", "Payment processing systems", "#10B981"),
        ("billing", "Billing and invoicing systems", "#10B981"),
        ("ecommerce", "E-commerce platforms", "#10B981"),
        ("authentication", "Authentication and identity services", "#F59E0B"),
        ("api-gateway", "API gateways and proxies", "#3B82F6"),
        ("database", "Database systems", "#8B5CF6"),
        ("cache", "Caching layers (Redis, Memcached)", "#EC4899"),
        ("messaging", "Message queues and event buses", "#6366F1"),
        ("monitoring", "Monitoring and observability", "#14B8A6"),
        ("logging", "Logging infrastructure", "#14B8A6"),
        ("ci-cd", "CI/CD pipelines", "#F97316"),
        ("storage", "Storage systems (S3, blob storage)", "#6B7280"),
    ],
    "compliance": [
        ("pci-dss", "PCI DSS (Payment Card Industry)", "#DC2626"),
        ("hipaa", "HIPAA (Healthcare)", "#DC2626"),
        ("soc2", "SOC 2 compliance", "#DC2626"),
        ("gdpr", "GDPR (EU data protection)", "#DC2626"),
        ("fedramp", "FedRAMP (US government)", "#DC2626"),
        ("iso27001", "ISO 27001 (Information security)", "#DC2626"),
        ("nist", "NIST frameworks", "#DC2626"),
    ],
    "env": [
        ("production", "Production environment", "#EF4444"),
        ("staging", "Staging environment", "#F59E0B"),
        ("development", "Development environment", "#10B981"),
        ("test", "Test environment", "#3B82F6"),
        ("dr", "Disaster recovery environment", "#8B5CF6"),
        ("sandbox", "Sandbox environment", "#6B7280"),
    ],
    "tier": [
        ("critical", "Mission-critical systems", "#DC2626"),
        ("high", "High priority systems", "#F59E0B"),
        ("standard", "Standard priority", "#3B82F6"),
        ("low", "Low priority", "#10B981"),
        ("experimental", "Experimental/beta systems", "#6B7280"),
    ],
    "team": [
        ("engineering", "Engineering team", "#3B82F6"),
        ("devops", "DevOps team", "#10B981"),
        ("security", "Security team", "#DC2626"),
        ("platform", "Platform team", "#8B5CF6"),
        ("data", "Data team", "#F59E0B"),
        ("infrastructure", "Infrastructure team", "#6B7280"),
        ("sre", "Site Reliability Engineering", "#14B8A6"),
    ],
}


async def seed_tenant_tags(db: AsyncSession, tenant: Tenant):
    """Seed default tags for a single tenant."""
    print(f"Seeding tags for tenant: {tenant.name}")
    
    created_count = 0
    
    for namespace, tags_data in DEFAULT_TAGS.items():
        for name, description, color in tags_data:
            # Check if tag already exists
            stmt = select(Tag).where(
                Tag.tenant_id == tenant.id,
                Tag.namespace == namespace,
                Tag.name == name,
            )
            existing = await db.scalar(stmt)
            
            if existing:
                print(f"  ⏭️  {namespace}:{name} (already exists)")
                continue
            
            # Create tag
            tag = Tag(
                tenant_id=tenant.id,
                name=name,
                namespace=namespace,
                display_name=f"{namespace}:{name}",
                description=description,
                color=color,
                is_default=True,
                is_system=False,  # Users can rename but not delete
            )
            
            db.add(tag)
            created_count += 1
            print(f"  ✅ {namespace}:{name}")
    
    await db.commit()
    print(f"Created {created_count} tags for {tenant.name}\n")


async def main():
    """Seed tags for all tenants."""
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
            await seed_tenant_tags(db, tenant)
        
        print("✨ Tag seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
