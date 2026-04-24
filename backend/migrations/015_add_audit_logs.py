"""
015_add_audit_logs.py

Creates the audit_logs table (if not already present) and adds any columns
that were introduced in the full audit log feature:
  - resource_name   VARCHAR(255)
  - success         BOOLEAN NOT NULL DEFAULT TRUE
  - error_message   VARCHAR(500)
  - created_at      TIMESTAMPTZ  (renamed from timestamp; column is re-created
                                  if the old name exists)

Indexes added:
  - ix_audit_logs_tenant_id
  - ix_audit_logs_action
  - ix_audit_logs_resource_type
  - ix_audit_logs_created_at
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ------------------------------------------------------------------
    # Create the table if it doesn't exist yet.
    # The IF NOT EXISTS guard makes this migration re-runnable.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Add columns that may be missing on existing tables (idempotent).
    # ------------------------------------------------------------------
    _add_column_if_missing("audit_logs", "resource_name",
                           sa.String(255), nullable=True)
    _add_column_if_missing("audit_logs", "success",
                           sa.Boolean(), nullable=False,
                           server_default=sa.text("TRUE"))
    _add_column_if_missing("audit_logs", "error_message",
                           sa.String(500), nullable=True)

    # If the old `timestamp` column still exists, create `created_at`
    # with the same data and drop `timestamp`.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'timestamp'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'created_at'
            ) THEN
                ALTER TABLE audit_logs
                    RENAME COLUMN "timestamp" TO created_at;
            END IF;
        END $$;
    """)

    # ------------------------------------------------------------------
    # Indexes (all IF NOT EXISTS so re-runnable)
    # ------------------------------------------------------------------
    op.create_index("ix_audit_logs_tenant_id",    "audit_logs", ["tenant_id"],    if_not_exists=True)
    op.create_index("ix_audit_logs_action",        "audit_logs", ["action"],       if_not_exists=True)
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"],if_not_exists=True)
    op.create_index("ix_audit_logs_created_at",    "audit_logs", ["created_at"],   if_not_exists=True)


def downgrade():
    op.drop_index("ix_audit_logs_created_at",    table_name="audit_logs", if_exists=True)
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs", if_exists=True)
    op.drop_index("ix_audit_logs_action",        table_name="audit_logs", if_exists=True)
    op.drop_index("ix_audit_logs_tenant_id",     table_name="audit_logs", if_exists=True)
    op.drop_table("audit_logs")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _add_column_if_missing(table, column_name, col_type, nullable=True,
                            server_default=None):
    """Add a column only when it doesn't already exist."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{column_name}'
            ) THEN
                ALTER TABLE {table} ADD COLUMN {column_name} TEXT;
            END IF;
        END $$;
        """
    )
