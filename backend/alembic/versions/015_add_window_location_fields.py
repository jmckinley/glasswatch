"""Add datacenter and geography fields to maintenance_windows

Revision ID: 015_add_window_location_fields
Revises: 014
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '015_add_window_location_fields'
down_revision = '013_add_invites'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'maintenance_windows',
        sa.Column('datacenter', sa.String(100), nullable=True)
    )
    op.add_column(
        'maintenance_windows',
        sa.Column('geography', sa.String(100), nullable=True)
    )


def downgrade():
    op.drop_column('maintenance_windows', 'datacenter')
    op.drop_column('maintenance_windows', 'geography')
