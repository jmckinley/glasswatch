"""
Seed script: generates realistic audit log entries for testing.

Usage:
    cd /home/node/glasswatch
    PYTHONPATH=/home/node/glasswatch python3 backend/scripts/seed_audit_log.py

Creates 100+ audit events across all categories, spread over the last 30 days.
Requires a running PostgreSQL instance (DATABASE_URL must be set or configured
in the app settings).
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running as `python3 backend/scripts/seed_audit_log.py` from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models.audit_log import AuditLog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)

SAMPLE_TENANT_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
SAMPLE_USER_IDS = [
    uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
    uuid.UUID("550e8400-e29b-41d4-a716-446655440002"),
    uuid.UUID("550e8400-e29b-41d4-a716-446655440003"),
]
SAMPLE_IPS = [
    "10.0.1.10",
    "10.0.1.20",
    "192.168.1.50",
    "203.0.113.42",
    "198.51.100.7",
]


def _rand_ts(days_back: int = 30) -> datetime:
    """Return a random UTC timestamp within the last `days_back` days."""
    offset_secs = random.randint(0, days_back * 86400)
    return NOW - timedelta(seconds=offset_secs)


def _pick(seq):
    return random.choice(seq)


def _make_entry(
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_name: str | None = None,
    user_id=None,
    details: dict | None = None,
    success: bool = True,
    error_message: str | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=SAMPLE_TENANT_ID,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or str(uuid.uuid4()),
        resource_name=resource_name,
        details=details or {},
        ip_address=_pick(SAMPLE_IPS),
        user_agent="Mozilla/5.0 (Glasswatch Seed)",
        success=success,
        error_message=error_message,
    )
    # Override created_at after construction (server_default won't apply here)
    entry.created_at = created_at or _rand_ts()
    return entry


# ---------------------------------------------------------------------------
# Category generators
# ---------------------------------------------------------------------------

def _bundle_events(n: int = 20) -> list[AuditLog]:
    """20 bundle events: created, approved, status changes, executed."""
    events = []
    statuses = ["approved", "status_changed", "executed", "created"]
    for i in range(n):
        action = _pick(statuses)
        bid = str(uuid.uuid4())
        name = f"Patch Bundle #{i + 1:03d}"
        events.append(
            _make_entry(
                action=f"bundle.{action}",
                resource_type="bundle",
                resource_id=bid,
                resource_name=name,
                user_id=_pick(SAMPLE_USER_IDS),
                details={
                    "new_status": action,
                    "risk_score": round(random.uniform(20, 95), 1),
                    "vuln_count": random.randint(1, 15),
                },
            )
        )
    return events


def _vulnerability_events(n: int = 20) -> list[AuditLog]:
    """20 vulnerability events: imported batches of different sizes."""
    events = []
    for i in range(n):
        count = random.randint(5, 150)
        events.append(
            _make_entry(
                action="vulnerability.imported",
                resource_type="vulnerability",
                resource_name=f"import-batch-{i + 1:03d}.csv",
                user_id=_pick(SAMPLE_USER_IDS),
                details={
                    "count": count,
                    "rows_processed": count + random.randint(0, 5),
                    "errors": random.randint(0, 3),
                    "filename": f"vulns-batch-{i + 1:03d}.csv",
                },
            )
        )
    return events


def _user_events(n: int = 15) -> list[AuditLog]:
    """15 user events: logins from different IPs, invites, accepts."""
    events = []
    actions = ["user.login", "user.invited", "user.invite_accepted"]
    for i in range(n):
        action = _pick(actions)
        uid_val = _pick(SAMPLE_USER_IDS)
        email = f"user{random.randint(1, 99)}@example.com"
        events.append(
            _make_entry(
                action=action,
                resource_type="user",
                resource_id=str(uid_val),
                resource_name=email,
                user_id=uid_val,
                details={
                    "email": email,
                    "role": _pick(["analyst", "engineer", "viewer", "admin"]),
                    "ip": _pick(SAMPLE_IPS),
                },
            )
        )
    return events


def _maintenance_window_events(n: int = 10) -> list[AuditLog]:
    """10 maintenance window events: created, deleted."""
    events = []
    actions = ["maintenance_window.created", "maintenance_window.deleted"]
    for i in range(n):
        wid = str(uuid.uuid4())
        name = f"MW {_pick(['Weekly', 'Emergency', 'Quarterly', 'Nightly'])} - {i + 1}"
        events.append(
            _make_entry(
                action=_pick(actions),
                resource_type="maintenance_window",
                resource_id=wid,
                resource_name=name,
                user_id=_pick(SAMPLE_USER_IDS),
                details={
                    "type": _pick(["scheduled", "emergency", "recurring"]),
                    "environment": _pick(["production", "staging", "development"]),
                    "duration_hours": random.randint(1, 8),
                },
            )
        )
    return events


def _goal_events(n: int = 10) -> list[AuditLog]:
    """10 goal events."""
    events = []
    actions = ["goal.created", "goal.updated", "goal.completed", "goal.deadline_changed"]
    for i in range(n):
        gid = str(uuid.uuid4())
        events.append(
            _make_entry(
                action=_pick(actions),
                resource_type="goal",
                resource_id=gid,
                resource_name=f"Reduce Critical CVEs Q{random.randint(1, 4)}",
                user_id=_pick(SAMPLE_USER_IDS),
                details={
                    "target_reduction_pct": random.randint(20, 80),
                    "environment": _pick(["production", "staging"]),
                },
            )
        )
    return events


def _failed_login_events(n: int = 5) -> list[AuditLog]:
    """5 failed login attempts (success=False)."""
    events = []
    for i in range(n):
        events.append(
            _make_entry(
                action="user.login",
                resource_type="user",
                resource_name=f"attacker{i}@unknown.example",
                success=False,
                error_message="Invalid credentials",
                details={
                    "email": f"attacker{i}@unknown.example",
                    "attempts": random.randint(1, 5),
                },
            )
        )
    return events


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    # Resolve the database URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        try:
            from backend.core.config import settings
            db_url = settings.DATABASE_URL
        except Exception as exc:
            print(f"ERROR: Cannot resolve DATABASE_URL — {exc}")
            sys.exit(1)

    # Build async engine (ensure asyncpg driver)
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Generate entries
    all_entries: list[AuditLog] = []
    bundle_evts = _bundle_events(20)
    vuln_evts = _vulnerability_events(20)
    user_evts = _user_events(15)
    mw_evts = _maintenance_window_events(10)
    goal_evts = _goal_events(10)
    failed_evts = _failed_login_events(5)

    all_entries.extend(bundle_evts)
    all_entries.extend(vuln_evts)
    all_entries.extend(user_evts)
    all_entries.extend(mw_evts)
    all_entries.extend(goal_evts)
    all_entries.extend(failed_evts)

    total = len(all_entries)

    async with session_factory() as session:
        for entry in all_entries:
            session.add(entry)
        await session.commit()

    await engine.dispose()

    # Summary
    print(f"Seeded {total} audit events across 6 categories")
    print(f"  Bundle events:               {len(bundle_evts)}")
    print(f"  Vulnerability events:        {len(vuln_evts)}")
    print(f"  User events:                 {len(user_evts)}")
    print(f"  Maintenance window events:   {len(mw_evts)}")
    print(f"  Goal events:                 {len(goal_evts)}")
    print(f"  Failed login attempts:       {len(failed_evts)}")


if __name__ == "__main__":
    asyncio.run(main())
