"""Add audit_logs table

Revision ID: 016_add_audit_logs
Revises: 015_add_window_location_fields
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '016_add_audit_logs'
down_revision = '015_add_window_location_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create the table if it doesn't exist yet (idempotent)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
            action      VARCHAR(100) NOT NULL,
            resource_type  VARCHAR(50),
            resource_id    VARCHAR(255),
            resource_name  VARCHAR(255),
            details        JSONB NOT NULL DEFAULT '{}',
            ip_address     VARCHAR(45),
            user_agent     TEXT,
            success        BOOLEAN NOT NULL DEFAULT TRUE,
            error_message  VARCHAR(500),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Indexes (all IF NOT EXISTS so re-runnable)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs(resource_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_created_at")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_resource_type")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_tenant_id")
    op.execute("DROP TABLE IF EXISTS audit_logs")
