"""
Add performance indexes

Revision ID: 007_add_performance_indexes
Revises: 006
Create Date: 2026-04-20

Adds optimized indexes for common query patterns:
- Tenant-scoped queries
- Status and severity filters
- Time-based queries
- Foreign key relationships
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_performance_indexes'
down_revision = '006_add_collaboration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes."""
    
    # Vulnerabilities table indexes
    op.create_index(
        'idx_vulnerabilities_tenant_severity',
        'vulnerabilities',
        ['tenant_id', 'severity'],
        unique=False
    )
    op.create_index(
        'idx_vulnerabilities_tenant_kev',
        'vulnerabilities',
        ['tenant_id', 'kev_status'],
        unique=False
    )
    op.create_index(
        'idx_vulnerabilities_cve',
        'vulnerabilities',
        ['cve_id'],
        unique=False
    )
    op.create_index(
        'idx_vulnerabilities_tenant_created',
        'vulnerabilities',
        ['tenant_id', 'created_at'],
        unique=False
    )
    
    # Assets table indexes
    op.create_index(
        'idx_assets_tenant_criticality',
        'assets',
        ['tenant_id', 'criticality'],
        unique=False
    )
    op.create_index(
        'idx_assets_tenant_internet_facing',
        'assets',
        ['tenant_id', 'internet_facing'],
        unique=False
    )
    op.create_index(
        'idx_assets_tenant_type',
        'assets',
        ['tenant_id', 'asset_type'],
        unique=False
    )
    
    # AssetVulnerability table indexes (for JOIN queries)
    op.create_index(
        'idx_asset_vuln_asset',
        'asset_vulnerabilities',
        ['asset_id'],
        unique=False
    )
    op.create_index(
        'idx_asset_vuln_vulnerability',
        'asset_vulnerabilities',
        ['vulnerability_id'],
        unique=False
    )
    op.create_index(
        'idx_asset_vuln_composite',
        'asset_vulnerabilities',
        ['asset_id', 'vulnerability_id'],
        unique=False
    )
    
    # PatchBundles table indexes
    op.create_index(
        'idx_patch_bundles_tenant_status',
        'patch_bundles',
        ['tenant_id', 'status'],
        unique=False
    )
    op.create_index(
        'idx_patch_bundles_created',
        'patch_bundles',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_patch_bundles_tenant_created',
        'patch_bundles',
        ['tenant_id', 'created_at'],
        unique=False
    )
    
    # Bundles table indexes
    op.create_index(
        'idx_bundles_tenant_status',
        'bundles',
        ['tenant_id', 'status'],
        unique=False
    )
    op.create_index(
        'idx_bundles_created',
        'bundles',
        ['created_at'],
        unique=False
    )
    
    # BundleItems table indexes (for bundle detail queries)
    op.create_index(
        'idx_bundle_items_bundle',
        'bundle_items',
        ['bundle_id'],
        unique=False
    )
    op.create_index(
        'idx_bundle_items_vulnerability',
        'bundle_items',
        ['vulnerability_id'],
        unique=False
    )
    
    # ApprovalRequests table indexes
    op.create_index(
        'idx_approval_requests_tenant_status',
        'approval_requests',
        ['tenant_id', 'status'],
        unique=False
    )
    op.create_index(
        'idx_approval_requests_requester',
        'approval_requests',
        ['requester_id'],
        unique=False
    )
    op.create_index(
        'idx_approval_requests_entity',
        'approval_requests',
        ['entity_type', 'entity_id'],
        unique=False
    )
    
    # ApprovalActions table indexes
    op.create_index(
        'idx_approval_actions_request',
        'approval_actions',
        ['request_id'],
        unique=False
    )
    op.create_index(
        'idx_approval_actions_actor',
        'approval_actions',
        ['actor_id'],
        unique=False
    )
    
    # Comments table indexes
    op.create_index(
        'idx_comments_entity',
        'comments',
        ['entity_type', 'entity_id'],
        unique=False
    )
    op.create_index(
        'idx_comments_author',
        'comments',
        ['author_id'],
        unique=False
    )
    op.create_index(
        'idx_comments_created',
        'comments',
        ['created_at'],
        unique=False
    )
    
    # Reactions table indexes
    op.create_index(
        'idx_reactions_comment',
        'reactions',
        ['comment_id'],
        unique=False
    )
    op.create_index(
        'idx_reactions_user',
        'reactions',
        ['user_id'],
        unique=False
    )
    
    # Activities table indexes (for audit trail queries)
    op.create_index(
        'idx_activities_tenant_created',
        'activities',
        ['tenant_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_activities_user',
        'activities',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'idx_activities_entity',
        'activities',
        ['entity_type', 'entity_id'],
        unique=False
    )
    op.create_index(
        'idx_activities_action',
        'activities',
        ['action'],
        unique=False
    )
    
    # MaintenanceWindows table indexes
    op.create_index(
        'idx_maintenance_windows_tenant',
        'maintenance_windows',
        ['tenant_id'],
        unique=False
    )
    op.create_index(
        'idx_maintenance_windows_start',
        'maintenance_windows',
        ['start_time'],
        unique=False
    )
    
    # Goals table indexes
    op.create_index(
        'idx_goals_tenant',
        'goals',
        ['tenant_id'],
        unique=False
    )
    op.create_index(
        'idx_goals_deadline',
        'goals',
        ['deadline'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    # Drop all indexes in reverse order
    
    # Goals
    op.drop_index('idx_goals_deadline', table_name='goals')
    op.drop_index('idx_goals_tenant', table_name='goals')
    
    # MaintenanceWindows
    op.drop_index('idx_maintenance_windows_start', table_name='maintenance_windows')
    op.drop_index('idx_maintenance_windows_tenant', table_name='maintenance_windows')
    
    # Activities
    op.drop_index('idx_activities_action', table_name='activities')
    op.drop_index('idx_activities_entity', table_name='activities')
    op.drop_index('idx_activities_user', table_name='activities')
    op.drop_index('idx_activities_tenant_created', table_name='activities')
    
    # Reactions
    op.drop_index('idx_reactions_user', table_name='reactions')
    op.drop_index('idx_reactions_comment', table_name='reactions')
    
    # Comments
    op.drop_index('idx_comments_created', table_name='comments')
    op.drop_index('idx_comments_author', table_name='comments')
    op.drop_index('idx_comments_entity', table_name='comments')
    
    # ApprovalActions
    op.drop_index('idx_approval_actions_actor', table_name='approval_actions')
    op.drop_index('idx_approval_actions_request', table_name='approval_actions')
    
    # ApprovalRequests
    op.drop_index('idx_approval_requests_entity', table_name='approval_requests')
    op.drop_index('idx_approval_requests_requester', table_name='approval_requests')
    op.drop_index('idx_approval_requests_tenant_status', table_name='approval_requests')
    
    # BundleItems
    op.drop_index('idx_bundle_items_vulnerability', table_name='bundle_items')
    op.drop_index('idx_bundle_items_bundle', table_name='bundle_items')
    
    # Bundles
    op.drop_index('idx_bundles_created', table_name='bundles')
    op.drop_index('idx_bundles_tenant_status', table_name='bundles')
    
    # PatchBundles
    op.drop_index('idx_patch_bundles_tenant_created', table_name='patch_bundles')
    op.drop_index('idx_patch_bundles_created', table_name='patch_bundles')
    op.drop_index('idx_patch_bundles_tenant_status', table_name='patch_bundles')
    
    # AssetVulnerability
    op.drop_index('idx_asset_vuln_composite', table_name='asset_vulnerabilities')
    op.drop_index('idx_asset_vuln_vulnerability', table_name='asset_vulnerabilities')
    op.drop_index('idx_asset_vuln_asset', table_name='asset_vulnerabilities')
    
    # Assets
    op.drop_index('idx_assets_tenant_type', table_name='assets')
    op.drop_index('idx_assets_tenant_internet_facing', table_name='assets')
    op.drop_index('idx_assets_tenant_criticality', table_name='assets')
    
    # Vulnerabilities
    op.drop_index('idx_vulnerabilities_tenant_created', table_name='vulnerabilities')
    op.drop_index('idx_vulnerabilities_cve', table_name='vulnerabilities')
    op.drop_index('idx_vulnerabilities_tenant_kev', table_name='vulnerabilities')
    op.drop_index('idx_vulnerabilities_tenant_severity', table_name='vulnerabilities')
