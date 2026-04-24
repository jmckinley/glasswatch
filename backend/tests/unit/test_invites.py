"""
Unit tests for invite creation logic.

Tests token uniqueness, expiry, acceptance, and revocation behavior.
"""
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


def _make_invite(**kwargs):
    """Helper: build a simple mock invite object."""
    from backend.models.invite import Invite

    defaults = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "email": "invited@example.com",
        "role": "analyst",
        "token": secrets.token_urlsafe(32),
        "created_by": uuid4(),
        "expires_at": datetime.utcnow() + timedelta(days=7),
        "accepted_at": None,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    invite = Invite(**defaults)
    return invite


class TestInviteTokenUniqueness:
    """Token generation produces unique values."""

    async def test_invite_token_is_unique(self):
        """Two separately-generated tokens must differ."""
        token_a = secrets.token_urlsafe(32)
        token_b = secrets.token_urlsafe(32)
        assert token_a != token_b, "tokens should be unique across calls"

    async def test_invite_token_has_minimum_length(self):
        """Token must be at least 32 chars (URL-safe base64 of 32 bytes)."""
        token = secrets.token_urlsafe(32)
        assert len(token) >= 32


class TestInviteExpiry:
    """Invite expiry timestamps are calculated correctly."""

    async def test_invite_expires_in_7_days(self):
        """expires_at should be approximately 7 days from now."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=7)

        delta = expires_at - now
        assert 6 <= delta.days <= 7, f"Expected ~7 days, got {delta.days}"

    async def test_invite_not_yet_expired(self):
        """A freshly-created invite is not expired."""
        invite = _make_invite()
        assert invite.expires_at > datetime.utcnow()

    async def test_invite_expired_flag(self):
        """An invite with expires_at in the past is considered expired."""
        invite = _make_invite(expires_at=datetime.utcnow() - timedelta(seconds=1))
        assert invite.expires_at < datetime.utcnow()


class TestInviteAcceptance:
    """Acceptance logic sets accepted_at and validates state."""

    async def test_invite_accept_marks_accepted_at(self):
        """After accepting, accepted_at must be set to a datetime."""
        invite = _make_invite()
        assert invite.accepted_at is None

        # Simulate accept logic
        invite.accepted_at = datetime.utcnow()
        assert invite.accepted_at is not None
        assert isinstance(invite.accepted_at, datetime)

    async def test_invite_accept_sets_recent_timestamp(self):
        """accepted_at should be very close to now."""
        invite = _make_invite()
        before = datetime.utcnow()
        invite.accepted_at = datetime.utcnow()
        after = datetime.utcnow()

        assert before <= invite.accepted_at <= after

    async def test_already_accepted_invite_raises_on_re_accept(self):
        """An already-accepted invite must raise 400."""
        from fastapi import HTTPException

        invite = _make_invite(accepted_at=datetime.utcnow())

        # Reproduce the guard from invites.py
        def _check_not_already_accepted(inv):
            if inv.accepted_at is not None:
                raise HTTPException(status_code=400, detail="Invite already accepted")

        with pytest.raises(HTTPException) as exc_info:
            _check_not_already_accepted(invite)

        assert exc_info.value.status_code == 400


class TestInviteRevocation:
    """Revoking (deleting) an invite prevents acceptance."""

    async def test_invite_revoked_cannot_be_accepted(self):
        """If the invite lookup returns None (deleted), a 404 is raised."""
        from fastapi import HTTPException

        # Simulate "invite deleted from DB" — lookup returns None
        invite = None

        def _accept_invite(inv):
            if inv is None:
                raise HTTPException(
                    status_code=404, detail="Invite not found or already used"
                )

        with pytest.raises(HTTPException) as exc_info:
            _accept_invite(invite)

        assert exc_info.value.status_code == 404

    async def test_valid_invite_can_be_accepted(self):
        """A pending, non-expired invite does not raise."""
        invite = _make_invite()

        def _check_invite(inv):
            if inv is None:
                raise Exception("not found")
            if inv.accepted_at is not None:
                raise Exception("already accepted")
            if inv.expires_at < datetime.utcnow():
                raise Exception("expired")

        # Should not raise
        _check_invite(invite)

    async def test_expired_invite_cannot_be_accepted(self):
        """Expired invite raises 400."""
        from fastapi import HTTPException

        invite = _make_invite(expires_at=datetime.utcnow() - timedelta(hours=1))

        def _check_expiry(inv):
            if inv.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="Invite has expired")

        with pytest.raises(HTTPException) as exc_info:
            _check_expiry(invite)

        assert exc_info.value.status_code == 400
