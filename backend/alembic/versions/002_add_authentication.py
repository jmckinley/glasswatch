"""Add authentication tables

Revision ID: 002_add_authentication
Revises: 001_initial_schema
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_authentication'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create user role enum
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'engineer', 'viewer', 'approver')")
    
    # Create approval status enum
    op.execute("CREATE TYPE approvalstatus AS ENUM ('pending', 'approved', 'rejected', 'expired')")
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('workos_user_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'engineer', 'viewer', 'approver', name='userrole'), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('api_key_hash', sa.String(length=255), nullable=True),
        sa.Column('api_key_last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workos_user_id')
    )
    
    # Create unique index on email per tenant
    op.create_index('idx_users_email_tenant', 'users', ['email', 'tenant_id'], unique=True)
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on audit logs for efficient querying
    op.create_index('idx_audit_logs_tenant_timestamp', 'audit_logs', ['tenant_id', 'timestamp'])
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    
    # Create approval_actions table
    op.create_table('approval_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bundle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'expired', name='approvalstatus'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('acted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundles.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for approval queries
    op.create_index('idx_approval_actions_bundle', 'approval_actions', ['bundle_id'])
    op.create_index('idx_approval_actions_status', 'approval_actions', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_approval_actions_status', table_name='approval_actions')
    op.drop_index('idx_approval_actions_bundle', table_name='approval_actions')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user', table_name='audit_logs')
    op.drop_index('idx_audit_logs_tenant_timestamp', table_name='audit_logs')
    op.drop_index('idx_users_email_tenant', table_name='users')
    
    # Drop tables
    op.drop_table('approval_actions')
    op.drop_table('audit_logs')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE approvalstatus")
    op.execute("DROP TYPE userrole")