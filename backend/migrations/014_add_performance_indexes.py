"""
014_add_performance_indexes.py

Performance indexes for high-volume queries at 500+ assets / 5000+ vulnerabilities.

Indexes already confirmed present (skipped here):
  - ix_asset_vuln_asset          (asset_vulnerabilities.asset_id)
  - ix_asset_vuln_vulnerability  (asset_vulnerabilities.vulnerability_id)
  - ix_asset_vuln_status         (asset_vulnerabilities.status)
  - ix_asset_vuln_score          (asset_vulnerabilities.risk_score)
  - ix_vulnerability_severity    (vulnerabilities.severity)
  - ix_vulnerability_kev         (vulnerabilities.kev_listed)
  - ix_notification_tenant_user_read (notifications.tenant_id, user_id, read)
  - bundle indexes (tenant_id, status, scheduled_for)

New indexes added by this migration:
  - ix_vulnerability_cvss_score  — ORDER BY cvss_score DESC in vuln list
  - ix_vulnerability_epss_score  — ORDER BY epss_score DESC in risk queries
  - ix_vulnerability_patch_available — filter patch_available=True
"""
from alembic import op


def upgrade():
    # Vulnerabilities: sorting and filtering columns used in list/detail queries
    op.create_index(
        "ix_vulnerability_cvss_score",
        "vulnerabilities",
        ["cvss_score"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_vulnerability_epss_score",
        "vulnerabilities",
        ["epss_score"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_vulnerability_patch_available",
        "vulnerabilities",
        ["patch_available"],
        if_not_exists=True,
    )


def downgrade():
    op.drop_index("ix_vulnerability_cvss_score", table_name="vulnerabilities", if_exists=True)
    op.drop_index("ix_vulnerability_epss_score", table_name="vulnerabilities", if_exists=True)
    op.drop_index("ix_vulnerability_patch_available", table_name="vulnerabilities", if_exists=True)
