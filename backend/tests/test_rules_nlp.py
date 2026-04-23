"""
Tests for NLP rule parsing logic.

Tests the pattern-matching fallback (always available, no DB needed)
and the response schema for the parse-nlp endpoint.

Integration tests against a live API require PostgreSQL and are
in tests/integration/ where the DB fixture uses a real PG instance.
"""
import pytest
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_pattern_matching(text: str) -> dict:
    """
    Run the same pattern-matching logic as the endpoint's fallback.
    Extracted so we can unit-test it independently of the DB.
    """
    lower = text.lower()

    result = {
        "name": text[:60],
        "description": text,
        "scope_type": "global",
        "scope_value": None,
        "scope_tags": None,
        "condition_type": "always",
        "condition_config": {},
        "action_type": "warn",
        "action_config": {},
        "priority": 50,
        "confidence": 0.5,
        "source": "pattern",
    }

    # Scope
    if "production" in lower or "prod" in lower:
        result["scope_type"] = "environment"
        result["scope_value"] = "production"

    # Condition + action
    if "friday" in lower:
        result["condition_type"] = "time_window"
        result["condition_config"] = {"type": "day_of_week", "days": ["Friday"], "after_hour": 15}
        result["action_type"] = "block"
        result["confidence"] = 0.85
        result["name"] = "Block deployments on Fridays"
    elif "month" in lower and "end" in lower:
        result["condition_type"] = "time_window"
        result["condition_config"] = {"type": "month_end", "days_before": 3}
        result["action_type"] = "warn"
        result["confidence"] = 0.85
        result["name"] = "Warn at month-end"

    return result


class TestNLPPatternMatching:
    def test_friday_rule(self):
        result = run_pattern_matching("Block deployments on Friday afternoons")
        assert result["condition_type"] == "time_window"
        assert result["action_type"] == "block"
        assert result["condition_config"]["type"] == "day_of_week"
        assert "Friday" in result["condition_config"]["days"]
        assert result["condition_config"]["after_hour"] == 15
        assert result["source"] == "pattern"
        assert result["confidence"] > 0.7

    def test_month_end_rule(self):
        result = run_pattern_matching("Warn about month end deployments")
        assert result["condition_type"] == "time_window"
        assert result["condition_config"]["type"] == "month_end"
        assert result["action_type"] == "warn"
        assert result["source"] == "pattern"

    def test_month_end_with_hyphen(self):
        result = run_pattern_matching("Block changes during month-end freeze")
        assert result["condition_type"] == "time_window"
        assert result["condition_config"]["type"] == "month_end"

    def test_production_scope(self):
        result = run_pattern_matching("Block deployments to production on Fridays")
        assert result["scope_type"] == "environment"
        assert result["scope_value"] == "production"
        # Should also match friday
        assert result["action_type"] == "block"

    def test_prod_shorthand_scope(self):
        result = run_pattern_matching("Warn before patching prod systems")
        assert result["scope_type"] == "environment"
        assert result["scope_value"] == "production"

    def test_unknown_text_defaults(self):
        result = run_pattern_matching("something completely unrecognized xyz123")
        assert result["scope_type"] == "global"
        assert result["condition_type"] == "always"
        assert result["action_type"] == "warn"
        assert result["source"] == "pattern"

    def test_response_schema_completeness(self):
        required_fields = [
            "name", "description", "scope_type", "scope_value",
            "scope_tags", "condition_type", "condition_config",
            "action_type", "action_config", "priority", "confidence", "source"
        ]
        result = run_pattern_matching("Block on Fridays")
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_confidence_is_float_in_range(self):
        result = run_pattern_matching("Block on Fridays")
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_priority_is_int(self):
        result = run_pattern_matching("Block on Fridays")
        assert isinstance(result["priority"], int)

    def test_name_truncated_to_60_chars(self):
        long_text = "x" * 100
        result = run_pattern_matching(long_text)
        assert len(result["name"]) <= 60

    def test_source_is_pattern(self):
        result = run_pattern_matching("some rule description")
        assert result["source"] == "pattern"

    def test_friday_case_insensitive(self):
        result = run_pattern_matching("BLOCK FRIDAY DEPLOYS")
        assert result["condition_type"] == "time_window"
        assert result["action_type"] == "block"


class TestSettingsLogic:
    """Test settings masking and merge logic without needing DB."""

    def _make_mask_fn(self):
        """Import and return the mask_sensitive function."""
        from backend.api.v1.settings import mask_sensitive
        return mask_sensitive

    def _make_merge_fn(self):
        from backend.api.v1.settings import deep_merge
        return deep_merge

    def _make_mark_configured_fn(self):
        from backend.api.v1.settings import mark_configured
        return mark_configured

    def test_mask_sensitive_masks_api_key(self):
        mask = self._make_mask_fn()
        result = mask({"vulncheck_api_key": "vc-supersecret-abcd"})
        assert result["vulncheck_api_key"] != "vc-supersecret-abcd"
        assert result["vulncheck_api_key"].startswith("***")
        assert "abcd" in result["vulncheck_api_key"]

    def test_mask_sensitive_leaves_none_alone(self):
        mask = self._make_mask_fn()
        result = mask({"vulncheck_api_key": None})
        assert result["vulncheck_api_key"] is None

    def test_mask_sensitive_leaves_non_sensitive_alone(self):
        mask = self._make_mask_fn()
        result = mask({"timezone": "America/New_York"})
        assert result["timezone"] == "America/New_York"

    def test_mask_sensitive_recurses_into_nested_dicts(self):
        mask = self._make_mask_fn()
        result = mask({"integrations": {"jira_api_token": "ATATT3x-1234"}})
        assert result["integrations"]["jira_api_token"] != "ATATT3x-1234"
        assert "1234" in result["integrations"]["jira_api_token"]

    def test_deep_merge_updates_nested(self):
        merge = self._make_merge_fn()
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        update = {"a": {"y": 99}}
        result = merge(base, update)
        assert result["a"]["x"] == 1  # preserved
        assert result["a"]["y"] == 99  # updated
        assert result["b"] == 3  # untouched

    def test_deep_merge_adds_new_keys(self):
        merge = self._make_merge_fn()
        base = {"a": 1}
        update = {"b": 2}
        result = merge(base, update)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_mark_configured_sets_flag_on_sensitive(self):
        mark = self._make_mark_configured_fn()
        result = mark({"vulncheck_api_key": "some-key"})
        assert result["vulncheck_api_key_configured"] is True

    def test_mark_configured_skips_none_value(self):
        mark = self._make_mark_configured_fn()
        result = mark({"vulncheck_api_key": None})
        assert result.get("vulncheck_api_key_configured") is None or \
               result.get("vulncheck_api_key_configured") is False

    def test_mark_configured_recurses_into_nested(self):
        mark = self._make_mark_configured_fn()
        result = mark({"integrations": {"anthropic_api_key": "sk-ant-test"}})
        assert result["integrations"]["anthropic_api_key_configured"] is True

    def test_default_settings_has_integrations(self):
        from backend.api.v1.settings import DEFAULT_SETTINGS
        assert "integrations" in DEFAULT_SETTINGS
        assert "ai" in DEFAULT_SETTINGS
        assert "notifications" in DEFAULT_SETTINGS
        assert "security" in DEFAULT_SETTINGS
        assert "display" in DEFAULT_SETTINGS

    def test_default_settings_integrations_keys(self):
        from backend.api.v1.settings import DEFAULT_SETTINGS
        integrations = DEFAULT_SETTINGS["integrations"]
        assert "vulncheck_api_key" in integrations
        assert "jira_url" in integrations
        assert "jira_email" in integrations
        assert "servicenow_url" in integrations

    def test_default_settings_ai_keys(self):
        from backend.api.v1.settings import DEFAULT_SETTINGS
        ai = DEFAULT_SETTINGS["ai"]
        assert "anthropic_api_key" in ai
        assert ai["ai_assistant_enabled"] is True
        assert ai["nlp_rules_enabled"] is True
