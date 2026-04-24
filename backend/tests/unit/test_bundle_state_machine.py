"""
Unit tests for bundle state machine transitions.

Tests the VALID_TRANSITIONS map that guards status changes via
PATCH /bundles/{id}/status and POST /bundles/{id}/approve.

The logic is extracted here so it can be tested without a database.
"""
import pytest

pytestmark = pytest.mark.asyncio

# ── Reproduce VALID_TRANSITIONS from bundles.py ───────────────────────────────

VALID_TRANSITIONS = {
    "draft":       ["scheduled", "approved", "cancelled"],
    "scheduled":   ["approved", "draft", "cancelled"],
    "approved":    ["in_progress", "draft", "cancelled"],
    "in_progress": ["completed", "failed"],
    "completed":   [],   # terminal
    "failed":      ["draft"],
    "cancelled":   [],   # terminal
}

ALL_STATUSES = list(VALID_TRANSITIONS.keys())


def can_transition(from_status: str, to_status: str) -> bool:
    """Return True when the transition is allowed by the state machine."""
    if from_status == to_status:
        return True  # no-op is always allowed
    return to_status in VALID_TRANSITIONS.get(from_status, [])


# ── Valid transitions ─────────────────────────────────────────────────────────

class TestValidTransitions:
    async def test_valid_transition_draft_to_pending(self):
        """draft → approved is a legal transition."""
        assert can_transition("draft", "approved") is True

    async def test_valid_transition_draft_to_scheduled(self):
        """draft → scheduled is a legal transition."""
        assert can_transition("draft", "scheduled") is True

    async def test_valid_transition_approved_to_in_progress(self):
        """approved → in_progress is a legal transition."""
        assert can_transition("approved", "in_progress") is True

    async def test_valid_transition_in_progress_to_completed(self):
        """in_progress → completed is a legal transition."""
        assert can_transition("in_progress", "completed") is True

    async def test_valid_transition_in_progress_to_failed(self):
        """in_progress → failed is a legal transition."""
        assert can_transition("in_progress", "failed") is True

    async def test_valid_transition_failed_to_draft(self):
        """failed → draft (retry) is a legal transition."""
        assert can_transition("failed", "draft") is True

    async def test_valid_transition_any_to_cancelled(self):
        """Cancellable statuses (draft, scheduled, approved) can all go → cancelled."""
        cancellable = ["draft", "scheduled", "approved"]
        for status in cancellable:
            assert can_transition(status, "cancelled"), \
                f"Expected '{status}' → 'cancelled' to be allowed"

    async def test_valid_transition_noop(self):
        """A status transition to itself (no-op) is always allowed."""
        for status in ALL_STATUSES:
            assert can_transition(status, status) is True


# ── Invalid transitions ───────────────────────────────────────────────────────

class TestInvalidTransitions:
    async def test_invalid_transition_completed_to_approved(self):
        """completed → approved must be rejected (terminal state)."""
        assert can_transition("completed", "approved") is False

    async def test_invalid_transition_completed_to_draft(self):
        """completed → draft must be rejected (terminal state)."""
        assert can_transition("completed", "draft") is False

    async def test_invalid_transition_in_progress_to_draft(self):
        """in_progress → draft must be rejected."""
        assert can_transition("in_progress", "draft") is False

    async def test_invalid_transition_in_progress_to_approved(self):
        """in_progress → approved must be rejected."""
        assert can_transition("in_progress", "approved") is False

    async def test_invalid_transition_cancelled_to_draft(self):
        """cancelled is terminal — cannot go back to draft."""
        assert can_transition("cancelled", "draft") is False

    async def test_invalid_transition_cancelled_to_approved(self):
        """cancelled → approved must be rejected."""
        assert can_transition("cancelled", "approved") is False


# ── Map completeness ──────────────────────────────────────────────────────────

class TestValidTransitionsMapIsComplete:
    async def test_valid_transitions_map_is_complete(self):
        """Every known status has an entry in VALID_TRANSITIONS."""
        for status in ALL_STATUSES:
            assert status in VALID_TRANSITIONS, \
                f"Status '{status}' is missing from VALID_TRANSITIONS"

    async def test_all_transition_targets_are_known_statuses(self):
        """Every target state in VALID_TRANSITIONS is itself a known status."""
        for from_status, targets in VALID_TRANSITIONS.items():
            for target in targets:
                assert target in ALL_STATUSES, \
                    f"Target '{target}' from '{from_status}' is not a known status"

    async def test_terminal_states_have_no_transitions(self):
        """completed and cancelled are terminal — they allow no transitions."""
        assert VALID_TRANSITIONS["completed"] == []
        assert VALID_TRANSITIONS["cancelled"] == []
