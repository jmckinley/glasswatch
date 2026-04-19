"""Initial schema with all core tables

Revision ID: 001
Revises: 
Create Date: 2026-04-19 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables for Glasswatch."""
    
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('region', sa.String(20), nullable=False),
        sa.Column('encryption_key_id', sa.String(255), nullable=True),
        sa.Column('settings', postgresql.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_tenant_slug', 'tenants', ['slug'], unique=True)

    # Create vulnerabilities table
    op.create_table('vulnerabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('identifier', sa.String(50), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('cvss_vector', sa.String(150), nullable=True),
        sa.Column('epss_score', sa.Float(), nullable=True),
        sa.Column('kev_listed', sa.Boolean(), nullable=False, default=False),
        sa.Column('patch_available', sa.Boolean(), nullable=False, default=False),
        sa.Column('patch_released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vendor_advisory_url', sa.String(500), nullable=True),
        sa.Column('affected_products', postgresql.JSON(), nullable=True),
        sa.Column('cpe_list', postgresql.JSON(), nullable=True),
        sa.Column('exploit_available', sa.Boolean(), nullable=False, default=False),
        sa.Column('exploit_maturity', sa.String(20), nullable=True),
        sa.Column('exploit_sources', postgresql.JSON(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vulnerability_identifier', 'vulnerabilities', ['identifier'], unique=True)
    op.create_index('ix_vulnerability_severity', 'vulnerabilities', ['severity'])
    op.create_index('ix_vulnerability_kev', 'vulnerabilities', ['kev_listed'])
    op.create_index('ix_vulnerability_published', 'vulnerabilities', ['published_at'])

    # Create assets table
    op.create_table('assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('identifier', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('environment', sa.String(50), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('owner_team', sa.String(255), nullable=True),
        sa.Column('owner_email', sa.String(255), nullable=True),
        sa.Column('business_unit', sa.String(255), nullable=True),
        sa.Column('criticality', sa.Integer(), nullable=False, default=3),
        sa.Column('exposure', sa.String(20), nullable=False, default='ISOLATED'),
        sa.Column('os_family', sa.String(50), nullable=True),
        sa.Column('os_version', sa.String(100), nullable=True),
        sa.Column('ip_addresses', postgresql.JSON(), nullable=True),
        sa.Column('fqdn', sa.String(255), nullable=True),
        sa.Column('cloud_account_id', sa.String(255), nullable=True),
        sa.Column('cloud_region', sa.String(50), nullable=True),
        sa.Column('cloud_instance_type', sa.String(50), nullable=True),
        sa.Column('cloud_tags', postgresql.JSON(), nullable=True),
        sa.Column('installed_packages', postgresql.JSON(), nullable=True),
        sa.Column('running_services', postgresql.JSON(), nullable=True),
        sa.Column('open_ports', postgresql.JSON(), nullable=True),
        sa.Column('compliance_frameworks', postgresql.JSON(), nullable=True),
        sa.Column('compensating_controls', postgresql.JSON(), nullable=True),
        sa.Column('patch_group', sa.String(100), nullable=True),
        sa.Column('maintenance_window', sa.String(100), nullable=True),
        sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_patched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uptime_days', sa.Integer(), nullable=True),
        sa.Column('cmdb_id', sa.String(255), nullable=True),
        sa.Column('monitoring_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_asset_tenant_id', 'assets', ['tenant_id'])
    op.create_index('ix_asset_identifier', 'assets', ['tenant_id', 'identifier'], unique=True)
    op.create_index('ix_asset_type', 'assets', ['type'])
    op.create_index('ix_asset_criticality', 'assets', ['criticality'])
    op.create_index('ix_asset_exposure', 'assets', ['exposure'])

    # Create asset_vulnerabilities junction table
    op.create_table('asset_vulnerabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vulnerability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('discovered_by', sa.String(50), nullable=True),
        sa.Column('scanner_confidence', sa.Float(), nullable=True),
        sa.Column('affected_package', sa.String(255), nullable=True),
        sa.Column('installed_version', sa.String(100), nullable=True),
        sa.Column('fixed_version', sa.String(100), nullable=True),
        sa.Column('affected_path', sa.String(500), nullable=True),
        sa.Column('snapper_data', postgresql.JSON(), nullable=True),
        sa.Column('code_executed', sa.Boolean(), nullable=True),
        sa.Column('library_loaded', sa.Boolean(), nullable=True),
        sa.Column('network_reachable', sa.Boolean(), nullable=True),
        sa.Column('last_execution', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_frequency', sa.String(20), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=False, default=0),
        sa.Column('score_factors', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='ACTIVE'),
        sa.Column('patch_available', sa.Boolean(), nullable=False, default=False),
        sa.Column('patch_id', sa.String(255), nullable=True),
        sa.Column('patch_tested', sa.Boolean(), nullable=False, default=False),
        sa.Column('scheduled_patch_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_patch_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mitigation_applied', sa.Boolean(), nullable=False, default=False),
        sa.Column('mitigation_type', sa.String(100), nullable=True),
        sa.Column('mitigation_details', sa.Text(), nullable=True),
        sa.Column('mitigation_effectiveness', sa.Integer(), nullable=True),
        sa.Column('exploitability_assessment', sa.Text(), nullable=True),
        sa.Column('business_impact_assessment', sa.Text(), nullable=True),
        sa.Column('recommended_action', sa.String(50), nullable=True),
        sa.Column('bundle_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bundle_order', sa.Integer(), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['vulnerability_id'], ['vulnerabilities.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'vulnerability_id', name='uq_asset_vulnerability')
    )
    op.create_index('ix_asset_vuln_score', 'asset_vulnerabilities', ['risk_score'])
    op.create_index('ix_asset_vuln_status', 'asset_vulnerabilities', ['status'])
    op.create_index('ix_asset_vuln_asset', 'asset_vulnerabilities', ['asset_id'])
    op.create_index('ix_asset_vuln_vulnerability', 'asset_vulnerabilities', ['vulnerability_id'])

    # Create goals table
    op.create_table('goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('goal_type', sa.String(50), nullable=False),
        sa.Column('target_completion_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('target_risk_score', sa.Integer(), nullable=True),
        sa.Column('target_vulnerability_count', sa.Integer(), nullable=True),
        sa.Column('asset_scope', postgresql.JSON(), nullable=True),
        sa.Column('vulnerability_scope', postgresql.JSON(), nullable=True),
        sa.Column('excluded_assets', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('excluded_vulnerabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('risk_tolerance', sa.String(50), nullable=False, default='MEDIUM'),
        sa.Column('max_patches_per_window', sa.Integer(), nullable=True),
        sa.Column('max_downtime_minutes', sa.Integer(), nullable=True),
        sa.Column('required_testing_hours', sa.Integer(), nullable=False, default=24),
        sa.Column('maintenance_windows', postgresql.JSON(), nullable=True),
        sa.Column('blackout_dates', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='DRAFT'),
        sa.Column('last_plan_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('plan_version', sa.Integer(), nullable=False, default=0),
        sa.Column('optimization_runtime_ms', sa.Integer(), nullable=True),
        sa.Column('current_risk_score', sa.Integer(), nullable=True),
        sa.Column('current_vulnerability_count', sa.Integer(), nullable=True),
        sa.Column('patches_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('patches_remaining', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_goal_tenant_id', 'goals', ['tenant_id'])
    op.create_index('ix_goal_status', 'goals', ['status'])
    op.create_index('ix_goal_target_date', 'goals', ['target_completion_date'])

    # Create enhanced_goals table
    op.create_table('enhanced_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_impact_per_hour', sa.Numeric(12, 2), nullable=True),
        sa.Column('regulatory_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('compliance_frameworks', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tier_0_assets', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('tier_1_assets', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('tier_2_assets', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('tier_3_assets', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('risk_profile', sa.String(50), nullable=False, default='BALANCED'),
        sa.Column('prefer_automated_deployment', sa.Boolean(), nullable=False, default=False),
        sa.Column('require_change_approval', sa.Boolean(), nullable=False, default=True),
        sa.Column('batch_similar_systems', sa.Boolean(), nullable=False, default=True),
        sa.Column('enable_canary_deployment', sa.Boolean(), nullable=False, default=False),
        sa.Column('canary_percentage', sa.Integer(), nullable=True, default=10),
        sa.Column('canary_success_hours', sa.Integer(), nullable=True, default=24),
        sa.Column('auto_rollback_on_failure', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_concurrent_patches', sa.Integer(), nullable=True),
        sa.Column('team_capacity_hours_per_week', sa.Integer(), nullable=True, default=40),
        sa.Column('acceptable_failure_rate', sa.Numeric(5, 2), nullable=True, default=5.0),
        sa.Column('min_success_rate_for_auto_proceed', sa.Numeric(5, 2), nullable=True, default=95.0),
        sa.Column('use_ai_reasoning', sa.Boolean(), nullable=False, default=True),
        sa.Column('ai_model_version', sa.String(50), nullable=True, default='claude-opus-4'),
        sa.Column('ai_reasoning_prompt', sa.Text(), nullable=True),
        sa.Column('notify_on_bundle_ready', sa.Boolean(), nullable=False, default=True),
        sa.Column('notify_on_patch_complete', sa.Boolean(), nullable=False, default=True),
        sa.Column('notification_channels', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_enhanced_goal_goal_id', 'enhanced_goals', ['goal_id'])

    # Create patch_bundles table
    op.create_table('patch_bundles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('bundle_type', sa.String(50), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_estimate_minutes', sa.Integer(), nullable=True, default=240),
        sa.Column('maintenance_window_id', sa.String(100), nullable=True),
        sa.Column('total_risk_score', sa.Integer(), nullable=True),
        sa.Column('highest_risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_assessment', sa.Text(), nullable=True),
        sa.Column('patch_weather_score', sa.Integer(), nullable=True),
        sa.Column('weather_forecast', sa.String(20), nullable=True),
        sa.Column('weather_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('asset_count', sa.Integer(), nullable=False, default=0),
        sa.Column('vulnerability_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_patch_size_mb', sa.Integer(), nullable=True),
        sa.Column('affected_environments', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('affected_asset_types', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('affected_teams', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('depends_on_bundles', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('blocks_bundles', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('implementation_steps', postgresql.JSON(), nullable=True),
        sa.Column('verification_steps', postgresql.JSON(), nullable=True),
        sa.Column('rollback_plan', sa.Text(), nullable=True),
        sa.Column('requires_testing', sa.Boolean(), nullable=False, default=True),
        sa.Column('test_environment', sa.String(100), nullable=True),
        sa.Column('test_duration_hours', sa.Integer(), nullable=True, default=24),
        sa.Column('test_success_criteria', postgresql.JSON(), nullable=True),
        sa.Column('change_ticket_id', sa.String(255), nullable=True),
        sa.Column('change_ticket_url', sa.String(500), nullable=True),
        sa.Column('approval_required', sa.Boolean(), nullable=False, default=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='PLANNED'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('patches_attempted', sa.Integer(), nullable=False, default=0),
        sa.Column('patches_successful', sa.Integer(), nullable=False, default=0),
        sa.Column('patches_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('failure_details', postgresql.JSON(), nullable=True),
        sa.Column('rollback_initiated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('optimization_factors', postgresql.JSON(), nullable=True),
        sa.Column('notifications_sent', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bundle_goal_id', 'patch_bundles', ['goal_id'])
    op.create_index('ix_bundle_scheduled', 'patch_bundles', ['scheduled_for'])
    op.create_index('ix_bundle_status', 'patch_bundles', ['status'])
    op.create_index('ix_bundle_risk', 'patch_bundles', ['total_risk_score'])

    # Create bundle_patches table
    op.create_table('bundle_patches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('bundle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vulnerability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_order', sa.Integer(), nullable=False, default=0),
        sa.Column('depends_on', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('patch_id', sa.String(255), nullable=True),
        sa.Column('patch_size_mb', sa.Integer(), nullable=True),
        sa.Column('estimated_install_time_minutes', sa.Integer(), nullable=True, default=10),
        sa.Column('requires_reboot', sa.Boolean(), nullable=False, default=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='PENDING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('output_log', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('verification_method', sa.String(100), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['bundle_id'], ['patch_bundles.id'], ),
        sa.ForeignKeyConstraint(['vulnerability_id'], ['vulnerabilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bundle_patch_bundle', 'bundle_patches', ['bundle_id'])
    op.create_index('ix_bundle_patch_asset', 'bundle_patches', ['asset_id'])
    op.create_index('ix_bundle_patch_order', 'bundle_patches', ['bundle_id', 'execution_order'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('ix_bundle_patch_order', table_name='bundle_patches')
    op.drop_index('ix_bundle_patch_asset', table_name='bundle_patches')
    op.drop_index('ix_bundle_patch_bundle', table_name='bundle_patches')
    op.drop_table('bundle_patches')
    
    op.drop_index('ix_bundle_risk', table_name='patch_bundles')
    op.drop_index('ix_bundle_status', table_name='patch_bundles')
    op.drop_index('ix_bundle_scheduled', table_name='patch_bundles')
    op.drop_index('ix_bundle_goal_id', table_name='patch_bundles')
    op.drop_table('patch_bundles')
    
    op.drop_index('ix_enhanced_goal_goal_id', table_name='enhanced_goals')
    op.drop_table('enhanced_goals')
    
    op.drop_index('ix_goal_target_date', table_name='goals')
    op.drop_index('ix_goal_status', table_name='goals')
    op.drop_index('ix_goal_tenant_id', table_name='goals')
    op.drop_table('goals')
    
    op.drop_index('ix_asset_vuln_vulnerability', table_name='asset_vulnerabilities')
    op.drop_index('ix_asset_vuln_asset', table_name='asset_vulnerabilities')
    op.drop_index('ix_asset_vuln_status', table_name='asset_vulnerabilities')
    op.drop_index('ix_asset_vuln_score', table_name='asset_vulnerabilities')
    op.drop_table('asset_vulnerabilities')
    
    op.drop_index('ix_asset_exposure', table_name='assets')
    op.drop_index('ix_asset_criticality', table_name='assets')
    op.drop_index('ix_asset_type', table_name='assets')
    op.drop_index('ix_asset_identifier', table_name='assets')
    op.drop_index('ix_asset_tenant_id', table_name='assets')
    op.drop_table('assets')
    
    op.drop_index('ix_vulnerability_published', table_name='vulnerabilities')
    op.drop_index('ix_vulnerability_kev', table_name='vulnerabilities')
    op.drop_index('ix_vulnerability_severity', table_name='vulnerabilities')
    op.drop_index('ix_vulnerability_identifier', table_name='vulnerabilities')
    op.drop_table('vulnerabilities')
    
    op.drop_index('ix_tenant_slug', table_name='tenants')
    op.drop_table('tenants')