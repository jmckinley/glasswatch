"""add password_hash to users

Revision ID: 012_add_password_hash
Revises: 011_fix_missing_columns
Create Date: 2026-04-23 18:00:00.000000

Adds password_hash column to support email/password authentication alongside OAuth.
"""
from alembic import op
import sqlalchemy as sa


revision = '012_add_password_hash'
down_revision = '011_fix_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('password_hash', sa.String(255), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('password_hash')
