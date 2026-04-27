"""Add created_by columns and invites table

Revision ID: 017_add_created_by_columns
Revises: 016_add_audit_logs
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = '017_add_created_by_columns'
down_revision = '016_add_audit_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add created_by to deployment_rules
    op.execute("""
        ALTER TABLE deployment_rules
        ADD COLUMN IF NOT EXISTS created_by VARCHAR(100)
    """)

    # Add created_by to tags
    op.execute("""
        ALTER TABLE tags
        ADD COLUMN IF NOT EXISTS created_by VARCHAR(100)
    """)

    # Create invites table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            email VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'analyst',
            token VARCHAR(255) NOT NULL UNIQUE,
            created_by UUID REFERENCES users(id),
            expires_at TIMESTAMP NOT NULL,
            accepted_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    # Index for token lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_invites_token ON invites(token)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_invites_tenant_id ON invites(tenant_id)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE deployment_rules DROP COLUMN IF EXISTS created_by")
    op.execute("ALTER TABLE tags DROP COLUMN IF EXISTS created_by")
    op.execute("DROP TABLE IF EXISTS invites")
