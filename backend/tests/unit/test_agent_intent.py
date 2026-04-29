"""
Regression tests: AI analyst intent pattern matching.

Guards against sample prompts displayed in the UI diverging from the
backend intent patterns — the exact failure that caused the analyst to
always respond with the capabilities list.
"""
import pytest
from backend.api.v1.agent import detect_intent, extract_cve, extract_bundle_name


# ---------------------------------------------------------------------------
# Sample prompts — these are the exact strings shown in the UI help menu.
# If detect_intent returns None for any of them, the fallback fires and
# the user sees the capabilities list instead of a real answer.
# ---------------------------------------------------------------------------

SAMPLE_PROMPT_INTENTS = [
    ("What needs my attention right now?", "attention"),
    ("Show me critical KEV vulnerabilities", "attention"),
    ("Create a rule blocking Friday deployments", "create_rule"),
    ("Show maintenance windows", "show_windows"),
    ("Add maintenance window on Saturday at 2am", "add_window"),
    ("Show goals", "show_goals"),
    ("Find fixes for CVE-2021-44228", "cve_lookup"),
    ("Show bundles", "show_bundles"),
    ("Pending approvals", "show_bundles"),
    ("Approve bundle KEV-Emergency", "approve_bundle"),
    ("How are we doing?", "risk_score"),
]


@pytest.mark.parametrize("prompt,expected_intent", SAMPLE_PROMPT_INTENTS)
def test_sample_prompt_matches_intent(prompt: str, expected_intent: str) -> None:
    """Every UI sample prompt must resolve to the correct intent."""
    result = detect_intent(prompt)
    assert result == expected_intent, (
        f"Sample prompt {prompt!r} expected intent {expected_intent!r} "
        f"but got {result!r}. "
        f"Update _INTENT_PATTERNS in agent.py to include this phrase."
    )


def test_unknown_prompt_returns_none() -> None:
    """Unrecognised prompts should return None and fall through to Claude."""
    assert detect_intent("hello there") is None
    assert detect_intent("what is the weather") is None


# ---------------------------------------------------------------------------
# extract_cve
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected_cve", [
    ("Find fixes for CVE-2021-44228", "CVE-2021-44228"),
    ("info on cve-2023-1234", "CVE-2023-1234"),
    ("nothing here", None),
])
def test_extract_cve(message: str, expected_cve: str | None) -> None:
    assert extract_cve(message) == expected_cve


# ---------------------------------------------------------------------------
# extract_bundle_name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected_name", [
    ("Approve bundle KEV-Emergency", "KEV-Emergency"),
    ("approve the bundle Sprint 10 Patches", "Sprint 10 Patches"),
    ("show bundles", None),
])
def test_extract_bundle_name(message: str, expected_name: str | None) -> None:
    assert extract_bundle_name(message) == expected_name
