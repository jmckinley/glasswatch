"""add onboarding and settings fields to tenant

Revision ID: 008
Revises: 007
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add onboarding and settings fields to tenant table."""
    
    # Add onboarding fields
    op.add_column('tenants', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('tenants', sa.Column('onboarding_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tenants', sa.Column('onboarding_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove onboarding and settings fields from tenant table."""
    
    op.drop_column('tenants', 'onboarding_data')
    op.drop_column('tenants', 'onboarding_step')
    op.drop_column('tenants', 'onboarding_completed')
