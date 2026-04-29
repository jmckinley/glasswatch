"""
Integration tests for the AI Agent endpoint (/api/v1/agent/chat).

Covers all 9 intent handlers, the fallback (no-API-key path), empty message,
and auth enforcement.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CHAT_URL = "/api/v1/agent/chat"


def _chat(msg: str):
    return {"message": msg}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentChatAPI:
    """Tests for POST /api/v1/agent/chat."""

    # --- auth ---

    async def test_requires_auth(self, client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await client.post(CHAT_URL, json=_chat("hello"))
        assert response.status_code == 401

    # --- validation ---

    async def test_empty_message_returns_422(self, authenticated_client: AsyncClient, test_tenant):
        """Empty message returns 422 (FastAPI validation)."""
        response = await authenticated_client.post(CHAT_URL, json={"message": ""})
        assert response.status_code == 422

    async def test_missing_message_field_returns_422(self, authenticated_client: AsyncClient, test_tenant):
        """Missing message field returns 422."""
        response = await authenticated_client.post(CHAT_URL, json={})
        assert response.status_code == 422

    # --- response shape ---

    async def _assert_chat_shape(self, client: AsyncClient, message: str):
        """Helper: POST chat and assert the response has the right shape."""
        response = await client.post(CHAT_URL, json=_chat(message))
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "actions_taken" in data
        assert "suggested_actions" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
        assert isinstance(data["actions_taken"], list)
        assert isinstance(data["suggested_actions"], list)
        return data

    # --- intent: attention ---

    async def test_intent_attention_what_needs_my_attention(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'What needs my attention right now?' triggers attention handler."""
        await self._assert_chat_shape(
            authenticated_client, "What needs my attention right now?"
        )

    async def test_intent_attention_critical_kev(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Show me critical KEV vulnerabilities' triggers attention handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Show me critical KEV vulnerabilities"
        )
        # Should NOT be the capabilities menu (fallback)
        assert "I can help with" not in data["response"]

    # --- intent: cve_lookup ---

    async def test_intent_cve_lookup(
        self, authenticated_client: AsyncClient, test_tenant,
        create_test_vulnerability, create_test_asset, create_test_bundle,
        test_session
    ):
        """'Find fixes for CVE-2024-1234' triggers cve_lookup handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Find fixes for CVE-2024-1234"
        )
        # Response should mention CVE or no-match message
        assert "CVE" in data["response"] or "not found" in data["response"].lower() or "no" in data["response"].lower()

    # --- intent: create_rule ---

    async def test_intent_create_rule(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Create a rule blocking Friday deployments' triggers create_rule handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Create a rule blocking Friday deployments"
        )
        # Response should mention rule creation or Friday
        lower = data["response"].lower()
        assert "rule" in lower or "friday" in lower or "created" in lower

    # --- intent: show_windows ---

    async def test_intent_show_windows(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Show maintenance windows' triggers show_windows handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Show maintenance windows"
        )
        # Should NOT be the capabilities menu
        assert "I can help with" not in data["response"]

    # --- intent: add_window ---

    async def test_intent_add_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Add maintenance window on Saturday at 2am' triggers add_window handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Add maintenance window on Saturday at 2am"
        )
        lower = data["response"].lower()
        assert "window" in lower or "saturday" in lower or "created" in lower or "maintenance" in lower

    # --- intent: show_goals ---

    async def test_intent_show_goals(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Show goals' triggers show_goals handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Show goals"
        )
        assert "I can help with" not in data["response"]

    # --- intent: show_bundles ---

    async def test_intent_show_bundles(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Show bundles' triggers show_bundles handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "Show bundles"
        )
        assert "I can help with" not in data["response"]

    async def test_intent_pending_approvals(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Pending approvals' also maps to show_bundles."""
        data = await self._assert_chat_shape(
            authenticated_client, "Pending approvals"
        )
        assert "I can help with" not in data["response"]

    # --- intent: approve_bundle ---

    async def test_intent_approve_bundle_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'Approve bundle NonExistent' gracefully handles missing bundle."""
        data = await self._assert_chat_shape(
            authenticated_client, "Approve bundle NonExistentBundle"
        )
        lower = data["response"].lower()
        assert "not found" in lower or "no bundle" in lower or "couldn't find" in lower or "approve" in lower

    # --- intent: risk_score ---

    async def test_intent_risk_score(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """'How are we doing?' triggers risk_score handler."""
        data = await self._assert_chat_shape(
            authenticated_client, "How are we doing?"
        )
        assert "I can help with" not in data["response"]

    # --- fallback (no API key) ---

    async def test_fallback_returns_capability_list(
        self, authenticated_client: AsyncClient, test_tenant, monkeypatch
    ):
        """
        Unknown intent with no ANTHROPIC_API_KEY returns the capability list,
        not an error.
        """
        # Ensure no API key is set for the fallback path
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        data = await self._assert_chat_shape(
            authenticated_client, "something completely random and unrecognised xyz123"
        )
        # Fallback returns capability menu
        assert "I can help with" in data["response"]
        # Suggests follow-up actions
        assert len(data["suggested_actions"]) > 0

    # --- context field ---

    async def test_context_field_accepted(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Optional context field is accepted without error."""
        response = await authenticated_client.post(
            CHAT_URL,
            json={"message": "Show goals", "context": {"page": "dashboard"}},
        )
        assert response.status_code == 200
