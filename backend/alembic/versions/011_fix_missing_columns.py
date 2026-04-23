"""fix missing columns: onboarding fields + oauth columns

Revision ID: 011_fix_missing_columns
Revises: 010_add_notifications
Create Date: 2026-04-23 12:13:00.000000

Adds columns that were added to models but never had migrations:
- tenants: onboarding_completed, onboarding_step, onboarding_data (from 008)
- users: oauth_provider, oauth_id (added in Sprint 10)
- maintenance_windows: priority, asset_group, service_name, is_default
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '011_fix_missing_columns'
down_revision = '010_add_notifications'
branch_labels = None
depends_on = None


def upgrade():
    # tenants: onboarding fields (already handled in 008 for new installs,
    # this ensures existing installs have them)
    with op.batch_alter_table('tenants') as batch_op:
        batch_op.add_column(
            sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false')
        )
        batch_op.add_column(
            sa.Column('onboarding_step', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('onboarding_data', postgresql.JSON(astext_type=sa.Text()), nullable=True)
        )

    # users: oauth columns
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('oauth_provider', sa.String(50), nullable=True)
        )
        batch_op.add_column(
            sa.Column('oauth_id', sa.String(255), nullable=True)
        )

    # maintenance_windows: columns added in Sprint 10 models but missing migration
    with op.batch_alter_table('maintenance_windows') as batch_op:
        batch_op.add_column(
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('asset_group', sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column('service_name', sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false')
        )


def downgrade():
    with op.batch_alter_table('maintenance_windows') as batch_op:
        batch_op.drop_column('is_default')
        batch_op.drop_column('service_name')
        batch_op.drop_column('asset_group')
        batch_op.drop_column('priority')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('oauth_id')
        batch_op.drop_column('oauth_provider')

    with op.batch_alter_table('tenants') as batch_op:
        batch_op.drop_column('onboarding_data')
        batch_op.drop_column('onboarding_step')
        batch_op.drop_column('onboarding_completed')
