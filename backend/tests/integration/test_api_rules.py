"""
Integration tests for the Rules API endpoints.

Covers CRUD, NLP parse, rule evaluation, and auth.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRulesAPI:
    """Integration tests for /api/v1/rules."""

    # ------------------------------------------------------------------
    # GET /rules — list
    # ------------------------------------------------------------------

    async def test_list_rules_requires_auth(self, client: AsyncClient):
        """Unauthenticated GET /rules returns 401."""
        response = await client.get("/api/v1/rules")
        assert response.status_code == 401

    async def test_list_rules_empty(self, authenticated_client: AsyncClient, test_tenant):
        """GET /rules returns a list (may include defaults)."""
        response = await authenticated_client.get("/api/v1/rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    # ------------------------------------------------------------------
    # GET /rules/defaults
    # ------------------------------------------------------------------

    async def test_get_default_rules(self, authenticated_client: AsyncClient, test_tenant):
        """GET /rules/defaults returns the default rule templates."""
        response = await authenticated_client.get("/api/v1/rules/defaults")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    # ------------------------------------------------------------------
    # POST /rules — create
    # ------------------------------------------------------------------

    async def test_create_rule_time_window(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /rules creates a time_window rule."""
        payload = {
            "name": "No Friday Deploys",
            "scope_type": "global",
            "condition_type": "time_window",
            "condition_config": {
                "blocked_days": [4],  # Friday
                "blocked_hours": list(range(0, 24)),
            },
            "action_type": "block",
            "action_config": {"reason": "No Friday deployments"},
        }
        response = await authenticated_client.post("/api/v1/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "No Friday Deploys"
        assert data["enabled"] is True
        assert "id" in data

    async def test_create_rule_risk_threshold(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /rules creates a risk_threshold rule."""
        payload = {
            "name": "High Risk Approval",
            "scope_type": "global",
            "condition_type": "risk_threshold",
            "condition_config": {"threshold": 80},
            "action_type": "require_approval",
            "action_config": {"approvers": ["security-team"]},
        }
        response = await authenticated_client.post("/api/v1/rules", json=payload)
        assert response.status_code == 201

    async def test_create_rule_requires_auth(self, client: AsyncClient):
        """Unauthenticated POST /rules returns 401."""
        response = await client.post(
            "/api/v1/rules",
            json={
                "name": "Anon Rule",
                "scope_type": "global",
                "condition_type": "always",
                "condition_config": {},
                "action_type": "warn",
                "action_config": {},
            },
        )
        assert response.status_code == 401

    async def test_create_rule_missing_name_returns_422(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Rule without name returns 422."""
        payload = {
            "scope_type": "global",
            "condition_type": "always",
            "condition_config": {},
            "action_type": "warn",
            "action_config": {},
        }
        response = await authenticated_client.post("/api/v1/rules", json=payload)
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # GET /rules/{id}
    # ------------------------------------------------------------------

    async def test_get_rule_by_id(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /rules/{id} returns the rule."""
        create = await authenticated_client.post(
            "/api/v1/rules",
            json={
                "name": "Fetch Me Rule",
                "scope_type": "global",
                "condition_type": "always",
                "condition_config": {},
                "action_type": "warn",
                "action_config": {},
            },
        )
        assert create.status_code == 201
        rule_id = create.json()["id"]

        response = await authenticated_client.get(f"/api/v1/rules/{rule_id}")
        assert response.status_code == 200
        assert response.json()["id"] == rule_id

    async def test_get_rule_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """GET /rules/{nonexistent} returns 404."""
        response = await authenticated_client.get(f"/api/v1/rules/{uuid4()}")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # PATCH /rules/{id}
    # ------------------------------------------------------------------

    async def test_update_rule(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /rules/{id} updates the rule."""
        create = await authenticated_client.post(
            "/api/v1/rules",
            json={
                "name": "Old Rule Name",
                "scope_type": "global",
                "condition_type": "always",
                "condition_config": {},
                "action_type": "warn",
                "action_config": {},
            },
        )
        rule_id = create.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/rules/{rule_id}", json={"name": "Updated Rule Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Rule Name"

    async def test_disable_rule(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """PATCH /rules/{id} can disable a rule."""
        create = await authenticated_client.post(
            "/api/v1/rules",
            json={
                "name": "Enable/Disable Rule",
                "scope_type": "global",
                "condition_type": "always",
                "condition_config": {},
                "action_type": "warn",
                "action_config": {},
                "enabled": True,
            },
        )
        rule_id = create.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/rules/{rule_id}", json={"enabled": False}
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    # ------------------------------------------------------------------
    # DELETE /rules/{id}
    # ------------------------------------------------------------------

    async def test_delete_rule(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /rules/{id} removes the rule."""
        create = await authenticated_client.post(
            "/api/v1/rules",
            json={
                "name": "Delete Me Rule",
                "scope_type": "global",
                "condition_type": "always",
                "condition_config": {},
                "action_type": "warn",
                "action_config": {},
            },
        )
        rule_id = create.json()["id"]

        delete = await authenticated_client.delete(f"/api/v1/rules/{rule_id}")
        assert delete.status_code == 200

        get = await authenticated_client.get(f"/api/v1/rules/{rule_id}")
        assert get.status_code == 404

    async def test_delete_rule_not_found(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """DELETE /rules/{nonexistent} returns 404."""
        response = await authenticated_client.delete(f"/api/v1/rules/{uuid4()}")
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # POST /rules/parse-nlp — NLP rule creation
    # ------------------------------------------------------------------

    async def test_parse_nlp_friday_block(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /rules/parse-nlp extracts day-of-week blocking from NLP."""
        response = await authenticated_client.post(
            "/api/v1/rules/parse-nlp",
            json={"text": "Block all deployments on Friday"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should return a rule structure with condition info
        assert isinstance(data, dict)

    async def test_parse_nlp_requires_auth(self, client: AsyncClient):
        """Unauthenticated POST /rules/parse-nlp returns 401."""
        response = await client.post(
            "/api/v1/rules/parse-nlp", json={"text": "Block Friday deployments"}
        )
        assert response.status_code == 401

    async def test_parse_nlp_empty_text_returns_422(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """Empty text returns 422."""
        response = await authenticated_client.post(
            "/api/v1/rules/parse-nlp", json={"text": ""}
        )
        assert response.status_code in (400, 422)

    # ------------------------------------------------------------------
    # POST /rules/evaluate
    # ------------------------------------------------------------------

    async def test_evaluate_rules_empty(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        """POST /rules/evaluate with no context returns a verdict."""
        response = await authenticated_client.post("/api/v1/rules/evaluate", json={})
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ("allow", "warn", "block")
        assert "matches" in data
        assert isinstance(data["matches"], list)

    async def test_evaluate_rules_requires_auth(self, client: AsyncClient):
        """Unauthenticated POST /rules/evaluate returns 401."""
        response = await client.post("/api/v1/rules/evaluate", json={})
        assert response.status_code == 401
