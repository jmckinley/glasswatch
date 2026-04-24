"""
Unit tests for AuditService.

Uses the in-memory SQLite test database via standard conftest fixtures.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.services.audit_service import AuditService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tenant_id():
    return uuid4()

def _user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuditServiceCreate:
    async def test_create_audit_log(self, test_session: AsyncSession, test_tenant, test_user):
        """AuditService.log creates a record in the DB."""
        entry = await AuditService.log(
            db=test_session,
            tenant_id=test_tenant.id,
            action="bundle.approved",
            resource_type="bundle",
            resource_id=str(uuid4()),
            resource_name="Test Bundle",
            user_id=test_user.id,
            details={"old_status": "draft", "new_status": "approved"},
            ip_address="127.0.0.1",
            user_agent="pytest/1.0",
        )
        await test_session.commit()

        assert entry.id is not None
        assert entry.action == "bundle.approved"
        assert entry.resource_type == "bundle"
        assert entry.resource_name == "Test Bundle"
        assert entry.details == {"old_status": "draft", "new_status": "approved"}
        assert entry.success is True
        assert entry.tenant_id == test_tenant.id
        assert entry.user_id == test_user.id

    async def test_null_user_allowed(self, test_session: AsyncSession, test_tenant):
        """System actions (user_id=None) are valid audit entries."""
        entry = await AuditService.log(
            db=test_session,
            tenant_id=test_tenant.id,
            action="vulnerability.imported",
            resource_type="vulnerability",
            details={"count": 42},
        )
        await test_session.commit()

        assert entry.user_id is None
        assert entry.action == "vulnerability.imported"
        assert entry.details["count"] == 42

    async def test_failed_action_recorded(self, test_session: AsyncSession, test_tenant, test_user):
        """success=False and error_message are stored correctly."""
        entry = await AuditService.log(
            db=test_session,
            tenant_id=test_tenant.id,
            action="user.login_failed",
            resource_type="user",
            resource_id=str(test_user.id),
            user_id=test_user.id,
            success=False,
            error_message="Invalid password",
        )
        await test_session.commit()

        assert entry.success is False
        assert entry.error_message == "Invalid password"


@pytest.mark.asyncio
class TestAuditServiceQuery:
    async def _seed(self, db: AsyncSession, test_tenant, test_user):
        """Create a handful of audit log entries for filtering tests."""
        actions = [
            ("bundle.approved", "bundle", "bundle-1"),
            ("bundle.executed", "bundle", "bundle-2"),
            ("user.login", "user", str(user.id)),
            ("vulnerability.imported", "vulnerability", None),
            ("maintenance_window.created", "maintenance_window", "mw-1"),
        ]
        for action, rtype, rid in actions:
            await AuditService.log(
                db=db,
                tenant_id=test_tenant.id,
                user_id=test_user.id if "user" in action else None,
                action=action,
                resource_type=rtype,
                resource_id=rid,
            )
        await db.commit()

    async def test_query_all(self, test_session: AsyncSession, test_tenant, test_user):
        """get_logs returns all entries for a tenant."""
        await self._seed(test_session, test_tenant, test_user)
        logs, total = await AuditService.get_logs(db=test_session, tenant_id=test_tenant.id)
        assert total == 5
        assert len(logs) == 5

    async def test_query_by_action(self, test_session: AsyncSession, test_tenant, test_user):
        """Filtering by action works."""
        await self._seed(test_session, test_tenant, test_user)
        logs, total = await AuditService.get_logs(
            db=test_session,
            tenant_id=test_tenant.id,
            action="bundle.approved",
        )
        assert total == 1
        assert logs[0].action == "bundle.approved"

    async def test_query_by_resource_type(self, test_session: AsyncSession, test_tenant, test_user):
        """Filtering by resource_type works."""
        await self._seed(test_session, test_tenant, test_user)
        logs, total = await AuditService.get_logs(
            db=test_session,
            tenant_id=test_tenant.id,
            resource_type="bundle",
        )
        assert total == 2
        for log in logs:
            assert log.resource_type == "bundle"

    async def test_query_by_user_id(self, test_session: AsyncSession, test_tenant, test_user):
        """Filtering by user_id works."""
        await self._seed(test_session, test_tenant, test_user)
        logs, total = await AuditService.get_logs(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )
        # user.login + user_id on bundle entries = only user.login has user_id in _seed
        assert total >= 1
        for log in logs:
            assert log.user_id == test_user.id

    async def test_query_by_date_range(self, test_session: AsyncSession, test_tenant, test_user):
        """since/until date range filtering works."""
        await self._seed(test_session, test_tenant, test_user)

        # Future window — should return 0
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        logs, total = await AuditService.get_logs(
            db=test_session,
            tenant_id=test_tenant.id,
            since=future,
        )
        assert total == 0

        # Past window that covers everything — should return all
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        logs, total = await AuditService.get_logs(
            db=test_session,
            tenant_id=test_tenant.id,
            since=past,
        )
        assert total == 5

    async def test_pagination(self, test_session: AsyncSession, test_tenant, test_user):
        """limit and offset work for pagination."""
        await self._seed(test_session, test_tenant, test_user)
        logs_p1, total = await AuditService.get_logs(
            db=test_session, tenant_id=test_tenant.id, limit=2, offset=0
        )
        logs_p2, _ = await AuditService.get_logs(
            db=test_session, tenant_id=test_tenant.id, limit=2, offset=2
        )
        assert total == 5
        assert len(logs_p1) == 2
        assert len(logs_p2) == 2
        # No overlap
        ids_p1 = {log.id for log in logs_p1}
        ids_p2 = {log.id for log in logs_p2}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_tenant_isolation(self, test_session: AsyncSession, test_tenant, test_user):
        """Logs for tenant A are not visible to tenant B."""
        await self._seed(test_session, test_tenant, test_user)

        other_tenant_id = uuid4()
        logs, total = await AuditService.get_logs(
            db=test_session, tenant_id=other_tenant_id
        )
        assert total == 0
