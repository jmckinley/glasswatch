"""add invites table

Revision ID: 013_add_invites
Revises: 012_add_password_hash
Create Date: 2026-04-24 12:00:00.000000

Adds the invites table to support team invite flows.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '013_add_invites'
down_revision = '012_add_password_hash'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invites',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='analyst'),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_invites_token', 'invites', ['token'], unique=True)
    op.create_index('ix_invites_tenant_id', 'invites', ['tenant_id'])


def downgrade():
    op.drop_index('ix_invites_tenant_id', table_name='invites')
    op.drop_index('ix_invites_token', table_name='invites')
    op.drop_table('invites')
