"""
Simulator URL overrides for testing.

Set SIMULATOR_MODE=true to route all external calls to the local simulator.
All URL overrides are resolved from SIMULATOR_BASE (default: http://localhost:8099).

Example:
    SIMULATOR_MODE=true SIMULATOR_BASE=http://localhost:8099 pytest tests/integration/

Usage in production code:
    from backend.simulators.config import get_endpoint

    base_url = get_endpoint("tenable", real_base="https://cloud.tenable.com")
"""
import os

SIMULATOR_MODE: bool = os.getenv("SIMULATOR_MODE", "false").lower() in ("true", "1", "yes")
SIMULATOR_BASE: str = os.getenv("SIMULATOR_BASE", "http://localhost:8099").rstrip("/")

SIMULATOR_ENDPOINTS: dict[str, str] = {
    "tenable":    f"{SIMULATOR_BASE}/tenable",
    "qualys":     f"{SIMULATOR_BASE}/qualys",
    "rapid7":     f"{SIMULATOR_BASE}/rapid7",
    "slack":      f"{SIMULATOR_BASE}/slack",
    "teams":      f"{SIMULATOR_BASE}/teams",
    "jira":       f"{SIMULATOR_BASE}/jira",
    "servicenow": f"{SIMULATOR_BASE}/servicenow",
    "cisa_kev":   f"{SIMULATOR_BASE}/cisa/kev",
    "nvd":        f"{SIMULATOR_BASE}/nvd",
    "epss":       f"{SIMULATOR_BASE}/epss",
    "resend":     f"{SIMULATOR_BASE}/resend",
}


def get_endpoint(service: str, real_base: str) -> str:
    """
    Return the correct base URL for a service.

    If SIMULATOR_MODE is active, returns the simulator URL.
    Otherwise returns real_base unchanged.

    Args:
        service:   Key from SIMULATOR_ENDPOINTS (e.g. "tenable")
        real_base: Production base URL to fall back to

    Returns:
        Base URL string (no trailing slash)
    """
    if SIMULATOR_MODE:
        return SIMULATOR_ENDPOINTS.get(service, f"{SIMULATOR_BASE}/{service}")
    return real_base.rstrip("/")
