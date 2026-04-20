"""Add approval workflow tables

Revision ID: 004
Revises: 002
Create Date: 2026-04-20 18:12:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add approval workflow tables."""
    
    # Create RiskLevel enum
    risk_level_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical',
        name='risklevel',
        create_type=True
    )
    risk_level_enum.create(op.get_bind(), checkfirst=True)
    
    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bundle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_level', risk_level_enum, nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'expired', name='approvalstatus'), nullable=False),
        sa.Column('required_approvals', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('current_approvals', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('impact_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on approval_requests
    op.create_index('ix_approval_requests_bundle_id', 'approval_requests', ['bundle_id'])
    op.create_index('ix_approval_requests_tenant_id', 'approval_requests', ['tenant_id'])
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('ix_approval_requests_expires_at', 'approval_requests', ['expires_at'])
    
    # Create approval_policies table
    op.create_table(
        'approval_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_level', risk_level_enum, nullable=False),
        sa.Column('required_approvals', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('required_roles', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_approve_low_risk', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escalation_hours', sa.Integer(), nullable=False, server_default='48'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on approval_policies
    op.create_index('ix_approval_policies_tenant_id', 'approval_policies', ['tenant_id'])
    op.create_index('ix_approval_policies_risk_level', 'approval_policies', ['risk_level'])
    
    # Add approval_request_id column to approval_actions table
    op.add_column(
        'approval_actions',
        sa.Column('approval_request_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_approval_actions_approval_request_id',
        'approval_actions',
        'approval_requests',
        ['approval_request_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on approval_request_id
    op.create_index('ix_approval_actions_approval_request_id', 'approval_actions', ['approval_request_id'])


def downgrade() -> None:
    """Remove approval workflow tables."""
    
    # Drop indexes
    op.drop_index('ix_approval_actions_approval_request_id', table_name='approval_actions')
    op.drop_index('ix_approval_policies_risk_level', table_name='approval_policies')
    op.drop_index('ix_approval_policies_tenant_id', table_name='approval_policies')
    op.drop_index('ix_approval_requests_expires_at', table_name='approval_requests')
    op.drop_index('ix_approval_requests_status', table_name='approval_requests')
    op.drop_index('ix_approval_requests_tenant_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_bundle_id', table_name='approval_requests')
    
    # Drop foreign key and column
    op.drop_constraint('fk_approval_actions_approval_request_id', 'approval_actions', type_='foreignkey')
    op.drop_column('approval_actions', 'approval_request_id')
    
    # Drop tables
    op.drop_table('approval_policies')
    op.drop_table('approval_requests')
    
    # Drop enum types
    sa.Enum(name='risklevel').drop(op.get_bind(), checkfirst=True)
