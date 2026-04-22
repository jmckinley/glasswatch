"""add tags, deployment rules, and connections tables

Revision ID: 009
Revises: 008
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tags, deployment_rules, and connections tables."""
    
    # Create tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('namespace', sa.String(50), nullable=False),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.JSON(), nullable=True, default=[]),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'namespace', 'name', name='uq_tag_tenant_namespace_name')
    )
    op.create_index('ix_tags_tenant_id', 'tags', ['tenant_id'])
    op.create_index('ix_tags_namespace', 'tags', ['namespace'])
    
    # Create deployment_rules table
    op.create_table('deployment_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope_type', sa.String(50), nullable=False),
        sa.Column('scope_value', sa.String(200), nullable=True),
        sa.Column('scope_tags', postgresql.JSON(), nullable=True),
        sa.Column('condition_type', sa.String(50), nullable=False),
        sa.Column('condition_config', postgresql.JSON(), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_config', postgresql.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=100),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_deployment_rules_tenant_id', 'deployment_rules', ['tenant_id'])
    op.create_index('ix_deployment_rules_scope_type', 'deployment_rules', ['scope_type'])
    op.create_index('ix_deployment_rules_enabled', 'deployment_rules', ['enabled'])
    
    # Create connections table
    op.create_table('connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False, default={}),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_connections_tenant_id', 'connections', ['tenant_id'])


def downgrade() -> None:
    """Drop tags, deployment_rules, and connections tables."""
    
    # Drop tables in reverse order
    op.drop_index('ix_connections_tenant_id', table_name='connections')
    op.drop_table('connections')
    
    op.drop_index('ix_deployment_rules_enabled', table_name='deployment_rules')
    op.drop_index('ix_deployment_rules_scope_type', table_name='deployment_rules')
    op.drop_index('ix_deployment_rules_tenant_id', table_name='deployment_rules')
    op.drop_table('deployment_rules')
    
    op.drop_index('ix_tags_namespace', table_name='tags')
    op.drop_index('ix_tags_tenant_id', table_name='tags')
    op.drop_table('tags')
