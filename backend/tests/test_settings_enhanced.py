"""
Tests for enhanced settings logic.

Unit tests for mask_sensitive, mark_configured, deep_merge, and
DEFAULT_SETTINGS structure. These do not require a database connection.

Integration tests against a live API are in tests/integration/.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.v1.settings import (
    mask_sensitive,
    mark_configured,
    deep_merge,
    get_merged_settings,
    DEFAULT_SETTINGS,
    SENSITIVE_KEYS,
)


class TestDefaultSettings:
    def test_has_all_sections(self):
        for section in ("notifications", "security", "integrations", "ai", "display"):
            assert section in DEFAULT_SETTINGS, f"Missing section: {section}"

    def test_integrations_section_keys(self):
        i = DEFAULT_SETTINGS["integrations"]
        expected = [
            "vulncheck_api_key", "vulncheck_api_key_configured",
            "snapper_webhook_secret", "snapper_webhook_secret_configured",
            "jira_url", "jira_email",
            "jira_api_token", "jira_api_token_configured",
            "jira_project_key",
            "servicenow_url", "servicenow_username",
            "servicenow_password", "servicenow_password_configured",
        ]
        for key in expected:
            assert key in i, f"Missing integrations key: {key}"

    def test_ai_section_keys(self):
        ai = DEFAULT_SETTINGS["ai"]
        assert "anthropic_api_key" in ai
        assert "anthropic_api_key_configured" in ai
        assert "ai_assistant_enabled" in ai
        assert "nlp_rules_enabled" in ai

    def test_ai_defaults_enabled(self):
        ai = DEFAULT_SETTINGS["ai"]
        assert ai["ai_assistant_enabled"] is True
        assert ai["nlp_rules_enabled"] is True
        assert ai["anthropic_api_key"] is None
        assert ai["anthropic_api_key_configured"] is False

    def test_notifications_has_slack_webhook(self):
        n = DEFAULT_SETTINGS["notifications"]
        assert "slack_webhook_url" in n
        assert "teams_enabled" in n
        assert "teams_webhook_url" in n

    def test_security_has_patch_age(self):
        s = DEFAULT_SETTINGS["security"]
        assert "min_patch_age_days" in s
        assert "patch_weather_threshold" in s


class TestDeepMerge:
    def test_shallow_merge(self):
        base = {"a": 1, "b": 2}
        update = {"b": 99}
        result = deep_merge(base, update)
        assert result["a"] == 1
        assert result["b"] == 99

    def test_deep_nested_merge(self):
        base = {"settings": {"x": 1, "y": 2}}
        update = {"settings": {"y": 99}}
        result = deep_merge(base, update)
        assert result["settings"]["x"] == 1
        assert result["settings"]["y"] == 99

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        update = {"a": {"x": 99}}
        result = deep_merge(base, update)
        assert base["a"]["x"] == 1  # unchanged
        assert result["a"]["x"] == 99

    def test_adds_new_keys(self):
        base = {"a": 1}
        update = {"b": 2, "c": 3}
        result = deep_merge(base, update)
        assert result["b"] == 2
        assert result["c"] == 3


class TestMaskSensitive:
    def test_masks_api_key(self):
        result = mask_sensitive({"vulncheck_api_key": "vc-secret1234"})
        val = result["vulncheck_api_key"]
        assert val is not None
        assert val.startswith("***")
        assert "1234" in val
        assert "secret" not in val

    def test_leaves_none_unmasked(self):
        result = mask_sensitive({"vulncheck_api_key": None})
        assert result["vulncheck_api_key"] is None

    def test_leaves_empty_string_unmasked(self):
        result = mask_sensitive({"vulncheck_api_key": ""})
        assert result["vulncheck_api_key"] == ""

    def test_non_sensitive_key_unchanged(self):
        result = mask_sensitive({"timezone": "UTC", "theme": "dark"})
        assert result["timezone"] == "UTC"
        assert result["theme"] == "dark"

    def test_recurses_into_nested(self):
        result = mask_sensitive({
            "integrations": {"jira_api_token": "ATATT3x-token-5678"}
        })
        val = result["integrations"]["jira_api_token"]
        assert val.startswith("***")
        assert "5678" in val

    def test_all_sensitive_keys_are_masked(self):
        settings = {key: f"secret-value-{key[-4:]}" for key in SENSITIVE_KEYS}
        result = mask_sensitive(settings)
        for key in SENSITIVE_KEYS:
            val = result[key]
            assert val is not None
            assert val.startswith("***"), f"Key {key!r} should be masked"

    def test_short_value_masked(self):
        # Even short values should be masked
        result = mask_sensitive({"vulncheck_api_key": "ab"})
        val = result["vulncheck_api_key"]
        assert val is not None
        assert "ab" in val  # all chars shown since len < 4


class TestMarkConfigured:
    def test_sets_configured_flag_when_value_set(self):
        result = mark_configured({"vulncheck_api_key": "real-key-here"})
        assert result["vulncheck_api_key_configured"] is True

    def test_does_not_set_flag_for_none(self):
        result = mark_configured({"vulncheck_api_key": None})
        configured = result.get("vulncheck_api_key_configured")
        # Should be absent or False, not True
        assert configured is not True

    def test_does_not_set_flag_for_non_sensitive(self):
        result = mark_configured({"timezone": "UTC"})
        assert "timezone_configured" not in result

    def test_recurses_into_nested(self):
        result = mark_configured({
            "integrations": {"anthropic_api_key": "sk-ant-abc"}
        })
        assert result["integrations"]["anthropic_api_key_configured"] is True

    def test_preserves_other_keys(self):
        result = mark_configured({
            "vulncheck_api_key": "some-key",
            "jira_url": "https://jira.example.com",
        })
        assert result["jira_url"] == "https://jira.example.com"
        assert result["vulncheck_api_key_configured"] is True


class TestGetMergedSettings:
    def test_none_returns_defaults(self):
        result = get_merged_settings(None)
        for section in ("notifications", "security", "integrations", "ai", "display"):
            assert section in result

    def test_empty_dict_returns_defaults(self):
        result = get_merged_settings({})
        assert "integrations" in result

    def test_partial_update_merges(self):
        tenant_settings = {"display": {"timezone": "Asia/Tokyo"}}
        result = get_merged_settings(tenant_settings)
        assert result["display"]["timezone"] == "Asia/Tokyo"
        # Other display keys preserved from defaults
        assert "date_format" in result["display"]
        # Other sections still present
        assert "integrations" in result
