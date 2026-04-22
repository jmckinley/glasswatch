"""add notifications

Revision ID: 010_add_notifications
Revises: 009_add_tags_rules_connections
Create Date: 2025-04-22 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_notifications'
down_revision = '009_add_tags_rules_connections'
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('channel', sa.String(length=50), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_notification_tenant_user_read', 'notifications', ['tenant_id', 'user_id', 'read'])
    op.create_index('ix_notification_created', 'notifications', ['created_at'])
    op.create_index(op.f('ix_notifications_tenant_id'), 'notifications', ['tenant_id'])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'])
    op.create_index(op.f('ix_notifications_read'), 'notifications', ['read'])


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_notifications_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_tenant_id'), table_name='notifications')
    op.drop_index('ix_notification_created', table_name='notifications')
    op.drop_index('ix_notification_tenant_user_read', table_name='notifications')
    
    # Drop table
    op.drop_table('notifications')
